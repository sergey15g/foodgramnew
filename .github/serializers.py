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

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'amount']

    # def to_representation(self, instance):
    #     # Добавляем сортировку объектов перед сериализацией
    #     queryset = instance.recipeingredient_set.order_by('id')  # Замените 'id' на поле, по которому нужно сортировать
    #     return super().RecipeIngredientSerializer(queryset)


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(source='recipeingredient_set', many=True)
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all())
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ['id', 'author', 'name', 'image', 'text', 'cooking_time', 'ingredients', 'tags', 'is_favorited', 'is_in_shopping_cart', 'is_subscribed']
        extra_kwargs = {
            'image': {'required': False, 'allow_null': True},
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True},
        }

    def to_internal_value(self, data):
        if 'image' in data and isinstance(data['image'], str):
            # Decode base64 image
            format, imgstr = data['image'].split(';base64,') 
            ext = format.split('/')[-1]
            data['image'] = ContentFile(base64.b64decode(imgstr), name='image.' + ext)
        return super().to_internal_value(data)

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.is_subscribed(user)
        return False
    
    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipeingredient_set')
        recipe = super().create(validated_data)
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.pop('ingredient')
            RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, **ingredient_data)
        return recipe

