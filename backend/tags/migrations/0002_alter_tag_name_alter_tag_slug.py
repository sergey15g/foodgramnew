# Generated by Django 4.2.14 on 2024-09-12 20:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tags", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tag",
            name="name",
            field=models.CharField(max_length=200, verbose_name="Название"),
        ),
        migrations.AlterField(
            model_name="tag",
            name="slug",
            field=models.SlugField(unique=True, verbose_name="Слаг"),
        ),
    ]
