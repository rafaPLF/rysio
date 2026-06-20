# Rysio Ubuntu Upload

Dieser Ordner ist zum Hochladen auf deinen Ubuntu-Server vorbereitet.

## Empfohlener Zielpfad

```bash
/home/Javiera/rysio
```

## Was du hochladen sollst

Lade den kompletten Inhalt dieses Ordners hoch.

## Was bewusst nicht enthalten ist

- `.env`
- `rysio.db`
- lokaler Owner-State
- `__pycache__`

## Nach dem Upload auf Ubuntu

1. In den Ordner wechseln:

```bash
cd /home/Javiera/rysio
```

2. Python installieren:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip -y
```

3. Virtuelle Umgebung anlegen:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

5. `.env` anlegen:

```bash
cp .env.example .env
nano .env
```

6. Teststart:

```bash
source .venv/bin/activate
python3 -m bot.launcher
```

## systemd Service

Datei anlegen:

```bash
sudo nano /etc/systemd/system/rysio.service
```

Inhalt:

```ini
[Unit]
Description=Rysio Discord Bot
After=network.target

[Service]
Type=simple
User=Javiera
WorkingDirectory=/home/Javiera/rysio
EnvironmentFile=/home/Javiera/rysio/.env
ExecStart=/home/Javiera/rysio/.venv/bin/python3 -m bot.launcher
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Dann:

```bash
sudo systemctl daemon-reload
sudo systemctl enable rysio
sudo systemctl start rysio
sudo systemctl status rysio
```

Logs:

```bash
journalctl -u rysio -f
```
