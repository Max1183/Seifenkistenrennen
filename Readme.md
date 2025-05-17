# Seifenkistenrennen

Eine Website, um die Ergebnisse eines Seifenkistenrennens einzutragen und zu verfolgen.

## Inhaltsverzeichnis

-   [Features](#features)
-   [Installation](#installation)
    -   [Backend](#backend)
    -   [Frontend](#frontend)
-   [Verwendung](#verwendung)
-   [Tests](#tests)
    -   [Backend](#backend-tests)
    -   [Frontend](#frontend-tests)
-   [Git-Workflow](#git-workflow)
-   [Lizenz](#lizenz)
-   [Deployment](#deployment)

## Features

-   Coming soon...

## Installation

### Backend

1. Klone das Repository: `git clone https://github.com/Max1183/Seifenkistenrennen.git`
2. Navigiere in den Backend-Ordner: `cd Backend`
3. Erstelle eine virtuelle Umgebung mit Poetry: `poetry shell`
4. Installiere die Abhängigkeiten: `poetry install`
5. Kopiere die `.env.example` Datei: `cp .env.example .env`
6. Fülle die `.env` Datei mit deinen Datenbankzugangsdaten und anderen notwendigen Umgebungsvariablen.
7. Führe die Migrationen aus: `poetry run python manage.py migrate`
8. Erstelle einen Superuser: `poetry run python manage.py createsuperuser`
9. Starte den Entwicklungsserver: `poetry run python manage.py runserver`

### Frontend

1. Navigiere in den Frontend-Ordner: `cd frontend`
2. Installiere die Abhängigkeiten: `npm install`
3. Starte den Entwicklungsserver: `npm run dev`

## Verwendung

1. Öffne den Browser und navigiere zur URL, auf der der Entwicklungsserver läuft: http://localhost:3000.
2. Das Backend ist unter http://localhost:8000 erreichbar.

## Tests

### Backend Tests

1. Navigiere in den Backend-Ordner: `cd backend`
2. Führe die Tests aus: `poetry run python manage.py test`

### Frontend Tests

1. Navigiere in den Frontend-Ordner: `cd frontend`
2. Führe die Tests aus: `npm run test`

## Git Workflow

1. Wechsle zum Develop-Branch: `git checkout develop`
2. Stelle sicher, dass dein Develop-Branch auf dem aktuellen Stand ist: `git pull origin develop`
3. Nimm Änderungen vor und füge sie zu git hinzu: `git add .`
4. Commite deine Änderungen: `git commit -m "Beschreibung der Änderungen"`
5. Pushe deine Änderungen: `git push origin develop`
6. Erstelle einen Pull Request von `develop` nach `main` auf GitHub.
7. Nach erfolgreichem Review und Tests wird der Pull Request auf Github in den main-Branch gemerged.
8. Aktualisiere deinen lokalen master-Branch: `git checkout master` & `git pull origin master`

## Contributing

Wenn du einen Fehler findest oder Verbesserungsvorschläge hast, erstelle bitte ein Issue oder einen Pull Request.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.

## Deployment

1. Dependencies in `requirement.txt` exportieren: `poetry export -f requirements.txt --output requirements.txt --without-hashes`
2. Docker-Image erstellen `docker build -t backend .`
3. Docker Container starten `docker run -p 8000:8000 -e PORT=8000 backend`
4. Frontend build testen: `npm run build`
