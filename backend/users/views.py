import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from recipes.serializers import SubscribeSerializer

from .models import Subscription
from .serializers import (
    SetPasswordSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


class UserPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = "limit"


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = UserPagination

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

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticatedOrReadOnly]
        if self.action in ["set_password", "avatar"]:
            self.permission_classes = [IsAuthenticated]
        return super(UserViewSet, self).get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            response_data = UserRegistrationSerializer(user).data
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticatedOrReadOnly],
        url_path="me",
    )
    def me(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = UserDetailSerializer(
            user, context={"request": request}
        )
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

        if request.method == "PUT" or request.method == "PATCH":
            # Check if avatar is provided in base64 format
            avatar_base64 = request.data.get("avatar")
            if avatar_base64:
                try:
                    # Decode base64 string
                    format, imgstr = avatar_base64.split(";base64,")
                    ext = format.split("/")[-1]
                    data = base64.b64decode(imgstr)
                    # Create a file-like object for Django
                    file_name = f"{user.id}_avatar.{ext}"
                    file = ContentFile(data, file_name)
                    user.avatar = file
                    user.save()
                    return Response(
                        {"avatar": user.avatar.url},
                        status=status.HTTP_200_OK,
                    )
                except Exception as e:
                    return Response(
                        {"detail": "Invalid base64 data.", "error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            return Response(
                {"detail": "No avatar provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "DELETE":
            if user.avatar:
                if default_storage.exists(user.avatar.name):
                    default_storage.delete(user.avatar.name)
                user.avatar = ""  # Set to empty string instead of None
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
        # recipes_limit = request.query_params.get('recipes_limit', None)

        if user == author:
            return Response(
                {"errors": "Нельзя подписаться на самого себя."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "POST":
            if Subscription.objects.filter(
                user=user, subscribed_to=author
            ).exists():
                return Response(
                    {"errors": "Вы уже подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            subscription = Subscription.objects.create(
                user=user, subscribed_to=author
            )
            # if recipes_limit is not None:
            #     subscription.recipes_limit = int(recipes_limit)
            #     subscription.save()
            serializer = self.get_serializer(
                author, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            subscription = Subscription.objects.filter(
                user=user, subscribed_to=author
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

    # def get_permissions(self):
    #     if self.action == "me":
    #         return [IsAuthenticated()]
    #     return super().get_permissions()
