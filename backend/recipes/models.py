from django.conf import settings
from django.db import models
from tags.models import Tag

from users.models import User


class Ingredient(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    measurement_unit = models.CharField(
        max_length=200, verbose_name="Ед. измерения"
    )

    class Meta:
        verbose_name = "Ингридиент"
        verbose_name_plural = "Ингридиенты"

    def __str__(self):
        return self.name


class Favorite(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites_recipes",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        "recipes.Recipe",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_favorite"
            )
        ]
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные"

    def __str__(self):
        return f"{self.recipe} теперь в избранном у {self.user} "


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор",
    )
    name = models.CharField(max_length=256, verbose_name="Имя")
    image = models.ImageField(
        upload_to="recipes/images/", verbose_name="Картинка"
    )
    text = models.TextField(verbose_name="Текст")
    cooking_time = models.PositiveIntegerField(verbose_name="Время готовки")
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", verbose_name="Ингридиенты"
    )
    tags = models.ManyToManyField(
        Tag, related_name="recipes", verbose_name="Тэги"
    )
    is_favorited = models.BooleanField(
        default=False, verbose_name="В избранном"
    )
    is_in_shopping_cart = models.BooleanField(
        default=False, verbose_name="В корзине"
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def is_subscribed(self, user):
        return Subscription.objects.filter(user=user, recipe=self).exists()

    def favorites_count(self):
        return self.favorited_by.count()

    def __str__(self):
        return self.name


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Юзверь"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name="Рецепт"
    )

    class Meta:
        unique_together = ("user", "recipe")
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return f"{self.user.username} подписан на {self.recipe.name}"


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name="Рецепт"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, verbose_name="Ингридиент"
    )
    amount = models.PositiveIntegerField(verbose_name="Кол-во")
    name = models.CharField(
        max_length=256, null=True, verbose_name="Название"
    )  # Сделать nullable временно
    measurement_unit = models.CharField(
        max_length=200, null=True, verbose_name="Ед. измерения"
    )

    class Meta:
        verbose_name = "Ингридиент рецепта"
        verbose_name_plural = "Ингридиенты рецептов"

    def save(self, *args, **kwargs):
        if self.ingredient:
            # Заполняем поля на основе связанного объекта Ingredient
            self.name = self.ingredient.name
            self.measurement_unit = self.ingredient.measurement_unit
        super().save(*args, **kwargs)
