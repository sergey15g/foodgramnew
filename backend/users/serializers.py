# users/serializers.py

from django.contrib.auth import get_user_model
from rest_framework import serializers

from recipes.fields import Base64ImageField

from .models import Subscription

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )
        read_only_fields = ("email",)

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            return (
                request.user.is_authenticated
                and Subscription.objects.filter(
                    user=request.user, subscribed_to=obj
                ).exists()
            )
        return False


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
        )
        extra_kwargs = {
            "avatar": {
                "required": False
            }  # Аватар не обязателен при регистрации
        }

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            password=validated_data["password"],
            avatar=validated_data.get("avatar"),
        )


class UserDetailSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, subscribed_to=obj
            ).exists()
        return False

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else ""


class SetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context["request"].user
        if not user.check_password(data["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Old password is incorrect."}
            )
        if data["current_password"] == data["new_password"]:
            raise serializers.ValidationError(
                {
                    "new_password": (
                        "New password must be different from old password."
                    )
                }
            )
        return data

    def save(self):
        user = self.context["request"].user
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()


# class SubscriptionSerializer(serializers.ModelSerializer):
#     is_subscribed = serializers.SerializerMethodField()
#     recipes = serializers.SerializerMethodField()
#     recipes_count = serializers.ReadOnlyField(source="recipes.count")
#     avatar = serializers.SerializerMethodField()
#
#     class Meta:
#         model = User
#         fields = (
#             "email",
#             "id",
#             "username",
#             "first_name",
#             "last_name",
#             "is_subscribed",
#             "recipes",
#             "recipes_count",
#             "avatar",
#         )
#
#     def validate(self, data):
#         user = data["user"]
#         subscribed_to = data["subscribed_to"]
#
#         if user == subscribed_to:
#             raise serializers.ValidationError(
#                 "Нельзя подписаться на самого себя."
#             )
#
#         if Subscription.objects.filter(user=user,
#                                        subscribed_to=subscribed_to).exists():
#             raise serializers.ValidationError(
#                 "Вы уже подписаны на этого пользователя."
#             )
#
#         return data


class AvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField(required=True)


class SubscriptionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['user', 'is_subscribed']

    def validate(self, data):
        user = data['user']
        author = data['is_subscribed']

        if user == author:
            raise serializers.ValidationError("Нельзя подписаться на самого себя.")

        if Subscription.objects.filter(user=user, subscribed_to=author).exists():
            raise serializers.ValidationError("Вы уже подписаны на этого пользователя.")

        return data

    def create(self, validated_data):
        return Subscription.objects.create(**validated_data)
