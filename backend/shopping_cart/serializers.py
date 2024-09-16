from rest_framework import serializers

from recipes.models import ShoppingCart
from recipes.serializers import RecipeReadSerializer


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeReadSerializer(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ["id", "user", "recipe"]


class ShoppingCartCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ["recipe"]
