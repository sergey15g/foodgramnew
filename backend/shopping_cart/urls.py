from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShoppingCartViewSet

router = DefaultRouter()
router.register(r'shopping_cart', ShoppingCartViewSet, basename='shopping_cart')

urlpatterns = [
    path('', include(router.urls)),
    # path('recipes/download_shopping_cart/', ShoppingCartReadViewSet.as_view({'get': 'download_shopping_cart'}), name='download_shopping_cart'),
    path('recipes/<int:pk>/shopping_cart/', ShoppingCartViewSet.as_view({'post': 'shopping_cart', 'delete': 'shopping_cart'}), name='recipe-shopping-cart'),
]