import django_filters
from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Recipe, Tag


class RecipeFilter(filters.FilterSet):
    tags = filters.AllValuesMultipleFilter(
        field_name="tags__slug",  # Фильтрация по полю slug в связи ManyToMany
    )
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
            return queryset.filter(shopping_cart__user=user)
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_is_subscribed(self, queryset, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return queryset.filter(subscription__user=user)
        return queryset
