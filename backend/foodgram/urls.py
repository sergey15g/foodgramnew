from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('tags.urls')),
    path('api/', include('recipes.urls')),
    path('api/', include('shopping_cart.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)