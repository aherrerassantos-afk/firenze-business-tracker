# 🏛️ Firenze Business Tracker

**Tracker automatico delle ultime imprese registrate nella provincia di Firenze**

Aggiornamento giornaliero automatico · Dashboard multi-utente · Export CSV

---

## 🗂️ Struttura Progetto

```
📁 progetto/
├── app.py                  ← Server Flask (API + Web)
├── start.sh                ← Script avvio (da usare)
├── cron_setup.sh           ← Setup aggiornamento automatico
│
├── scraper/
│   ├── scraper.py          ← Estrattore dati
│   ├── config.py           ← Configurazione
│   └── requirements.txt    ← Dipendenze Python
│
├── templates/
│   └── index.html          ← Dashboard HTML
│
├── static/
│   ├── style.css           ← Design premium
│   └── app.js              ← Logica frontend
│
└── data/
    └── imprese_firenze.json ← Dati estratti (auto-generato)
```

---

## 🚀 Installazione e Avvio (su Server Linux/Mac)

### Prerequisiti
```bash
# Python 3.8+ richiesto
python3 --version

# Installa pip se non presente
sudo apt install python3-pip python3-venv  # Ubuntu/Debian
# oppure
brew install python3  # macOS
```

### Primo avvio
```bash
# 1. Rendi eseguibili gli script
chmod +x start.sh cron_setup.sh

# 2. Avvia il server (installa dipendenze automaticamente)
./start.sh
```

Il server partirà su `http://0.0.0.0:5000` — accessibile da qualsiasi browser sulla stessa rete.

---

## ⏰ Aggiornamento Automatico Giornaliero

```bash
# Configura il cron job (eseguire UNA SOLA VOLTA)
./cron_setup.sh
```

Questo configura un task automatico che aggiorna i dati ogni mattina alle **06:00**.

Monitorare i log:
```bash
tail -f cron.log
```

---

## 🌐 Deploy su Server Remoto (Produzione)

### Con Nginx come reverse proxy

```nginx
# /etc/nginx/sites-available/firenze-tracker
server {
    listen 80;
    server_name tuodominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/firenze-tracker /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Come servizio systemd (avvio automatico)

```ini
# /etc/systemd/system/firenze-tracker.service
[Unit]
Description=Firenze Business Tracker
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/progetto
ExecStart=/path/to/progetto/start.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable firenze-tracker
sudo systemctl start firenze-tracker
sudo systemctl status firenze-tracker
```

---

## 📡 API REST

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/` | GET | Dashboard web |
| `/api/imprese` | GET | Lista imprese (filtrabili) |
| `/api/stats` | GET | Statistiche aggregate |
| `/api/aggiorna` | POST | Forza aggiornamento |
| `/api/stato` | GET | Stato del server |
| `/api/comuni` | GET | Lista comuni disponibili |
| `/api/export/csv` | GET | Download CSV |

### Parametri `/api/imprese`
- `?giorni=7` — periodo di analisi (default: 7)
- `?limit=100` — massimo risultati (max: 500)
- `?search=bar` — ricerca per nome/indirizzo/settore
- `?comune=firenze` — filtra per comune
- `?ateco=56` — filtra per codice ATECO

---

## 🔧 Configurazione

Modifica `scraper/config.py` per personalizzare:

```python
DAYS_LOOKBACK = 7        # giorni da analizzare
MAX_RESULTS = 500        # max risultati
SERVER_PORT = 5000       # porta del server
```

---

## 📊 Fonti Dati

Il sistema tenta le fonti in ordine di priorità:

1. **OpenData Regione Toscana** — Gratuito, CSV/JSON
2. **OpenData Comune di Firenze** — Gratuito, API REST
3. **Registro Imprese** — Scraping HTML (fallback)
4. **Dati Demo** — Generati localmente (sempre disponibili)

---

## ℹ️ Note Legali

I dati estratti provengono da fonti pubbliche ufficiali (Registro delle Imprese, Camera di Commercio di Firenze). L'uso è consentito per analisi di mercato e ricerca, nel rispetto dei termini di servizio di InfoCamere e del GDPR.
