from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from tags.serializers import Tag, TagSerializer
from django.shortcuts import get_object_or_404
from users.models import Subscription, User
from users.serializers import UserSerializer

from .fields import Base64ImageField
from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source="ingredient"
    )  # Используем только ID
    name = serializers.CharField(source="ingredient.name", read_only=True)
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit", read_only=True
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeWriteSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="recipeingredient_set", many=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(
        read_only=True
    )
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "name",
            "image",
            "text",
            "cooking_time",
            "is_in_shopping_cart",
        )
        extra_kwargs = {
            "image": {"required": False, "allow_null": True},
            "name": {"required": True},
            "text": {"required": True},
            "cooking_time": {"required": True},
        }

    def validate(self, data):
        tags = data.get("tags", [])
        ingredients = data.get("recipeingredient_set", [])
        image = data.get("image")

        # Проверка на пустые теги
        if not tags:
            raise serializers.ValidationError(
                {"tags": "Поле Тег не может быть пустым."}
            )

        # Проверка на уникальность тегов
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {"tags": "Дублирование не применимо."}
            )

        # Проверка на уникальность ингредиентов
        ingredient_ids = [
            ingredient["ingredient"].id for ingredient in ingredients
        ]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {"ingredients": "Дублирование не применимо."}
            )

        # Проверка на изображение
        if image is None or image == "":
            raise serializers.ValidationError(
                {"image": "Изображение нельзя оставить пустым"}
            )

        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop("recipeingredient_set", [])
        tags_data = validated_data.pop("tags", [])
        validated_data["author"] = self.context["request"].user

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        if not ingredients_data:
            raise serializers.ValidationError("Ингридиенты отсутствуют")

        self.create_recipe_ingredients(recipe, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        ingredients = validated_data.pop("recipeingredient_set", None)

        if not ingredients:
            raise ValidationError(
                {
                    "recipeingredient_set": (
                        "Поле ingredients обязательно для обновления рецепта"
                    )
                }
            )

        if tags is None:
            raise ValidationError(
                {"tags": "Поле tags обязательно для обновления рецепта"}
            )

        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_recipe_ingredients(instance, ingredients)
        instance.save()

        return instance

    def create_recipe_ingredients(self, recipe, ingredients_data):
        recipe_ingredients = []
        for ingredient_data in ingredients_data:
            recipe_ingredient = RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data.pop("ingredient"),
                **ingredient_data,
            )
            try:
                recipe_ingredient.full_clean()
                recipe_ingredients.append(recipe_ingredient)
            except DjangoValidationError as e:
                raise serializers.ValidationError(
                    {"amount": e.messages}
                )

        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        return (
            request.user.is_authenticated
            and request.user.favorites.filter(recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        return (
            request.user.is_authenticated
            and request.user.recipes_shopping_cart.filter(
                recipe=obj
            ).exists()
        )

    def to_representation(self, instance):
        return RecipeReadSerializer(instance).data


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="recipeingredient_set", many=True
    )
    is_favorited = serializers.SerializerMethodField(
        "check_is_in_favourited"
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        "check_is_in_shopping_cart"
    )
    image = Base64ImageField(required=False, allow_null=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "name",
            "image",
            "text",
            "cooking_time",
            "is_in_shopping_cart",
        )
        extra_kwargs = {
            "image": {"required": False, "allow_null": True},
            "name": {"required": True},
            "text": {"required": True},
            "cooking_time": {"required": True},
        }

    def get_is_subscribed(self, obj):
        user = self.context["request"].user
        if user.is_authenticated:
            return obj.is_subscribed(user)
        return False

    def get_image(self, obj):
        if obj.image:
            return self.context["request"].build_absolute_uri(
                obj.image.url
            )
        return ""

    def check_is_in_shopping_cart(self, obj):
        if self.context.get("request") is None:
            return False

        if self.context.get("request").user.is_authenticated:
            return (
                self.context.get("request")
                .user.recipes_shopping_cart.filter(recipe=obj)
                .exists()
            )

        return False

    def check_is_in_favourited(self, obj):
        if self.context.get("request") is None:
            return False

        user = self.context.get("request").user
        if (
            user.is_authenticated
            and user.favorites.filter(recipe=obj).exists()
        ):
            return True

        return False


class RecipeLimitedFieldsSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="recipeingredient_set", many=True
    )
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
            "is_in_shopping_cart",
        )
        extra_kwargs = {
            "image": {"required": False, "allow_null": True},
            "name": {"required": True},
            "text": {"required": True},
            "cooking_time": {"required": True},
        }


class SubscribeSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source="recipes.count")
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
            "avatar",
        )
        read_only_fields = ('email', 'username', 'first_name', 'last_name')

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user.users_subscriptions.filter(
                subscribed_to=obj
            ).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get("request")
        limit = request.GET.get("recipes_limit")
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[: int(limit)]
        serializer = RecipeCustSerializer(
            recipes, many=True, read_only=True
        )
        return serializer.data

    def get_avatar(self, obj):
        if obj.avatar:
            return self.context["request"].build_absolute_uri(
                obj.avatar.url
            )
        return None

    def validate(self, data):
        request = self.context.get("request")
        user = request.user
        author = self.instance  # Получаем автора из переданных данных

        # Проверка, что пользователь не подписывается на самого себя
        if user == author:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя."
            )

        # Проверка, что подписка уже не существует
        if Subscription.objects.filter(user=user,
                                       subscribed_to=author
                                       ).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого пользователя."
            )

        return data

    def validate_for_delete(self, user, author):
        # Проверка существования подписки
        if not Subscription.objects.filter(user=user,
                                           subscribed_to=author
                                           ).exists():
            raise serializers.ValidationError("Подписка не найдена.")

    def validate_for_delete(self, user, author):
        # Проверка существования подписки
        if not Subscription.objects.filter(user=user,
                                           subscribed_to=author
                                           ).exists():
            raise serializers.ValidationError("Подписка не найдена.")

    def create(self, validated_data):
        # Создаем объект подписки
        user = self.context['request'].user
        author = self.instance  # Используем self.instance для автора

        # Создание подписки
        subscription = Subscription.objects.create(user=user, subscribed_to=author)
        return subscription


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id",)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        favorite = get_object_or_404(Favorite, pk=representation["id"])
        recipe = favorite.recipe
        short_serializer = RecipeCustSerializer(recipe)
        return short_serializer.data

    def get_image(self, obj):
        if obj.image:
            return self.context["request"].build_absolute_uri(
                obj.image.url
            )
        return None


class SubscriptionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    recipes_limit = serializers.IntegerField(required=False, default=None)

    class Meta:
        model = Subscription
        fields = ("user", "recipes", "recipes_count")

    def get_user(self, obj):
        user = obj.user
        user_serializer = UserSerializer(user, context=self.context)
        return user_serializer.data

    def get_recipes(self, obj):
        recipes = Recipe.objects.filter(author=obj.recipe.author)
        return RecipeCustSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.recipe.author).count()


class CustomUserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )
        extra_kwargs = {
            "id": {"required": True},
        }

    def get_is_subscribed(self, obj):
        user = self.context.get("request").user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=user, subscribed_to=obj
        ).exists()

    def to_representation(self, instance):
        if isinstance(instance, User) and instance.is_anonymous:
            representation = super().to_representation(instance)
            representation.pop("email", None)
            return representation
        return super().to_representation(instance)


class RecipeCustSerializer(ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Форматируем URL изображения, если оно присутствует
        representation["image"] = (
            instance.image.url
            if instance.image else None
        )
        return representation


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeShortSerializer(source='recipe', read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ("recipe",)  # Оставляем только поле recipe

    def to_representation(self, instance):
        # Возвращаем сериализованные данные рецепта
        return RecipeShortSerializer(instance.recipe).data


class ShoppingCartCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ("recipe",)
