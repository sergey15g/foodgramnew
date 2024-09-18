from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
from tags.serializers import Tag, TagSerializer
from users.models import Subscription, User
from users.serializers import UserSerializer

from .fields import Base64ImageField
from .models import Favorite, Ingredient, Recipe, RecipeIngredient


class RecipeCustSerializer(ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class RecipeIngredientManager:
    @staticmethod
    def create_recipe_ingredient(recipe, ingredient_data):
        ingredient = ingredient_data.pop("ingredient")
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            **ingredient_data,
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
    ingredients = RecipeIngredientSerializer(
        source="recipeingredient_set", many=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "is_favorited",
            "ingredients",
            "name",
            "image",
            "text",
            "cooking_time",
        )
        extra_kwargs = {
            "image": {"required": False, "allow_null": True},
            "name": {"required": True},
            "text": {"required": True},
            "cooking_time": {"required": True},
        }

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                "Поле Тег не может быть пустым."
            )

        if len(value) != len(set(value)):
            raise serializers.ValidationError("Теги дублируются.")
        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                {"ingredients": "Поле обязательно."}
            )

        ingredient_ids = [
            ingredient["ingredient"].id for ingredient in value
        ]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {"ingredients": "Дублирование не применимо."}
            )
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop("recipeingredient_set")
        tags_data = validated_data.pop("tags")

        recipe = Recipe.objects.create(**validated_data)  # Создаем рецепт
        recipe.tags.set(tags_data)  # Добавляем теги к рецепту

        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data.pop("ingredient"),
                **ingredient_data,
            )
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        if ingredients_data is None or not ingredients_data:
            raise ValidationError(
                {
                    "ingredients": "Поле обязательно и не может быть пустым."
                }
            )

        instance = super().update(instance, validated_data)

        # Удаляем все существующие ингредиенты рецепта
        instance.recipeingredient_set.all().delete()

        # Создаем новые ингредиенты
        for ingredient_data in ingredients_data:
            RecipeIngredientManager.create_recipe_ingredient(
                instance, ingredient_data
            )

        return instance


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

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Изменяем вывод тегов
        tags = instance.tags.all()
        representation["tags"] = TagSerializer(
            tags, many=True
        ).data  # Выводим объекты тегов
        return representation

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
        if (
            self.context.get("request").user.is_authenticated
            and list(
                self.context.get("request")
                .user.favorites.all()
                .filter(recipe=obj)
            )
            != []
        ):
            return True
        return False

    def create(self, validated_data):
        ingredients_data = validated_data.pop("recipeingredient_set", [])
        tags_data = validated_data.pop("tags", [])
        validated_data["author"] = self.context["request"].user

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        if ingredients_data == []:
            raise serializers.ValidationError("Ингридиенты отсутствуют")

        ingredient_ids = [
            ingredient["ingredient"].id for ingredient in ingredients_data
        ]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {"ingredients": "Дублирование не применимо."}
            )

        for ingridient in ingredients_data:
            if ingridient["amount"] < 1:
                raise serializers.ValidationError(
                    {"ingredients": "Кол-во ингридиентов не меньше 1"}
                )

        if tags_data == []:
            raise serializers.ValidationError("Теги отсутствуют")

        tag_ids = [tag.id for tag in tags_data]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {"tags": "Дублирование не применимо."}
            )

        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.pop("ingredient")
            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=ingredient, **ingredient_data
            )

        try:
            if (
                validated_data["image"] is None
                or validated_data["image"] == ""
            ):
                raise serializers.ValidationError(
                    {"image": "Изображение нельзя оставить пустым"}
                )
        except Exception:
            raise serializers.ValidationError(
                {"image": "Изображение нельзя оставить пустым"}
            )

        return recipe


class RecipeLimitedFieldsSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="recipeingredient_set", many=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
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

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Изменяем вывод тегов
        tags = instance.tags.all()
        representation["tags"] = TagSerializer(
            tags, many=True
        ).data  # Выводим объекты тегов
        return representation


class RecipeUpdateIngredientSerializer(serializers.ModelSerializer):
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
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = "__all__"

    def check_is_in_favourited(self, obj):
        if self.context.get("request") is None:
            return False
        if (
            self.context.get("request").user.is_authenticated
            and list(
                self.context.get("request")
                .user.favorites.all()
                .filter(recipe=obj)
            )
            != []
        ):
            return True
        return False

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

    def to_internal_value(self, data):
        return super().to_internal_value(data)

    def get_fields(self):
        fields = super().get_fields()
        # Удаляем поле measurement_unit из вывода
        fields.pop("measurement_unit", None)
        return fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Изменяем вывод тегов
        tags = instance.tags.all()
        representation["tags"] = TagSerializer(
            tags, many=True
        ).data  # Выводим объекты тегов
        return representation

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return ""

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Cooking time must be at least 1 minute."
            )
        return value

    def validate(self, data):
        if self.instance is None and "ingredients" not in data:
            raise serializers.ValidationError(
                "The 'ingredients' field is required."
            )
        return data

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

        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {"tags": "Дублирование не применимо."}
            )

        for ingridient in ingredients:
            if ingridient["amount"] < 1:
                raise serializers.ValidationError(
                    {"ingredients": "Кол-во ингридиентов не меньше 1"}
                )

        try:
            if (
                validated_data["image"] == ""
                or validated_data["image"] is None
            ):
                raise serializers.ValidationError(
                    {"image": "Изображение нельзя оставить пустым"}
                )
        except Exception:
            pass

        # Обновляем экземпляр рецепта без полей 'tags' и 'ingredients'
        instance = super().update(instance, validated_data)

        # Обновляем теги и ингредиенты
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_amounts(
            recipe=instance, ingredients=ingredients
        )

        # Сохраняем изменения
        instance.save()
        return instance

    def validate_ingredients(self, value):
        ingredient_ids = [
            ingredient["ingredient"].id for ingredient in value
        ]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Дублирование ингредиентов не допускается."
            )
        return value

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)
        self.create_ingredients_amounts(recipe, ingredients)
        return recipe

    def create_ingredients_amounts(self, recipe, ingredients):
        for ingredient in ingredients:
            RecipeIngredient.objects.create(recipe=recipe, **ingredient)


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

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user.recipes_subscriptions.filter(
                author=obj
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


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = "id"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        recipe = Favorite.objects.get(pk=representation["id"]).recipe
        return {
            "id": recipe.id,
            "name": recipe.name,
            "image": recipe.image.url,
            "cooking_time": recipe.cooking_time,
        }

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
        return {
            "email": user.email,
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar": (
                self.context["request"].build_absolute_uri(
                    user.avatar.url
                )
                if user.avatar
                else None
            ),
        }

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
