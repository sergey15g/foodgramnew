# Generated by Django 4.2.14 on 2024-07-22 18:19

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("recipes", "0004_rename_cooking_time_recipe_cooking_duration"),
    ]

    operations = [
        migrations.RenameField(
            model_name="recipe",
            old_name="cooking_duration",
            new_name="cooking_time",
        ),
    ]
