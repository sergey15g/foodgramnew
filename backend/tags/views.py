from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.versioning import AcceptHeaderVersioning
from rest_framework.response import Response

from .models import Tag
from .serializers import TagViewSerializer


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by("id")
    serializer_class = TagViewSerializer
    permission_classes = [AllowAny]
    versioning_class = AcceptHeaderVersioning

    def get(self, request, *args, **kwargs):
        version = request.version
        if version == '1.0':
            # Логика для версии 1.0
            data = {"version": "1.0", "message": "This is version 1.0"}
        elif version == '2.0':
            # Логика для версии 2.0
            data = {"version": "2.0", "message": "This is version 2.0"}
        else:
            data = {"error": "Unsupported version"}
        return Response(data)
