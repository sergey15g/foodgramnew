# Foodgram

## Описание
Этот проект создан для объединения тех, кто любит и живет готовкой! Только тут вы сможете обмениваться рецептами, добавлять понравившиеся в избранное, распределять по тегам и многое другое! А в любом рецепте вы легко сможете сохранить список ингридиентов прямо в корзину покупок! Готовить - это не просто легко, но и интересно!

## Развернем проект с Docker hub
В домашней директории создадим папку проекта - `foodgram`:

```bash
mkdir foodgram
```
Переходим в папку, копируем файл `docker-compose.production.yml` и разворачиваем проект:
```bash
cd foodgram
sudo docker compose -f docker-compose.production.yml up
```

## Развернули, а что дальше?

После запуска нужно выполнить сбор статистики и миграцию для бэкенда. Для этого мы вводим следующие команды:

```bash
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate

sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic

sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /static/static/
```

Готово! Наслаждаемся по адресу: 

```
http://127.0.0.1:9000/
или
http://localhost:9000/
```
## Автор проекта
>[sergey15g](https://github.com/sergey15g).