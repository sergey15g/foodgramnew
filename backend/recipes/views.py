import io
import logging
from http import HTTPStatus

from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from shopping_cart.serializers import ShoppingCartSerializer

from .filters import IngredientFilter, RecipeFilter
from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)
from .pagination import RecipePagination
from .serializers import (
    FavoriteRecipeSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeUpdateIngredientSerializer,
)

logger = logging.getLogger(__name__)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by("id")
    serializer_class = RecipeReadSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = RecipePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_queryset(self):
        queryset = super().get_queryset()

        return queryset

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return RecipeUpdateIngredientSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        if "image" not in request.data or request.data["image"] == "":
            raise ValidationError({"image": "This field is required."})
        # Обрабатываем POST запрос на создание нового рецепта
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers,
            )
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        # Логика получения ссылки на рецепт
        link = f"/api/recipes/{recipe.id}/"
        return Response({"short-link": link}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()

        # Проверка, является ли текущий пользователь автором рецепта
        if instance.author != request.user:
            raise PermissionDenied(
                "You do not have permission to update this recipe."
            )

        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)

        return Response(status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Проверка, является ли текущий пользователь автором рецепта
        if instance.author != request.user:
            raise PermissionDenied(
                "You do not have permission to update this recipe."
            )

        instance.delete()

        return Response({"detail": "DELETED"}, status=204)

    def perform_destroy(self, instance):
        instance.delete()

    def _handle_post_request(self, request, pk, model, serializer_class):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        instance, created = model.objects.get_or_create(
            user=user, recipe=recipe
        )
        serializer = serializer_class(instance)
        response = serializer.data
        return Response(
            response,
            status=(
                status.HTTP_201_CREATED
                if created
                else HTTPStatus.BAD_REQUEST
            ),
        )

    def _handle_delete_request(self, request, pk, model):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        instance = model.objects.filter(user=user, recipe=recipe)
        if instance.exists():
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"detail": "Recipe not found in the list"},
            status=HTTPStatus.BAD_REQUEST,
        )

    @action(detail=True, methods=["post"])
    def shopping_cart(self, request, pk=None):
        return self._handle_post_request(
            request, pk, ShoppingCart, ShoppingCartSerializer
        )

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        return self._handle_delete_request(request, pk, ShoppingCart)

    @action(detail=True, methods=["post"])
    def favorite(self, request, pk=None):
        return self._handle_post_request(
            request, pk, Favorite, FavoriteRecipeSerializer
        )

    @favorite.mapping.delete
    def remove_from_favorite(self, request, pk=None):
        return self._handle_delete_request(request, pk, Favorite)

    @action(
        detail=False, methods=["get"], url_path="download_shopping_cart"
    )
    def download_shopping_cart(self, request):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=18,
        )
        styles = getSampleStyleSheet()
        styles["Normal"].fontName = "Times-Roman"  # Установка шрифта
        elements = []

        # Получаем все рецепты в корзине пользователя
        shopping_cart_items = request.user.recipes_shopping_cart.all()
        recipe_ids = [item.recipe.id for item in shopping_cart_items]

        # Получаем все ингредиенты в рецептах в корзине пользователя
        ingredients = (
            RecipeIngredient.objects.filter(recipe__id__in=recipe_ids)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        if ingredients:
            elements.append(Paragraph("Список покупок:", styles["Normal"]))
            elements.append(Spacer(1, 12))

            for index, ingredient in enumerate(ingredients, start=1):
                text = (
                    f'{index}. {ingredient["ingredient__name"]} -'
                    f' {ingredient["total_amount"]} '
                    f'{ingredient["ingredient__measurement_unit"]}.'
                )
                elements.append(Paragraph(text, styles["Normal"]))
                elements.append(Spacer(1, 12))
        else:
            elements.append(
                Paragraph("Список покупок пуст!", styles["Heading1"])
            )

        doc.build(elements)
        buffer.seek(0)
        return FileResponse(
            buffer, as_attachment=True, filename="shopping_cart.pdf"
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.DjangoFilterBackend, SearchFilter]
    filterset_class = IngredientFilter
    pagination_class = None

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # @action(detail=True, methods=["post"])
    # def favorite(self, request, pk=None):
    #     instance = self.get_object()
    #     request.user.favorite_recipe.recipe.add(instance)
    #     serializer = self.get_serializer(instance)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)
    #
    # @favorite.mapping.delete
    # def unfavorite(self, request, pk=None):
    #     instance = self.get_object()
    #     request.user.favorite_recipe.recipe.remove(instance)
    #     return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteRecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeReadSerializer

    def get_serializer_class(self):
        if self.action == "create" or self.action == "destroy":
            return FavoriteRecipeSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            return Response(status=401)
        instance = self.get_object()
        _, created = Favorite.objects.get_or_create(
            user=request.user, recipe=instance
        )
        if created:
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(
            {"detail": "Recipe is already in favorites."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            return Response(status=401)
        instance = self.get_object()
        favorite = Favorite.objects.filter(
            user=request.user, recipe=instance
        ).first()
        if favorite:
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"detail": "Recipe is not in favorites."},
            status=status.HTTP_400_BAD_REQUEST,
        )
