# Generated by Django 4.2.14 on 2024-07-18 18:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("recipes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShoppingCart",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="in_shopping_cart",
                        to="recipes.recipe",
                    ),
                ),
            ],
        ),
    ]
