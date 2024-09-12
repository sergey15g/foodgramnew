from rest_framework import serializers
from .models import Recipe, Ingredient, RecipeIngredient
from users.models import User, Subscription
from tags.serializers import TagSerializer, Tag
from users.serializers import UserSerializer
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
import base64


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Если полученный объект строка, и эта строка 
        # начинается с 'data:image'...
        if isinstance(data, str) and data.startswith('data:image'):
            # ...начинаем декодировать изображение из base64.
            # Сначала нужно разделить строку на части.
            format, imgstr = data.split(';base64,')  
            # И извлечь расширение файла.
            ext = format.split('/')[-1]  
            # Затем декодировать сами данные и поместить результат в файл,
            # которому дать название по шаблону.
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


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
    is_favorited = serializers.SerializerMethodField('check_is_in_favourited')
    is_in_shopping_cart = serializers.SerializerMethodField('check_is_in_shopping_cart')
    # is_subscribed = serializers.SerializerMethodField()
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = ['id', 'tags', 'author', 'ingredients', 'is_favorited', 'name', 'image', 'text', 'cooking_time', 'is_in_shopping_cart']
        extra_kwargs = {
            'image': {'required': False, 'allow_null': True},
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True},
        }

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("Поле Тег не может быть пустым.")
        
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Теги дублируются.")
        return value
    
    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError("Время готовки должно быть не менее 1 минуты.")
        return value
    
    def to_internal_value(self, data):
        if 'image' in data and isinstance(data['image'], str):
            try:
                format, imgstr = data['image'].split(';base64,')
            except ValueError:
                raise serializers.ValidationError('Неверный формат картинки')

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
            raise serializers.ValidationError({"ingredients": "Поле обязательно."})

        # Проверка на повторяющиеся ингредиенты
        ingredient_ids = [ingredient['ingredient'].id for ingredient in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError({"ingredients": "Дублирование не применимо."})

        recipe = Recipe.objects.create(**validated_data)  # Создаем рецепт
        recipe.tags.set(tags_data)  # Добавляем теги к рецепту

        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.pop('ingredient')
            RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, **ingredient_data)

        return recipe
    
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        if ingredients_data is None or not ingredients_data:
            raise ValidationError({"ingredients": "Поле обязательно и не может быть пустым."})

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
            return self.context['request'].build_absolute_uri(obj.image.url)
        return ""

    def check_is_in_shopping_cart(self, obj):
        if self.context.get("request") is None:
            return False
        if self.context.get("request").user.is_authenticated and list(self.context.get("request").user.shopping_cart.all().filter(recipe=obj)) != []:
            return True
        return False

    def check_is_in_favourited(self, obj):
        if self.context.get("request") is None:
            return False
        if self.context.get("request").user.is_authenticated and list(self.context.get("request").user.favorites_recipes.all().filter(recipe=obj)) != []:
            return True
        return False


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
        fields = ['id', 'tags', 'author', 'ingredients', 'is_favorited', 'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time', 'is_in_shopping_cart']
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


class RecipeUpdateIngredientSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(source='recipeingredient_set', many=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = '__all__'
    
    def to_internal_value(self, data):
        if 'image' in data and isinstance(data['image'], str):
            try:
                format, imgstr = data['image'].split(';base64,')
            except ValueError:
                raise serializers.ValidationError('Invalid image data')

            ext = format.split('/')[-1]
            data['image'] = ContentFile(base64.b64decode(imgstr), name='image.' + ext)
        return super().to_internal_value(data)

    def get_fields(self):
        fields = super().get_fields()
        # Удаляем поле measurement_unit из вывода
        fields.pop('measurement_unit', None)
        #fields.pop('image', None)
        return fields
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Изменяем вывод тегов
        tags = instance.tags.all()
        representation['tags'] = TagSerializer(tags, many=True).data  # Выводим объекты тегов
        return representation
        
    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return ""
    
    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError("Cooking time must be at least 1 minute.")
        return value
    
    def validate(self, data):
        if self.instance is None and 'ingredients' not in data:
            raise serializers.ValidationError("The 'ingredients' field is required.")
        return data
    
    def update(self, instance, validated_data):
    # Убедитесь, что валидированные данные содержат поля 'tags' и 'ingredients'
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('recipeingredient_set', None)

    # Если отсутствует поле 'ingredients' или 'tags', возвращаем ошибку 400
        if ingredients == [] or ingredients is None:
            raise ValidationError({'recipeingredient_set': 'Поле ingredients обязательно для обновления рецепта'})
        if tags is None:
            raise ValidationError({'tags': 'Поле tags обязательно для обновления рецепта'})

        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError({"tags": "Дублирование не применимо."})

    # Обновляем экземпляр рецепта без полей 'tags' и 'ingredients'
        instance = super().update(instance, validated_data)

    # Обновляем теги и ингредиенты
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_amounts(recipe=instance, ingredients=ingredients)

    # Сохраняем изменения
        instance.save()
        return instance
    
    def create_ingredients_amounts(self, recipe, ingredients):
        ingredient_ids = [ingredient['ingredient'].id for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError({"ingredients": "Дублирование не применимо."})
        for ingredient_data in ingredients:
            ingredient = ingredient_data.pop('ingredient')
            RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, **ingredient_data)


class SubscribeSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(user=request.user, subscribed_to=obj).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipeCustSerializer(recipes, many=True, read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_avatar(self, obj):
        if obj.avatar:
            return self.context['request'].build_absolute_uri(obj.avatar.url)
        return None


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']
    
    def get_image(self, obj):
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return None


class SubscriptionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    recipes_limit = serializers.IntegerField(required=False, default=None)

    class Meta:
        model = Subscription
        fields = ['user', 'recipes', 'recipes_count']

    def get_user(self, obj):
        user = obj.user
        return {
            'email': user.email,
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar': self.context['request'].build_absolute_uri(user.avatar.url) if user.avatar else None,
        }

    def get_recipes(self, obj):
        recipes = Recipe.objects.filter(author=obj.recipe.author)
        return RecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.recipe.author).count()


class CustomUserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )
        extra_kwargs = {
            'id': {'required': True},
        }

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user, subscribed_to=obj).exists()

    def to_representation(self, instance):
        # Проверяем, является ли пользователь анонимным
        if isinstance(instance, User) and instance.is_anonymous:
            # Если пользователь анонимный, удаляем поле 'email' из сериализованных данных
            representation = super().to_representation(instance)
            representation.pop('email', None)
            return representation
        return super().to_representation(instance)
    

class RecipeCustSerializer(ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )