from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FavoriteRecipeViewSet, IngredientViewSet, RecipeViewSet

router = DefaultRouter()
router.register(r"recipes", RecipeViewSet, basename="recipe")
router.register(r"ingredients", IngredientViewSet, basename="ingredient")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "recipes/<int:pk>/favorite/",
        FavoriteRecipeViewSet.as_view(
            {"post": "create", "delete": "destroy"}
        ),
        name="favorite",
    ),
]
