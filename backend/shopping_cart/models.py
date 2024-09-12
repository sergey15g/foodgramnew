from django.contrib.auth import get_user_model
from django.db import models

from recipes.models import Recipe

User = get_user_model()


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shopping_cart"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="in_shopping_cart"
    )

    class Meta:
        unique_together = ("user", "recipe")

    def __str__(self):
        return f"{self.user.username}'s cart - {self.recipe.name}"
