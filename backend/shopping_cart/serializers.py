from rest_framework import serializers

from .models import ShoppingCart
from recipes.serializers import RecipeSerializer


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ["id", "user", "recipe"]


class ShoppingCartCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ["recipe"]
