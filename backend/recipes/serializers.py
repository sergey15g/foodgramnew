from rest_framework import serializers
from .models import Recipe, Ingredient, RecipeIngredient
from tags.serializers import TagSerializer, Tag
from users.serializers import UserSerializer
from django.core.files.base import ContentFile
import base64
import imghdr


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), source='ingredient')  # Используем только ID
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(source='ingredient.measurement_unit', read_only=True)
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'measurement_unit', 'amount']
    
    def validate_amount(self, value):
        if value < 1:
            raise serializers.ValidationError("Amount must be greater than or equal to 1.")
        return value

    # def to_representation(self, instance):
    #     # Добавляем сортировку объектов перед сериализацией
    #     queryset = instance.recipeingredient_set.order_by('id')  # Замените 'id' на поле, по которому нужно сортировать
    #     return super().RecipeIngredientSerializer(queryset)


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(source='recipeingredient_set', many=True)
    # tags = TagSerializer(many=True, read_only=True)
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all())
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    # is_subscribed = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ['id', 'tags', 'author', 'ingredients', 'is_favorited', 'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time']
        extra_kwargs = {
            'image': {'required': False, 'allow_null': True},
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True},
        }

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("Tags field cannot be empty.")
        
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Tags field contains duplicate entries.")
        return value
    
    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError("Cooking time must be at least 1 minute.")
        return value
    
    def to_internal_value(self, data):
        if 'image' in data and isinstance(data['image'], str):
            try:
                format, imgstr = data['image'].split(';base64,')
            except ValueError:
                raise serializers.ValidationError('Invalid image data')

            ext = format.split('/')[-1]
            data['image'] = ContentFile(base64.b64decode(imgstr), name='image.' + ext)
        return super().to_internal_value(data)

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.is_subscribed(user)
        return False
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Изменяем вывод тегов
        tags = instance.tags.all()
        representation['tags'] = TagSerializer(tags, many=True).data  # Выводим объекты тегов
        return representation
    
    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipeingredient_set')
        tags_data = validated_data.pop('tags')  # Извлекаем теги из validated_data

        # Проверка на пустое поле ingredients
        if not ingredients_data:
            raise serializers.ValidationError({"ingredients": "This field is required."})

        # Проверка на повторяющиеся ингредиенты
        ingredient_ids = [ingredient['ingredient'].id for ingredient in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError({"ingredients": "Duplicate ingredients are not allowed."})

        recipe = Recipe.objects.create(**validated_data)  # Создаем рецепт
        recipe.tags.set(tags_data)  # Добавляем теги к рецепту

        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.pop('ingredient')
            RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, **ingredient_data)

        return recipe
    
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipeingredient_set')
        instance = super().update(instance, validated_data)

        # Удаляем все существующие ингредиенты рецепта
        instance.recipeingredient_set.all().delete()

        # Создаем новые ингредиенты
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.pop('ingredient')
            RecipeIngredient.objects.create(recipe=instance, ingredient=ingredient, **ingredient_data)

        return instance

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return ""


class RecipeLimitedFieldsSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(source='recipeingredient_set', many=True)
    # tags = TagSerializer(many=True, read_only=True)
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all())
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    # is_subscribed = serializers.SerializerMethodField()
    # image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ['id', 'tags', 'author', 'ingredients', 'is_favorited', 'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time']
        extra_kwargs = {
            'image': {'required': False, 'allow_null': True},
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True},
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Изменяем вывод тегов
        tags = instance.tags.all()
        representation['tags'] = TagSerializer(tags, many=True).data  # Выводим объекты тегов
        return representation