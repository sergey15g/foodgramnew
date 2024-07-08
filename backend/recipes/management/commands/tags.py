from django.core.management import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):
    help = 'Создаем тэги'

    def handle(self, *args, **kwargs):
        data = [
            {'name': 'Обед', 'color': '#49B64E', 'slug': 'dinner'},
            {'name': 'Ужин', 'color': '#8775D2', 'slug': 'supper'},
            {'name': 'Завтрак', 'color': '#674EA7', 'slug': 'breakfast'}]
        Tag.objects.bulk_create(Tag(**tag) for tag in data)
        self.stdout.write(self.style.SUCCESS('Все тэги загружены!'))
