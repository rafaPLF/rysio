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

## Erste Commands

- `/rysio help`
- `/rysio setup`
- `/rysio commands`
- `/help`
- `/setup status`
- `/setup language`
- `/tickets status`
- `/tickets panel`

## Architektur

- `bot/core`: Bootstrapping, Logging, Fehler, Extension-Loader
- `bot/config`: Settings und Umgebungsvariablen
- `bot/database`: DB-Basis, Session, Models
- `bot/modules`: Feature-Module
- `bot/services`: Business-Logik
- `bot/locales`: Sprachdateien
