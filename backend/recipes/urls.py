from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FavoriteRecipeViewSet,
    IngredientViewSet,
    RecipeViewSet,
    ShoppingCartViewSet,
)

router = DefaultRouter()
router.register(r"recipes", RecipeViewSet, basename="recipe")
router.register(r"ingredients", IngredientViewSet, basename="ingredient")
router.register(
    r"shopping_cart", ShoppingCartViewSet, basename="shopping_cart"
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "recipes/<int:pk>/favorite/",
        FavoriteRecipeViewSet.as_view(
            {"post": "create", "delete": "destroy"}
        ),
        name="favorite",
    ),
    path(
        "recipes/<int:pk>/shopping_cart/",
        ShoppingCartViewSet.as_view(
            {"post": "shopping_cart", "delete": "shopping_cart"}
        ),
        name="recipe-shopping-cart",
    ),
]
