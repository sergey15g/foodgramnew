from rest_framework import serializers
from .models import Tag


class TagSerializer(serializers.ModelSerializer):
    # id = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all())

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        # Если нужно, чтобы сериализатор обрабатывал списки объектов
        many = True


class TagViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
