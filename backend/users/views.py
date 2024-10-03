
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.versioning import AcceptHeaderVersioning

from recipes.serializers import SubscribeSerializer
from utils.mixins import APIVersionMixin

from .models import Subscription
from .pagination import UserPagination
from .permissions import IsAuthenticatedUser, IsOwnerOrReadOnly
from .serializers import (
    AvatarSerializer,
    SetPasswordSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


class UserViewSet(APIVersionMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = UserPagination
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']
    permission_classes = [IsAuthenticatedUser]
    versioning_class = AcceptHeaderVersioning

    def get_serializer_class(self):
        if self.action == "list":
            return UserSerializer
        if self.action == "retrieve":
            return UserDetailSerializer
        if self.action == "create":
            return UserRegistrationSerializer
        if self.action == "set_password":
            return SetPasswordSerializer
        if self.action in ["avatar"]:
            return UserDetailSerializer
        if self.action == "subscribe":
            return SubscribeSerializer
        return UserSerializer

    def get(self, request, *args, **kwargs):
        return self.get_versioned_response(request)

    def get_permissions(self):
        if self.action in ["create", "get"]:
            self.permission_classes = [AllowAny]
        elif self.action in (
                ["set_password", "avatar", "subscribe", "subscriptions", "me"]
        ):
            self.permission_classes = [IsOwnerOrReadOnly]
        elif self.action == "retrieve":
            self.permission_classes = [IsAuthenticatedOrReadOnly]
        else:
            self.permission_classes = [IsAuthenticatedOrReadOnly]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            response_data = UserRegistrationSerializer(user).data
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=["get"], url_path="me",
            permission_classes=[IsAuthenticated]
            )
    def me(self, request, *args, **kwargs):
        user = request.user
        serializer = UserDetailSerializer(user, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="set_password",
    )
    def set_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar(self, request, *args, **kwargs):
        user = request.user

        if request.method in ["PUT", "PATCH"]:
            serializer = AvatarSerializer(data=request.data)
            if serializer.is_valid():
                avatar = serializer.validated_data["avatar"]
                user.avatar = avatar
                user.save()
                return Response(
                    {"avatar": user.avatar.url}, status=status.HTTP_200_OK
                )
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == "DELETE":
            if user.avatar:
                if default_storage.exists(user.avatar.name):
                    default_storage.delete(user.avatar.name)
                user.avatar = ""
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
    )
    def subscribe(self, request, pk=None):
        user = request.user
        author = get_object_or_404(User, id=pk)

        if user == author:
            return Response(
                {"errors": "Нельзя подписаться на самого себя."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "POST":
            # Использование сериализатора для создания подписки
            data = {
                "subscribed_to": author.id
            }

            # Передаем данные в сериализатор
            serializer = SubscribeSerializer(author, data=data, context={"request": request})

            # Вызов метода is_valid для проверки всех валидаторов
            serializer.is_valid(raise_exception=True)

            # Создание подписки, если валидаторы прошли успешно
            Subscription.objects.create(user=user, subscribed_to=author)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            # Использование сериализатора для валидации существования подписки
            serializer = SubscribeSerializer(
                author, context={"request": request}
            )
            serializer.validate_for_delete(user=user, author=author)

            # Удаление подписки
            subscription = Subscription.objects.filter(user=user,
                                                       subscribed_to=author
                                                       ).first()
            if subscription:
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            return Response(
                {"errors": "Подписка не найдена."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request, *args, **kwargs):
        user = request.user
        queryset = User.objects.filter(users_subscribers__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)
