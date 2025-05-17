# Seifenkistenrennen Manager 🏁

Willkommen beim Seifenkistenrennen Manager! Diese Webanwendung ermöglicht die Erfassung, Verwaltung und Anzeige von Ergebnissen für Seifenkistenrennen. Sie besteht aus einem React-Frontend für eine ansprechende Benutzererfahrung und einem robusten Django-Backend mit einer PostgreSQL-Datenbank zur Datenhaltung.

[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

-   **Ergebnisverfolgung:** Live-Anzeige von Rennergebnissen und Ranglisten.
-   **Admin-Dashboard:**
    -   Verwaltung von Rennen, Teams und Teilnehmern (Racers).
    -   Einfache Erfassung und Korrektur von Laufzeiten.
    -   Benutzerfreundliche Oberfläche zur Konfiguration von Rennparametern.
-   **Moderne Technologie-Stack:**
    -   **Frontend:** React mit TypeScript für eine typsichere und interaktive Benutzeroberfläche.
    -   **Backend:** Django & Django REST Framework für eine leistungsstarke und sichere API.
    -   **Datenbank:** PostgreSQL für zuverlässige Datenspeicherung.
-   **Docker-Unterstützung:** Vereinfachte Entwicklung und konsistentes Deployment dank Dockerisierung des Backends und der Datenbank.
-   **Sichere Authentifizierung:** JWT-basierte Authentifizierung für den Admin-Bereich.
-   **Responsive Design:** (Ziel) Gute Darstellung auf verschiedenen Bildschirmgrößen.
-   **(Optional) Python-Client:** Möglichkeit, Ergebnisse über einen separaten Python-Client an die API zu senden.

## 🚀 Schnellstart & Installation

### Voraussetzungen

-   [Git](https://git-scm.com/)
-   [Node.js](https://nodejs.org/) (Version 18.x oder höher empfohlen) und [npm](https://www.npmjs.com/) (oder Yarn/pnpm)
-   [Python](https://www.python.org/) (Version 3.9 oder höher empfohlen)
-   [Poetry](https://python-poetry.org/) für die Python-Abhängigkeitsverwaltung im Backend.
-   [Docker](https://www.docker.com/get-started) und [Docker Compose](https://docs.docker.com/compose/install/) (für die Docker-basierte Einrichtung)

### 1. Repository klonen

```bash
git clone https://github.com/Max1183/Seifenkistenrennen.git
cd Seifenkistenrennen
```

### 2. Backend Setup (mit Docker Compose - Empfohlen)

Diese Methode startet das Django-Backend und eine PostgreSQL-Datenbank in Docker-Containern.

1.  **Navigiere in den Backend-Ordner:**
    ```bash
    cd backend_django
    ```
2.  **Umgebungsvariablen konfigurieren:**
    Kopiere die Beispiel-Umgebungsdatei und passe sie bei Bedarf an. Die Standardwerte sind für die Docker-Compose-Einrichtung optimiert.
    ```bash
    cp .env.example .env
    ```
    _Wichtig:_ `DB_HOST` in `.env` sollte auf `db` gesetzt sein, um auf den PostgreSQL-Container innerhalb des Docker-Netzwerks zu verweisen.
3.  **Anwendung bauen und starten:**
    ```bash
    docker-compose up --build -d
    ```
    -   `-d` startet die Container im Hintergrund.
    -   `--build` erzwingt den Neuaufbau der Images, falls Änderungen am `Dockerfile` oder den Quellcode-Abhängigkeiten vorgenommen wurden.
4.  **Datenbankmigrationen ausführen:**
    ```bash
    docker-compose exec web python manage.py makemigrations race_core
    docker-compose exec web python manage.py migrate
    ```
5.  **Superuser erstellen (für den Admin-Zugang):**
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```
    Folge den Anweisungen, um einen Administrator-Account anzulegen.

Das Backend ist nun unter `http://localhost:8000` erreichbar.

### 3. Backend Setup (Lokal ohne Docker)

Falls du das Backend lieber direkt auf deinem System ohne Docker betreiben möchtest:

1.  **Navigiere in den Backend-Ordner:**
    ```bash
    cd backend_django
    ```
2.  **Virtuelle Umgebung erstellen und aktivieren (mit Poetry):**
    ```bash
    poetry shell
    ```
3.  **Abhängigkeiten installieren:**
    ```bash
    poetry install
    ```
4.  **Umgebungsvariablen konfigurieren:**
    Kopiere die Beispiel-Umgebungsdatei für die lokale Entwicklung (falls vorhanden, sonst `.env.example` anpassen):
    ```bash
    cp .env.local.example .env.local  # Und cp .env.example .env
    ```
    Bearbeite .env.local und .env und stelle sicher, dass DB_HOST auf 'localhost' oder deine lokale PostgreSQL-IP zeigt.
    Stelle sicher, dass deine settings.py .env.local oder die entsprechenden lokalen Einstellungen lädt.
5.  **PostgreSQL Datenbank einrichten:**
    Stelle sicher, dass du eine lokale PostgreSQL-Instanz laufen hast und eine Datenbank sowie einen Benutzer gemäß den Angaben in deiner `.env.local` (oder `.env`) Datei erstellt hast.
6.  **Datenbankmigrationen ausführen:**
    ```bash
    poetry run python manage.py migrate
    ```
7.  **Superuser erstellen:**
    ```bash
    poetry run python manage.py createsuperuser
    ```
8.  **Entwicklungsserver starten:**
    `bash
    poetry run python manage.py runserver
    `
    Das Backend ist nun unter `http://localhost:8000` erreichbar.

### 4. Frontend Setup

1.  **Navigiere in den Frontend-Ordner (vom Projekt-Root aus):**
    ```bash
    cd frontend_react
    ```
2.  **Abhängigkeiten installieren:**
    ```bash
    npm install
    ```
3.  **Umgebungsvariablen konfigurieren (optional):**
    Das Frontend erwartet die Backend-API unter einer bestimmten URL. Standardmäßig ist dies `http://127.0.0.1:8000/api`. Falls abweichend, erstelle eine `.env`-Datei im `frontend_react`-Ordner:
    ```dotenv
    # frontend_react/.env
    VITE_API_BASE_URL=http://localhost:8000/api
    ```
4.  **Entwicklungsserver starten:**
    `bash
    npm run dev
    `
    Das Frontend ist nun üblicherweise unter `http://localhost:5173` (Vite) oder `http://localhost:3000` (Create React App) erreichbar.

## 🛠️ Verwendung

-   **Öffentliche Seite:** Navigiere zur URL des Frontend-Entwicklungsservers (z.B. `http://localhost:5173`), um die Rennergebnisse und Informationen einzusehen.
-   **Admin-Bereich:**
    -   Greife auf `/admin/login` zu (z.B. `http://localhost:5173/admin/login`).
    -   Melde dich mit den zuvor erstellten Superuser-Anmeldedaten an.
    -   Verwalte Teams, Teilnehmer und Ergebnisse über das Admin-Dashboard.
-   **Django Admin Interface:** Das traditionelle Django Admin Interface ist unter `http://localhost:8000/admin/` (wenn das Backend läuft) verfügbar und kann für direkte Datenmanipulationen genutzt werden.

## 🧪 Tests

### Backend Tests

1.  **Navigiere in den Backend-Ordner:** `cd backend_django`
2.  **Ausführen mit Docker Compose (empfohlen):**
    ```bash
    docker-compose exec web python manage.py test race_core
    ```
3.  **Ausführen lokal (ohne Docker):**
    ```bash
    poetry run python manage.py test race_core
    ```

### Frontend Tests

1.  **Navigiere in den Frontend-Ordner:** `cd frontend_react`
2.  **Führe die Tests aus:**
    ```bash
    npm run test
    ```

## 🚢 Deployment

### Backend (mit Docker)

1.  **Umgebungsvariablen für Produktion:**
    Stelle sicher, dass eine `.env`-Datei mit produktionssicheren Werten (insbesondere `SECRET_KEY`, `DEBUG=False`, korrekte `CORS_ALLOWED_ORIGINS` und Datenbank-Credentials für die Produktionsdatenbank) vorhanden ist. Diese wird von `docker-compose.yml` (oder direkt von Docker beim Start) verwendet.
2.  **(Optional) `requirements.txt` für reinen Docker Build exportieren:**
    Obwohl das `Dockerfile` `poetry install` verwenden kann, ist es manchmal üblich, eine `requirements.txt` zu haben.
    ```bash
    cd backend_django
    poetry export -f requirements.txt --output requirements.txt --without-hashes
    ```
3.  **Docker Image bauen (falls nicht über Docker Compose):**
    Wenn du das Image manuell bauen und z.B. in eine Container Registry pushen möchtest:
    ```bash
    cd backend_django
    docker build -t dein-registry/seifenkisten-backend:latest .
    ```
4.  **Anwendung mit Docker Compose starten (Produktionsbeispiel):**
    Für die Produktion würdest du typischerweise eine separate `docker-compose.prod.yml` verwenden oder deine bestehende `docker-compose.yml` anpassen (z.B. Volumes für Code-Mounting entfernen, Gunicorn mit mehr Workern starten, Logging konfigurieren).
    ```bash
    docker-compose up --build -d
    ```
    Stelle sicher, dass `DB_HOST` in der Produktionsumgebung korrekt auf den Datenbankservice zeigt und Persistenz für die Datenbank (Volumes) konfiguriert ist.

### Frontend

1.  **Frontend bauen:**
    Navigiere in den `frontend_react`-Ordner:
    ```bash
    cd frontend_react
    npm run build
    ```
    Dies erstellt optimierte statische Dateien im `dist` (Vite) oder `build` (CRA) Ordner.
2.  **Statische Dateien bereitstellen:**
    Der Inhalt des `dist`/`build`-Ordners kann nun auf einem beliebigen statischen Webhost (z.B. Netlify, Vercel, AWS S3/CloudFront, GitHub Pages) oder einem Webserver wie Nginx oder Apache bereitgestellt werden.
    -   **Wichtig für Client-seitiges Routing:** Konfiguriere deinen Server so, dass alle Anfragen, die nicht auf eine existierende Datei zeigen, an die `index.html` weitergeleitet werden, damit React Router die Navigation übernehmen kann.

## 🔄 Git Workflow (Beispiel)

Wir verwenden einen einfachen Git-Flow mit `develop`- und `main`-Branches.

1.  **Arbeite immer auf einem Feature-Branch:**
    ```bash
    git checkout develop          # Wechsle zum Entwicklungsbranch
    git pull origin develop       # Hole die neuesten Änderungen
    git checkout -b feature/dein-feature-name  # Erstelle einen neuen Branch für dein Feature
    ```
2.  **Änderungen vornehmen und committen:**
    ```bash
    git add .
    git commit -m "Implementiere das XYZ-Feature" # Nutze aussagekräftige Commit-Nachrichten (siehe Conventional Commits)
    ```
3.  **Pushe deinen Feature-Branch:**
    ```bash
    git push origin feature/dein-feature-name
    ```
4.  **Erstelle einen Pull Request (PR):**
    Gehe zu GitHub (oder deiner Git-Hosting-Plattform) und erstelle einen Pull Request von deinem `feature/dein-feature-name`-Branch in den `develop`-Branch.
5.  **Review und Merge:**
    Nach einem erfolgreichen Code-Review und bestandenen Tests wird der PR in den `develop`-Branch gemerged.
6.  **Release (Merge von `develop` nach `main`):**
    Wenn ein Release ansteht, wird ein PR von `develop` nach `main` erstellt. Der `main`-Branch sollte immer den stabilen, deploybaren Code enthalten.
7.  **Lokale Branches aktuell halten:**
    ```bash
    git checkout main
    git pull origin main
    git checkout develop
    git pull origin develop
    ```

## 🤝 Contributing

Beiträge sind herzlich willkommen! Wenn du einen Fehler findest, eine Funktion vorschlagen möchtest oder Code beitragen willst:

1.  Forke das Repository.
2.  Erstelle einen neuen Feature-Branch (`git checkout -b feature/tolles-neues-feature`).
3.  Commite deine Änderungen (`git commit -am 'feat: Füge tolles neues Feature hinzu'`).
4.  Pushe zum Branch (`git push origin feature/tolles-neues-feature`).
5.  Öffne einen Pull Request.

Bitte stelle sicher, dass deine Commits den [Conventional Commits](https://www.conventionalcommits.org/) Spezifikationen folgen und dass alle Tests bestehen.

## 📜 Lizenz

Dieses Projekt ist unter der [MIT-Lizenz](LICENSE) lizenziert. Eine Kopie der Lizenz findest du in der `LICENSE`-Datei.
