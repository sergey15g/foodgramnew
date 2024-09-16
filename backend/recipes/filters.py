import django_filters
from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Recipe, Tag


class RecipeFilter(django_filters.FilterSet):
    tags = django_filters.AllValuesMultipleFilter(
        field_name="tags__slug",  # Фильтрация по полю slug в связи ManyToMany
    )
    is_in_shopping_cart = django_filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )
    is_favorited = django_filters.BooleanFilter(
        method='filter_is_favorited'
    )

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


# class TagFilter(filters.FilterSet):
#     tags = django_filters.ModelMultipleChoiceFilter(
#         field_name='tags__slug',
#         queryset=Tag.objects.all(),
#         to_field_name='slug',
#         conjoined=False,  # Это позволит использовать логический оператор "ИЛИ"
#     )
#
#     class Meta:
#         model = Recipe
#         fields = []
#
#     def filter_tags(self, queryset, name, value):
#         tags = value.split(",")
#         query = Q()
#         for tag in tags:
#             query |= Q(tags__slug=tag)
#         return queryset.filter(query).distinct()
