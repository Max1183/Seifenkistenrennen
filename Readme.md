# Seifenkistenrennen Manager 🏁

Willkommen beim Seifenkistenrennen Manager! Diese Webanwendung ermöglicht die Erfassung, Verwaltung und Anzeige von Ergebnissen für Seifenkistenrennen. Sie besteht aus einem React-Frontend für eine ansprechende Benutzererfahrung und einem robusten Django-Backend mit einer PostgreSQL-Datenbank zur Datenhaltung. Außerdem verfügt sie über einen Python-Client für die Kommunikation mit dem Backend.

[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Inhaltsverzeichnis

- [✨ Features](#-features)
- [🚀 Schnellstart & Installation](#-schnellstart--installation)
  - [Voraussetzungen](#voraussetzungen)
  - [1. Repository klonen](#1-repository-klonen)
  - [2. Backend Setup (mit Docker Compose - Empfohlen)](#2-backend-setup-mit-docker-compose---empfohlen)
  - [3. Backend Setup (Lokal ohne Docker)](#3-backend-setup-lokal-ohne-docker)
  - [4. Frontend Setup](#4-frontend-setup)
- [🛠️ Verwendung](#️-verwendung)
- [🧪 Tests](#-tests)
  - [Backend Tests](#backend-tests)
  - [Frontend Tests](#frontend-tests)
- [🚢 Deployment](#-deployment)
  - [Backend (mit Docker)](#backend-mit-docker)
  - [Frontend](#frontend)
- [🔄 Git Workflow (Beispiel)](#-git-workflow-beispiel)
- [🤝 Contributing](#-contributing)
- [📜 Lizenz](#-lizenz)

## ✨ Features

- **Ergebnisverfolgung:** Live-Anzeige von Rennergebnissen und Ranglisten.
- **Admin-Dashboard:**
  - Verwaltung von Rennen, Teams und Teilnehmern (Racers).
  - Einfache Erfassung und Korrektur von Laufzeiten.
  - Benutzerfreundliche Oberfläche zur Konfiguration von Rennparametern.
- **Moderne Technologie-Stack:**
  - **Frontend:** React mit TypeScript für eine typsichere und interaktive Benutzeroberfläche.
  - **Backend:** Django & Django REST Framework für eine leistungsstarke und sichere API.
  - **Datenbank:** PostgreSQL für zuverlässige Datenspeicherung.
- **Docker-Unterstützung:** Vereinfachte Entwicklung und konsistentes Deployment dank Dockerisierung des Backends und der Datenbank.
- **Sichere Authentifizierung:** JWT-basierte Authentifizierung für den Admin-Bereich.
- **Responsive Design:** Gute Darstellung auf verschiedenen Bildschirmgrößen.
- **Python-Client:** Möglichkeit, Ergebnisse über einen separaten Python-Client an die API zu senden.

## 🚀 Schnellstart & Installation

### Voraussetzungen

- [Git](https://git-scm.com/)
- [Node.js](https://nodejs.org/) (aktuellste LTS-Version oder höher empfohlen) und [npm](https://www.npmjs.com/) (oder Yarn/pnpm)
- [Python](https://www.python.org/) (Version 3.9 oder höher empfohlen)
- [Poetry](https://python-poetry.org/) für die Python-Abhängigkeitsverwaltung im Backend.
- [Docker](https://www.docker.com/get-started) und [Docker Compose](https://docs.docker.com/compose/install/) (für die Docker-basierte Einrichtung)

### 1. Repository klonen

```bash
git clone https://github.com/Max1183/Seifenkistenrennen.git
cd Seifenkistenrennen
```

### 2. Backend Setup (mit Docker Compose - Empfohlen)

Diese Methode startet das Django-Backend und eine PostgreSQL-Datenbank in Docker-Containern.

1. **Navigiere in den Backend-Ordner:**

    ```bash
    cd backend
    ```

2. **Umgebungsvariablen konfigurieren:**
    Kopiere die Beispiel-Umgebungsdatei und passe sie bei Bedarf an. Die Standardwerte sind für die Docker-Compose-Einrichtung optimiert.

    ```bash
    cp .env.example .env.dev
    ```

    _Wichtig:_ `DB_HOST` in `.env.dev` sollte auf `db` gesetzt sein, um auf den PostgreSQL-Container innerhalb des Docker-Netzwerks zu verweisen.
3. **Anwendung bauen und starten:**

    ```bash
    docker-compose --env-file .env.dev up --build -d
    ```

    - `-d` startet die Container im Hintergrund.
    - `--build` erzwingt den Neuaufbau der Images, falls Änderungen am `Dockerfile` oder den Quellcode-Abhängigkeiten vorgenommen wurden.

Das Backend ist nun unter `http://localhost:8000` erreichbar.

### 3. Backend Setup (Lokal ohne Docker)

Falls du das Backend lieber direkt auf deinem System ohne Docker betreiben möchtest:

1. **Navigiere in den Backend-Ordner:**

    ```bash
    cd backend
    ```

2. **Virtuelle Umgebung erstellen und aktivieren (mit Poetry):**

    ```bash
    poetry shell
    ```

3. **Abhängigkeiten installieren:**

    ```bash
    poetry install
    ```

4. **Umgebungsvariablen konfigurieren:**
    Kopiere die Beispiel-Umgebungsdatei und passe sie für die lokale Entwicklung an:

    ```bash
    cp .env.example .env.local
    ```

    Bearbeite die `.env.local`-Datei. Stelle sicher, dass `DB_HOST` auf `localhost` oder deine lokale PostgreSQL-IP zeigt und die Datenbank-Credentials korrekt sind.
    _Hinweis: Deine `settings.py` muss so konfiguriert sein, dass sie Variablen aus dieser `.env.local`-Datei lädt (z.B. mittels `python-decouple` oder `django-environ`)._
5. **PostgreSQL Datenbank einrichten:**
    Stelle sicher, dass du eine lokale PostgreSQL-Instanz laufen hast und eine Datenbank sowie einen Benutzer gemäß den Angaben in deiner `.env.local`-Datei erstellt hast.
6. **Datenbankmigrationen ausführen:**

    ```bash
    poetry run python manage.py migrate
    ```

7. **Superuser erstellen:**
    Dieser benutzerdefinierte Befehl erstellt einen Superuser mit Standard-Credentials (siehe Code) oder fragt diese ab.

    ```bash
    poetry run python manage.py create_initial_superuser
    ```

    Alternativ kannst du den Standard-Django-Befehl verwenden:

    ```bash
    poetry run python manage.py createsuperuser
    ```

8. **Entwicklungsserver starten:**

    ```bash
    poetry run python manage.py runserver
    ```

    Das Backend ist nun unter `http://localhost:8000` erreichbar.

### 4. Frontend Setup

1. **Navigiere in den Frontend-Ordner (vom Projekt-Root aus):**

    ```bash
    cd Frontend
    ```

2. **Abhängigkeiten installieren:**

    ```bash
    npm install
    ```

3. **Umgebungsvariablen konfigurieren:**
    Das Frontend erwartet die Backend-API unter einer bestimmten URL. Standardmäßig ist dies `http://127.0.0.1:8000/api`. Falls abweichend, erstelle eine `.env`-Datei im Wurzelverzeichnis deines Frontend-Projekts (z.B. `Frontend/.env`):

    ```dotenv
    # Frontend/.env
    VITE_API_BASE_URL=http://localhost:8000/api
    ```

4. **Entwicklungsserver starten:**

    ```bash
    npm run dev
    ```

    Das Frontend ist nun unter `http://localhost:3000` (oder der von Vite/React angezeigten Adresse) erreichbar.

## 🛠️ Verwendung

- **Öffentliche Seite:** Navigiere zur URL des Frontend-Entwicklungsservers (z.B. `http://localhost:3000`), um die Rennergebnisse und Informationen einzusehen.
- **Admin-Bereich:**
  - Greife auf `/admin` zu (z.B. `http://localhost:3000/admin`).
  - Melde dich mit den zuvor erstellten Superuser-Anmeldedaten an.
  - Verwalte Teams, Teilnehmer und Ergebnisse über das Admin-Dashboard.
- **Django Admin Interface:** Das traditionelle Django Admin Interface ist unter `http://localhost:8000/admin/` (wenn das Backend läuft) verfügbar und kann für direkte Datenmanipulationen genutzt werden.

## 🧪 Tests

### Backend Tests

1. **Navigiere in den Backend-Ordner:** `cd backend`
2. **Ausführen mit Docker Compose:**

    ```bash
    docker-compose exec web python manage.py test race_core
    ```

    (Ersetze `race_core` ggf. mit dem Namen deiner App oder lasse es weg, um alle Tests auszuführen.)
3. **Ausführen lokal (ohne Docker, Poetry-Umgebung muss aktiv sein):**

    ```bash
    poetry run python manage.py test race_core
    ```

### Frontend Tests

1. **Navigiere in den Frontend-Ordner:** `cd Frontend` (oder den Stammordner deines React-Projekts)
2. **Führe die Tests aus:**

    ```bash
    npm run test
    ```

## 🚢 Deployment

### Backend (mit Docker)

1. **Umgebungsvariablen für Produktion:**
    Stelle sicher, dass eine `.env.prod`-Datei mit produktionssicheren Werten (insbesondere `SECRET_KEY`, `DEBUG=False`, korrekte `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` und Datenbank-Credentials für die Produktionsdatenbank) vorhanden ist. Diese wird von `docker-compose.yml` (oder direkt von Docker beim Start) verwendet.
2. **Docker Image bauen:**

    ```bash
    cd backend
    docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
    ```

    Stelle sicher, dass `DB_HOST` in der Produktionsumgebung korrekt auf den Datenbankservice zeigt und Persistenz für die Datenbank (Volumes) konfiguriert ist.

### Frontend

1. **Frontend bauen:**
    Navigiere in den `Frontend`-Ordner (oder den Stammordner deines React-Projekts):

    ```bash
    cd Frontend
    npm run build
    ```

    Dies erstellt optimierte statische Dateien im `dist`-Ordner (bei Vite) oder `build`-Ordner (bei Create React App).
2. **Statische Dateien bereitstellen:**
    Der Inhalt des `dist`/`build`-Ordners kann nun auf einem beliebigen statischen Webhost (z.B. Netlify, Vercel, AWS S3/CloudFront, GitHub Pages) oder einem Webserver wie Nginx oder Apache bereitgestellt werden.
    - **Wichtig für Client-seitiges Routing:** Konfiguriere deinen Server so, dass alle Anfragen, die nicht auf eine existierende Datei zeigen, an die `index.html` weitergeleitet werden, damit React Router die Navigation übernehmen kann.

## 🔄 Git Workflow (Beispiel)

Wir verwenden einen einfachen Git-Flow mit `develop`- und `master`-Branches.

1. **Arbeite immer im `develop`-Branch (oder Feature-Branches davon):**

    ```bash
    git checkout develop          # Wechsle zum Entwicklungsbranch
    git pull origin develop       # Hole die neuesten Änderungen
    # Erstelle optional einen Feature-Branch
    git checkout -b feature/neues-feature
    ```

2. **Änderungen vornehmen und committen:**

    ```bash
    git add .
    git commit -m "feat: Implementiere das XYZ-Feature" # Nutze aussagekräftige Commit-Nachrichten (siehe Conventional Commits)
    ```

3. **Pushe deinen Branch (Feature-Branch oder `develop`):**

    ```bash
    git push origin feature/neues-feature # oder git push origin develop
    ```

4. **Erstelle einen Pull Request (PR):**
    Gehe zu GitHub (oder deiner Git-Hosting-Plattform) und erstelle einen Pull Request vom `feature/neues-feature`-Branch (oder `develop`) in den `develop`-Branch (für Zwischenreviews) oder vom `develop`-Branch in den `master`-Branch (für Releases).
5. **Review und Merge:**
    Nach einem erfolgreichen Code-Review und bestandenen Tests wird der PR in den Zielbranch (`develop` oder `master`) gemerged. Der `master`-Branch sollte immer den stabilen, deploybaren Code enthalten.
6. **Lokale Branches aktuell halten:**

    ```bash
    git checkout master
    git pull origin master
    git checkout develop
    git pull origin develop
    ```

## 🤝 Contributing

Beiträge sind herzlich willkommen! Wenn du einen Fehler findest, eine Funktion vorschlagen möchtest oder Code beitragen willst:

1. Forke das Repository.
2. Erstelle einen neuen Feature-Branch (`git checkout -b feature/tolles-neues-feature` von `develop` ausgehend).
3. Commite deine Änderungen (`git commit -am 'feat: Füge tolles neues Feature hinzu'`). Halte dich dabei an die [Conventional Commits](https://www.conventionalcommits.org/) Spezifikationen.
4. Pushe zum Branch (`git push origin feature/tolles-neues-feature`).
5. Öffne einen Pull Request gegen den `develop`-Branch des Original-Repositorys.

Bitte stelle sicher, dass alle Tests bestehen, bevor du einen Pull Request stellst.

## 📜 Lizenz

Dieses Projekt ist unter der [MIT-Lizenz](LICENSE) lizenziert. Eine Kopie der Lizenz findest du in der `LICENSE`-Datei.
