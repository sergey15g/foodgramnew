from django.contrib import admin
from django.contrib.admin import display
from unfold.admin import ModelAdmin

from tags.models import Tag

from .models import Favorite, Ingredient, Recipe, RecipeIngredient


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug")
    list_filter = ("name",)
    search_fields = ("name", "slug")


@admin.register(Ingredient)
class IngredientAdmin(ModelAdmin):
    list_display = (
        "name",
        "measurement_unit",
    )
    list_filter = ("name",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "author", "added_in_favorites")
    readonly_fields = ("added_in_favorites",)
    search_fields = ("name", "author__username", "author__email")
    list_filter = (
        "author",
        "name",
        "tags",
    )

    @display(description="Количество в избранных")
    def added_in_favorites(self, obj):
        return obj.favorites_count()


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(ModelAdmin):
    list_display = (
        "recipe",
        "ingredient",
        "amount",
    )


admin.site.register(Favorite)
