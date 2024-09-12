import io
import logging

from django.db.models import Q, Sum
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from shopping_cart.models import ShoppingCart
from shopping_cart.serializers import ShoppingCartSerializer

from .filters import RecipeFilter, TagFilter
from .models import Favorite, Ingredient, Recipe
from .pagination import RecipePagination
from .serializers import (FavoriteRecipeSerializer, IngredientSerializer,
                          RecipeLimitedFieldsSerializer, RecipeSerializer,
                          RecipeUpdateIngredientSerializer)

logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont("Times-Roman", "times.ttf"))


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by("id")
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = RecipePagination
    filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['tags']
    filterset_class = RecipeFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        tag_slugs = self.request.query_params.getlist("tags")
        if (
            self.request.query_params.get("is_in_shopping_cart") == "1"
            and self.request.user.is_authenticated
        ):
            queryset = queryset.filter(
                in_shopping_cart__user=self.request.user
            )
        if (
            self.request.query_params.get("is_favorited") == "1"
            and self.request.user.is_authenticated
        ):
            queryset = queryset.filter(favorited_by__user=self.request.user)
        if tag_slugs:
            return queryset.filter(Q(tags__slug__in=tag_slugs)).distinct()
        return queryset

    def get_serializer_class(self):
        if "tags" in self.request.query_params:
            return RecipeLimitedFieldsSerializer

        if self.action in ["update", "partial_update"]:
            return RecipeUpdateIngredientSerializer

        # elif self.action in ['destroy']:
        #     return RecipeUpdateIngredientSerializer
        return super().get_serializer_class()

    def get_filterset_class(self):
        if "tags" in self.request.query_params:
            return TagFilter
        return super().get_filterset_class()

    def list(self, request, *args, **kwargs):
        logger.info(f"Request query params: {request.query_params}")
        queryset = self.filter_queryset(self.get_queryset())

        if "tags" in request.query_params:
            filterset_class = self.get_filterset_class()
            if filterset_class:
                filterset = filterset_class(
                    request.query_params, queryset=queryset
                )
                if filterset.is_valid():
                    queryset = filterset.qs
                    logger.info(
                        f"Filtered queryset count: {queryset.count()}"
                    )
                else:
                    return Response(
                        filterset.errors, status=status.HTTP_400_BAD_REQUEST
                    )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            response = {
                "id": serializer.data["recipe"]["id"],
                "name": serializer.data["recipe"]["name"],
                "image": serializer.data["recipe"]["image"],
                "cooking_time": serializer.data["recipe"]["cooking_time"],
            }
            return Response(
                response, status=status.HTTP_201_CREATED if created else 400
            )

        if request.method == "DELETE":
            shopping_cart = ShoppingCart.objects.filter(
                user=user, recipe=recipe
            )
            if shopping_cart.exists():
                shopping_cart.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Recipe not in shopping cart"}, status=400)

    @action(detail=False, methods=["get"], url_path="download_shopping_cart")
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

        shopping_cart_items = request.user.shopping_cart.all()
        recipes = [item.recipe for item in shopping_cart_items]

        ingredients = (
            Recipe.objects.filter(id__in=[recipe.id for recipe in recipes])
            .values("ingredients__name", "ingredients__measurement_unit")
            .annotate(amount=Sum("recipeingredient__amount"))
            .order_by()
        )

        if ingredients:
            elements.append(Paragraph("Список покупок:", styles["Normal"]))
            elements.append(Spacer(1, 12))

            for index, ingredient in enumerate(ingredients, start=1):
                text = (
                    f'{index}. {ingredient["ingredients__name"]} -'
                    f' {ingredient["amount"]} '
                    f'{ingredient["ingredients__measurement_unit"]}.'
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


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request, *args, **kwargs):
        name = request.query_params.get("name", None)
        if name:
            queryset = self.queryset.filter(name__istartswith=name)
        else:
            queryset = self.queryset

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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

    @action(detail=True, methods=["post"])
    def favorite(self, request, pk=None):
        instance = self.get_object()
        request.user.favorite_recipe.recipe.add(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def unfavorite(self, request, pk=None):
        instance = self.get_object()
        request.user.favorite_recipe.recipe.remove(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteRecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

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
