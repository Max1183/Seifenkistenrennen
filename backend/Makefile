.PHONY: up-dev up-prod down logs test shell bash

default: up-dev

up-dev:
	@echo 🚀  Starte Entwicklungsumgebung...
	docker-compose --env-file .env.dev up --build -d

# Startet die Produktionsumgebung
up-prod:
	@echo 🏭  Starte Produktionsumgebung...
	docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Stoppt alle Dienste
down:
	@echo 🛑  Stoppe alle Dienste...
	docker-compose down

# Zeigt die Logs aller Dienste an
logs:
	docker-compose logs -f

# Führt die Django-Tests aus
test:
	@echo 🧪  Führe Tests aus...
	docker-compose --env-file .env.dev run --rm web python manage.py test

# Öffnet eine Django-Shell
shell:
	docker-compose --env-file .env.dev run --rm web python manage.py shell

# Öffnet eine Bash/Sh-Shell im laufenden Web-Container
bash:
	docker-compose exec web /bin/sh