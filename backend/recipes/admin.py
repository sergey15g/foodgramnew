from django.contrib import admin
from django.contrib.admin import display

from .models import Favorite, Ingredient, Recipe, RecipeIngredient


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "measurement_unit",
    )
    list_filter = ("name",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "author", "added_in_favorites")
    readonly_fields = ("added_in_favorites",)
    list_filter = (
        "author",
        "name",
        "tags",
    )

    @display(description="Количество в избранных")
    def added_in_favorites(self, obj):
        return obj.favorites_count()


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = (
        "recipe",
        "ingredient",
        "amount",
    )


admin.site.register(Favorite)
