# Generated by Django 4.2.14 on 2024-09-12 20:03

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        (
            "recipes",
            "0010_alter_recipe_author_alter_recipe_cooking_time_and_more",
        ),
        ("shopping_cart", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shoppingcart",
            name="recipe",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="in_shopping_cart",
                to="recipes.recipe",
                verbose_name="Рецепт",
            ),
        ),
        migrations.AlterField(
            model_name="shoppingcart",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="shopping_cart",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Юзверь",
            ),
        ),
    ]
