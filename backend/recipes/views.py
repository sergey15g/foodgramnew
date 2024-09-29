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
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.versioning import AcceptHeaderVersioning

from utils.mixins import APIVersionMixin

from .filters import IngredientFilter, RecipeFilter
from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    ShortLink,
)
from .pagination import RecipePagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    FavoriteRecipeSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShoppingCartSerializer,
    ShoppingCartCreateSerializer,
)
from .utils import generate_short_code

logger = logging.getLogger(__name__)


class RecipeViewSet(APIVersionMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by("id")
    serializer_class = RecipeReadSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    pagination_class = RecipePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    versioning_class = AcceptHeaderVersioning

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return RecipeWriteSerializer
        # Для чтения (list, retrieve и т.д.) используем ReadSerializer
        return RecipeReadSerializer

    def get(self, request, *args, **kwargs):
        return self.get_versioned_response(request)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        # Логика получения ссылки на рецепт
        long_link = f"/api/recipes/{recipe.id}/"
        short_link = ShortLink.objects.filter(long_url=long_link).first()
        if not short_link:
            short_code = generate_short_code()
            short_link = ShortLink.objects.create(
                long_url=long_link, short_code=short_code
            )
        link = f"/s/{short_link.short_code}"
        return Response({"short-link": link}, status=status.HTTP_200_OK)

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

        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__in=request.user.recipes_shopping_cart.values_list(
                    'recipe', flat=True
                )
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        if ingredients:
            elements.append(
                Paragraph("Список покупок:", styles["Normal"])
            )
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


class IngredientViewSet(APIVersionMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.DjangoFilterBackend, SearchFilter]
    filterset_class = IngredientFilter
    pagination_class = None
    versioning_class = AcceptHeaderVersioning

    def get(self, request, *args, **kwargs):
        return self.get_versioned_response(request)


class FavoriteRecipeViewSet(APIVersionMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeReadSerializer
    permission_classes = [IsAuthenticated]
    versioning_class = AcceptHeaderVersioning

    def get_serializer_class(self):
        if self.action in ("create", "destroy"):
            return FavoriteRecipeSerializer
        return super().get_serializer_class()

    def get(self, request, *args, **kwargs):
        return self.get_versioned_response(request)

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {"user": request.user.id, "recipe": instance.id}
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )
        return Response(
            {"detail": "Recipe is already in favorites."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ShoppingCartViewSet(APIVersionMixin, viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    permission_classes = [IsAuthenticated]
    versioning_class = AcceptHeaderVersioning

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return ShoppingCartSerializer
        return ShoppingCartCreateSerializer

    def get(self, request, *args, **kwargs):
        return self.get_versioned_response(request)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)

    @action(
        detail=True,
        methods=["get", "post", "delete"],
        url_path="shopping_cart",
    )
    def shopping_cart(self, request, pk=None):
        try:
            recipe = Recipe.objects.get(id=pk)
        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Recipe not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user

        if request.method == "POST":
            shopping_cart, created = ShoppingCart.objects.get_or_create(
                user=user, recipe=recipe
            )
            serializer = ShoppingCartSerializer(shopping_cart)
            return Response(
                serializer.data,
                status=(
                    status.HTTP_201_CREATED
                    if created
                    else status.HTTP_200_OK
                ),
            )

        if request.method == "DELETE":
            shopping_cart = ShoppingCart.objects.filter(
                user=user, recipe=recipe
            )
            if shopping_cart.exists():
                shopping_cart.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"detail": "Recipe not in shopping cart"},
            status=status.HTTP_404_NOT_FOUND,
        )


class ShoppingCartReadViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
