# config.py — Configurazione Scraper Imprese Firenze
import os

# === PARAMETRI GEOGRAFICI ===
PROVINCIA_CODE = "FI"
PROVINCIA_NAME = "Firenze"
REGIONE = "Toscana"

# === FINESTRA TEMPORALE ===
DAYS_LOOKBACK = 7         # quanti giorni indietro cercare
MAX_RESULTS = 500         # massimo risultati per query

# === PERCORSI FILE ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "imprese_firenze.json")
LOG_FILE = os.path.join(BASE_DIR, "scraper.log")

# === FONTI DATI (ordine di priorità) ===

# 1. OpenData Regione Toscana (gratuito, CSV)
OPENDATA_TOSCANA_URL = "https://dati.toscana.it/dataset/imprese-registrate"
OPENDATA_TOSCANA_API = "https://dati.toscana.it/api/3/action/datastore_search"
OPENDATA_RESOURCE_ID = "imprese-fi"  # ID risorsa specifica Firenze

# 2. Registro Imprese (fallback scraping)
REGISTRO_IMPRESE_BASE = "https://www.registroimprese.it"
REGISTRO_IMPRESE_SEARCH = "https://www.registroimprese.it/ricerca-libera"

# 3. OpenData Comune di Firenze
COMUNE_FI_OPENDATA = "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets"

# 4. Regione Toscana SUAP (Sportello Unico Attività Produttive)
SUAP_TOSCANA_API = "https://suap.toscana.it/api/v1/pratiche"

# === HTTP HEADERS (simula browser reale) ===
SCRAPER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# === RETRY & TIMEOUT ===
REQUEST_TIMEOUT = 15      # secondi
MAX_RETRIES = 3
RETRY_DELAY = 2           # secondi tra tentativi

# === SERVER ===
SERVER_HOST = "0.0.0.0"   # accessibile da rete
SERVER_PORT = 8080
DEBUG_MODE = False
