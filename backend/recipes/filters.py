from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Recipe, Ingredient


class RecipeFilter(filters.FilterSet):
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')

    class Meta:
        model = Recipe
        fields = [
            'tags',
            'author',
            "is_in_shopping_cart",
            "is_favorited",
        ]

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return queryset.filter(recipes_in_shopping_cart__user=user)
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return queryset.filter(favorited_by__user=user)
        return queryset

    def filter_is_subscribed(self, queryset, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return queryset.filter(subscription__user=user)
        return queryset


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']
