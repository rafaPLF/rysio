# DC Bot

Sauberes Grundgeruest fuer einen mehrsprachigen Multi-Server-Discord-Bot mit Vorbereitung fuer Free- und Premium-Features.

## Tech Stack

- Python
- discord.py
- PostgreSQL
- SQLAlchemy
- Alembic

## Start

1. Virtuelle Umgebung erstellen
2. `pip install -r requirements.txt`
3. `.env.example` nach `.env` kopieren und Werte eintragen
4. `python -m bot.launcher`

## Lokaler Test ohne PostgreSQL

Fuer den ersten lokalen Test kann `SQLite` genutzt werden:

```env
DATABASE_URL=sqlite+aiosqlite:///./rysio.db
```

Spaeter kann das wieder auf PostgreSQL umgestellt werden.

## Intents fuer den ersten Test

Die aktuelle Test-Konfiguration startet standardmaessig ohne privilegierte Intents. Fuer spaetere Features wie Join-Autoroles oder tiefere Message-Moderation koennen diese in der `.env` aktiviert und im Discord Developer Portal freigeschaltet werden:

```env
ENABLE_MEMBERS_INTENT=true
ENABLE_MESSAGE_CONTENT_INTENT=true
```

## Webpanel-Vorbereitung

Rysio hat jetzt eine erste interne Log-API fuer das spaetere Control Panel. Sie ist standardmaessig aus und kann lokal ueber die `.env` aktiviert werden:

```env
WEB_API_ENABLED=true
WEB_API_HOST=127.0.0.1
WEB_API_PORT=8080
WEB_API_TOKEN=dein-langer-geheimer-token
WEB_API_ALLOWED_ORIGIN=https://console.rysio.app
```

Verfuegbare Startpunkte:

- `GET /api/health`
- `GET /api/guilds/{guild_id}/logs`

Die Log-Route erwartet den Header:

```text
Authorization: Bearer dein-langer-geheimer-token
```

Beispiel:

```text
http://127.0.0.1:8080/api/guilds/123456789/logs?limit=50&offset=0
```

Fuer einen separaten Webspace liegt eine fertige statische Upload-Datei unter [portal_upload/index.html](/C:/Users/Rafal/Desktop/DC%20bot/portal_upload/index.html). Diese Seite kann per FTP hochgeladen werden und spricht dann die API auf dem Bot-Server an.

## Erste Commands

- `/rysio help`
- `/rysio setup`
- `/rysio commands`
- `/help`
- `/reactionroles create`
- `/reactionroles add`
- `/jtc setup`
- `/logs setup`
- `/setup status`
- `/setup language`
- `/tickets status`
- `/tickets panel`

## Patch Notes

Automatische Patch Notes werden ueber [bot/release_notes.json](/C:/Users/Rafal/Desktop/DC bot/bot/release_notes.json) gesteuert. Wenn sich die Version dort erhoeht, postet Rysio die neue Update-Nachricht beim naechsten Start einmalig pro Server in den gesetzten Info-Channel.

## Architektur

- `bot/core`: Bootstrapping, Logging, Fehler, Extension-Loader
- `bot/config`: Settings und Umgebungsvariablen
- `bot/database`: DB-Basis, Session, Models
- `bot/modules`: Feature-Module
- `bot/services`: Business-Logik
- `bot/locales`: Sprachdateien
