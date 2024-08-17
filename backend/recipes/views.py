from rest_framework import viewsets
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Recipe, Ingredient
from .serializers import RecipeSerializer, IngredientSerializer, RecipeLimitedFieldsSerializer
from .pagination import RecipePagination
from .filters import RecipeFilter, TagFilter
from django.db.models import Q
from rest_framework.exceptions import ValidationError, PermissionDenied
import logging

logger = logging.getLogger(__name__)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('id')
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = RecipePagination
    filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['tags']
    # filterset_class = RecipeFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        tag_slugs = self.request.query_params.getlist('tags')
        if tag_slugs:
            queryset = queryset.filter(
                Q(tags__slug__in=tag_slugs)
            ).distinct()
        return queryset

    def get_serializer_class(self):
        if 'tags' in self.request.query_params:
            return RecipeLimitedFieldsSerializer
        return super().get_serializer_class()

    def get_filterset_class(self):
        if 'tags' in self.request.query_params:
            return TagFilter
        return super().get_filterset_class()

    def list(self, request, *args, **kwargs):
        logger.info(f"Request query params: {request.query_params}")
        queryset = self.filter_queryset(self.get_queryset())

        if 'tags' in request.query_params:
            filterset_class = self.get_filterset_class()
            if filterset_class:
                filterset = filterset_class(request.query_params, queryset=queryset)
                if filterset.is_valid():
                    queryset = filterset.qs
                    logger.info(f"Filtered queryset count: {queryset.count()}")
                else:
                    return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if 'image' not in request.data or request.data['image'] == "":
            raise ValidationError({"image": "This field is required."})
        # Обрабатываем POST запрос на создание нового рецепта
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        # Логика получения ссылки на рецепт
        link = f"/api/recipes/{recipe.id}/"
        return Response({'short-link': link}, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Проверка, является ли текущий пользователь автором рецепта
        if instance.author != request.user:
            raise PermissionDenied("You do not have permission to update this recipe.")

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request, *args, **kwargs):
        name = request.query_params.get('name', None)
        if name:
            queryset = self.queryset.filter(name__istartswith=name)
        else:
            queryset = self.queryset

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
