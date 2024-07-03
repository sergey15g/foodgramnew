ifeq ($(OS),Windows_NT)
	SLEEP := timeout
else
	SLEEP := sleep
endif

start:
	docker compose -f infra/docker-compose.yml up --build -d
	$(SLEEP) 2

	docker compose -f infra/docker-compose.yml exec api python manage.py migrate
	docker compose -f infra/docker-compose.yml exec api python manage.py import_csv
	docker compose -f infra/docker-compose.yml exec api python manage.py tags

	docker compose -f infra/docker-compose.yml rm frontend -f

see-db:
	docker compose -f infra/docker-compose.yml exec database psql -U postgres

see-api:
	docker compose -f infra/docker-compose.yml logs -f api

rebuild-nginx:
	docker compose -f infra/docker-compose.yml rm nginx -f
	docker compose -f infra/docker-compose.yml up -d --build nginx

update-api:
	docker compose -f infra/docker-compose.yml cp ./backend/. api:app

	docker compose -f infra/docker-compose.yml restart api
	docker compose -f infra/docker-compose.yml restart nginx

gen-dump:
	docker compose -f infra/docker-compose.yml exec database sh -c 'pg_dump -h 127.0.0.1 --username=postgres -d postgres > dumps/$$(date +'%Y-%m-%d_%H-%M-%S').dump'