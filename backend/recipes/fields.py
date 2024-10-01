import base64

from django.core.files.base import ContentFile
from rest_framework import serializers


import base64
import uuid
from django.core.files.base import ContentFile

from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Если полученный объект строка, и эта строка
        # начинается с 'data:image'...
        if isinstance(data, str) and data.startswith("data:image"):
            # ...начинаем декодировать изображение из base64.
            # Сначала нужно разделить строку на части.
            format_image, imgstr = data.split(";base64,")
            # И извлечь расширение файла.
            ext = format_image.split("/")[-1]
            # Генерируем уникальное имя файла
            file_name = f"{uuid.uuid4()}.{ext}"
            # Затем декодировать сами данные и поместить результат в файл,
            # которому дать уникальное название.
            data = ContentFile(base64.b64decode(imgstr), name=file_name)

        return super().to_internal_value(data)

