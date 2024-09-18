from recipes.models import ShoppingCart
from recipes.serializers import RecipeReadSerializer
from rest_framework import serializers


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeReadSerializer(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ("id", "user", "recipe")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        recipe = representation["recipe"]
        return {
            "id": recipe["id"],
            "name": recipe["name"],
            "image": recipe["image"],
            "cooking_time": recipe["cooking_time"],
        }


class ShoppingCartCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = "recipe"
