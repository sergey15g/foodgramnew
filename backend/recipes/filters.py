import django_filters
from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Recipe, Tag


class RecipeFilter(django_filters.FilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name="tags__slug",  # Фильтрация по полю slug в связи ManyToMany
        queryset=Tag.objects.all(),
        to_field_name="slug",  # Указывает, что нужно фильтровать по slug
    )

    class Meta:
        model = Recipe
        fields = [
            "tags",
            "author",
        ]

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and not user.is_anonymous:
            return queryset.filter(shopping_cart__user=user)
        return queryset


class TagFilter(filters.FilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name="tags__slug",
        queryset=Tag.objects.all(),
        to_field_name="slug",
        conjoined=False,  # Это позволит использовать логический оператор "ИЛИ"
    )

    class Meta:
        model = Recipe
        fields = []

    def filter_tags(self, queryset, name, value):
        tags = value.split(",")
        query = Q()
        for tag in tags:
            query |= Q(tags__slug=tag)
        return queryset.filter(query).distinct()
