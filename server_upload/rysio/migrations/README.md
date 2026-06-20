# Migrationen

Aktuell erstellt der Bot die Basis-Tabellen beim Start automatisch ueber SQLAlchemy `create_all`.

Fuer einen spaeteren Produktionsbetrieb sollte das auf echte Alembic-Migrationen umgestellt werden, damit Schema-Aenderungen versioniert deployt werden koennen.
