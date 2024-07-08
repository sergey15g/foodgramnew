from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Subscribe
from api.pagination import CustomPagination
from api.permissions import IsAdminOrReadOnly
from api.serializers import (CustomUserCreateSerializer, CustomUserSerializer,
                             SubscribeSerializer)
from users.models import User


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdminOrReadOnly]

    @action(
        detail=False,
        methods=["put", "patch", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
    )
    def set_avatar(self, request: Request):
        user: User = request.user
        if request.method in ["PUT", "PATCH"]:
            avatar = request.FILES.get("avatar")

            if avatar:
                avatar.name = f"{user.id}_{avatar.name}"
                user.avatar = avatar
                user.save()
                return Response(
                    {"status": "Аватарка присвоена"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"detail": "Необходимо предоставить файл аватара."},
                    status=status.HTTP_200_OK,
                )
        elif request.method == "DELETE":
            user.avatar = "avatars/default_avatar.png"
            user.save()
            return Response({"avatar": user.avatar.url},
                            status=status.HTTP_200_OK)
        else:
            return Response(
                {"detail": "Метод не разрешен."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def get_serializer_class(self):
        if self.action == "create":
            return CustomUserCreateSerializer
        elif self.action == "subscribe":
            return SubscribeSerializer
        return super().get_serializer_class()

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)

        if user == author:
            return Response(
                {"errors": "Нельзя подписаться на самого себя."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "POST":
            if Subscribe.objects.filter(user=user, author=author).exists():
                return Response(
                    {"errors": "Вы уже подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Subscribe.objects.create(user=user, author=author)
            serializer = self.get_serializer(author,
                                             context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            subscription = Subscribe.objects.filter(
                user=user, author=author).first()
            if subscription:
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"errors": "Подписка не найдена."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(subscribing__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(pages, many=True,
                                         context={"request": request})
        return self.get_paginated_response(serializer.data)

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        return super().get_permissions()
