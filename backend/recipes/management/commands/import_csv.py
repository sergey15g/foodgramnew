# recipes/management/commands/import_csv.py
import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from recipes.models import Ingredient

MODELS_CSV = {
    Ingredient: 'ingredients.csv',
}

EXPECTED_HEADER = ['name', 'measurement_unit']


class Command(BaseCommand):
    help = 'Импорт данных из CSV файлов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            help='Путь к директории с CSV файлами. По умолчанию используется путь из настроек.',
        )

    def handle(self, *args, **options):
        csv_dir = options['path'] if options['path'] else settings.CSV_DIR

        for model, csv_file in MODELS_CSV.items():
            model.objects.all().delete()
            path_to_file = os.path.join(csv_dir, csv_file)
            
            if not os.path.isfile(path_to_file):
                raise CommandError(f'Файл {path_to_file} не найден.')
                
            self.stdout.write(self.style.NOTICE(f'Начат импорт данных из файла {path_to_file}'))

            with open(path_to_file, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                if reader.fieldnames != EXPECTED_HEADER:
                    raise CommandError('Неверный формат файла: неправильные заголовки полей.')

                instances = [model(**data) for data in reader]
                model.objects.bulk_create(instances)

            self.stdout.write(self.style.SUCCESS(f'Завершен импорт данных в модель {model.__name__}'))

        self.stdout.write(self.style.SUCCESS('Импорт всех данных завершен.'))
