import io

from django.db.models import Sum
from django.http import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from recipes.models import ShoppingCart
from .serializers import (
    ShoppingCartCreateSerializer,
    ShoppingCartSerializer,
)
from recipes.models import Recipe

FILENAME = 'shopping_cart.pdf'


class ShoppingCartViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ShoppingCartSerializer
        return ShoppingCartCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)

    @action(
        detail=True,
        methods=['get', 'post', 'delete'],
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        try:
            recipe = Recipe.objects.get(id=pk)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Recipe not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user

        if request.method == 'POST':
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

        if request.method == 'DELETE':
            shopping_cart = ShoppingCart.objects.filter(
                user=user, recipe=recipe
            )
            if shopping_cart.exists():
                shopping_cart.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Recipe not in shopping cart'},
            status=status.HTTP_404_NOT_FOUND,
        )

    @action(
        detail=False, methods=['get'], url_path='download_shopping_cart'
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
        elements = []

        shopping_cart = (
            request.user.recipes_shopping_cart.recipe.values(
                'ingredients__name', 'ingredients__measurement_unit'
            )
            .annotate(amount=Sum('recipe__amount'))
            .order_by()
        )

        if shopping_cart:
            elements.append(
                Paragraph('Список покупок:', styles['Heading1'])
            )
            elements.append(Spacer(1, 12))

            for index, recipe in enumerate(shopping_cart, start=1):
                text = (
                    f'{index}. {recipe['ingredients__name']} - '
                    f'{recipe['amount']} '
                    f'{recipe['ingredients__measurement_unit']}.'
                )
                elements.append(Paragraph(text, styles['Normal']))
                elements.append(Spacer(1, 12))
        else:
            elements.append(
                Paragraph('Список покупок пуст!', styles['Heading1'])
            )

        doc.build(elements)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=FILENAME)


class ShoppingCartReadViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
