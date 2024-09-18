# recipes/management/commands/import_csv.py
import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from recipes.models import Ingredient

CSV_FILES_MAP = {
    Ingredient: "ingredients.csv",
}

EXPECTED_FIELDS = ["name", "measurement_unit"]


class Command(BaseCommand):
    help = "Импорт данных из CSV файлов"

    def add_arguments(self, parser):
        parser.add_argument(
            "--directory",
            type=str,
            help="Путь к директории с CSV файлами."
            " По умолчанию используется путь из настроек.",
        )

    def handle(self, *args, **options):
        csv_directory = (
            options["directory"] if options["directory"] else settings.CSV_DIR
        )

        for model, csv_filename in CSV_FILES_MAP.items():
            model.objects.all().delete()
            file_path = os.path.join(csv_directory, csv_filename)

            if not os.path.isfile(file_path):
                raise CommandError(f"Файл {file_path} не найден.")

            self.stdout.write(
                self.style.NOTICE(
                    f"Начало импорта данных из файла {file_path}"
                )
            )

            with open(file_path, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                if reader.fieldnames != EXPECTED_FIELDS:
                    raise CommandError(
                        "Неверный формат файла: неправильные заголовки полей."
                    )

                instances = [model(**data) for data in reader]
                model.objects.bulk_create(instances)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Импорт данных в модель {model.__name__} завершен"
                )
            )

        self.stdout.write(
            self.style.SUCCESS("Импорт всех данных успешно завершен.")
        )
