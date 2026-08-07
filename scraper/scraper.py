"""
scraper.py — Estrattore Ultime Imprese Registrate a Firenze
Fonti: OpenData Toscana, Registro Imprese, Comune di Firenze
Aggiornamento: giornaliero automatico via cron
"""

import os
import sys
import json
import time
import logging
import hashlib
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Import compatibile sia con esecuzione diretta che come modulo
try:
    from scraper.config import *          # importato da app.py (root)
except ImportError:
    # Eseguito direttamente: python3 scraper/scraper.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import *

# ─────────────────────────────────────────
# Setup logging
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def genera_id(nome, data, indirizzo=""):
    """Genera un ID univoco per evitare duplicati."""
    raw = f"{nome}|{data}|{indirizzo}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def safe_get(url, params=None, timeout=REQUEST_TIMEOUT, retries=MAX_RETRIES):
    """HTTP GET con retry automatico."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                params=params,
                headers=SCRAPER_HEADERS,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            log.warning(f"Tentativo {attempt + 1}/{retries} fallito: {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    log.error(f"Tutte le richieste fallite per: {url}")
    return None


def normalizza_data(data_str):
    """Normalizza vari formati di data a YYYY-MM-DD."""
    if not data_str:
        return None
    formati = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S",
        "%Y%m%d", "%d.%m.%Y",
    ]
    for fmt in formati:
        try:
            return datetime.strptime(str(data_str).strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return str(data_str)


# ─────────────────────────────────────────
# FONTE 1: OpenData CCIAA Toscana / InfoCamere Open
# ─────────────────────────────────────────

def scrape_opendata_toscana(data_da, data_a):
    """
    Tenta di estrarre dal portale OpenData Regione Toscana.
    Endpoint: dati.toscana.it (CKAN API)
    """
    log.info("📡 Fonte 1: OpenData Toscana...")
    risultati = []

    # Endpoint CKAN con filtri
    endpoint = "https://dati.toscana.it/api/3/action/datastore_search_sql"
    query = f"""
        SELECT * FROM "imprese_registrate_fi"
        WHERE data_iscrizione >= '{data_da}'
        AND data_iscrizione <= '{data_a}'
        AND provincia = 'FI'
        ORDER BY data_iscrizione DESC
        LIMIT {MAX_RESULTS}
    """

    resp = safe_get(endpoint, params={"sql": query})
    if resp and resp.status_code == 200:
        try:
            data = resp.json()
            records = data.get("result", {}).get("records", [])
            log.info(f"  → OpenData Toscana: {len(records)} record trovati")
            for r in records:
                risultati.append(normalizza_record_opendata(r))
        except Exception as e:
            log.warning(f"  → Errore parsing OpenData Toscana: {e}")
    else:
        log.warning("  → OpenData Toscana non disponibile, passo alla fonte 2")

    return risultati


def normalizza_record_opendata(r):
    """Normalizza un record dal formato OpenData Toscana."""
    return {
        "id": genera_id(
            r.get("denominazione", ""),
            r.get("data_iscrizione", ""),
            r.get("indirizzo", ""),
        ),
        "denominazione": r.get("denominazione", r.get("ragione_sociale", "N/D")).strip().title(),
        "data_iscrizione": normalizza_data(r.get("data_iscrizione", r.get("data_apertura", ""))),
        "indirizzo": r.get("indirizzo", r.get("sede_legale", "N/D")).strip().title(),
        "comune": r.get("comune", "Firenze").strip().title(),
        "provincia": "FI",
        "codice_ateco": r.get("codice_ateco", r.get("ateco", "")).strip(),
        "desc_ateco": r.get("descrizione_ateco", r.get("attivita", "N/D")).strip().capitalize(),
        "forma_giuridica": r.get("forma_giuridica", r.get("natura_giuridica", "N/D")).strip(),
        "partita_iva": r.get("partita_iva", r.get("codice_fiscale", "")).strip(),
        "stato": r.get("stato", "Attiva").strip().title(),
        "fonte": "OpenData Toscana",
        "estratto_il": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─────────────────────────────────────────
# FONTE 2: Comune di Firenze OpenData
# ─────────────────────────────────────────

def scrape_comune_firenze(data_da, data_a):
    """
    Tenta di estrarre dal portale OpenData del Comune di Firenze.
    Usa l'API Opendatasoft (explore v2.1)
    """
    log.info("📡 Fonte 2: OpenData Comune di Firenze...")
    risultati = []

    # Dataset attività commerciali Comune di Firenze
    datasets_to_try = [
        "attivita-commerciali-firenze",
        "licenze-commerciali",
        "suap-pratiche-firenze",
        "registro-imprese-firenze",
    ]

    for dataset in datasets_to_try:
        url = f"https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/{dataset}/records"
        params = {
            "limit": 100,
            "order_by": "data_apertura DESC",
            "where": f"data_apertura >= '{data_da}' AND data_apertura <= '{data_a}'",
        }
        resp = safe_get(url, params=params)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                records = data.get("results", [])
                if records:
                    log.info(f"  → Comune FI ({dataset}): {len(records)} record")
                    for r in records:
                        risultati.append(normalizza_record_comune(r, dataset))
                    break
            except Exception as e:
                log.warning(f"  → Errore {dataset}: {e}")

    if not risultati:
        log.warning("  → Comune FI non disponibile, passo alla fonte 3")

    return risultati


def normalizza_record_comune(r, fonte_dataset):
    """Normalizza un record dal formato Comune di Firenze."""
    return {
        "id": genera_id(
            r.get("denominazione", r.get("ragione_sociale", "")),
            r.get("data_apertura", r.get("data_iscrizione", "")),
            r.get("indirizzo", ""),
        ),
        "denominazione": r.get("denominazione", r.get("ragione_sociale", r.get("nome", "N/D"))).strip().title(),
        "data_iscrizione": normalizza_data(r.get("data_apertura", r.get("data_iscrizione", r.get("data_inizio", "")))),
        "indirizzo": r.get("indirizzo", r.get("via", r.get("sede", "N/D"))).strip().title(),
        "comune": "Firenze",
        "provincia": "FI",
        "codice_ateco": r.get("codice_ateco", "").strip(),
        "desc_ateco": r.get("tipo_attivita", r.get("categoria", r.get("settore", "N/D"))).strip().capitalize(),
        "forma_giuridica": r.get("forma_giuridica", r.get("tipo_soggetto", "N/D")).strip(),
        "partita_iva": r.get("partita_iva", r.get("codice_fiscale", "")).strip(),
        "stato": "Attiva",
        "fonte": f"Comune di Firenze ({fonte_dataset})",
        "estratto_il": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─────────────────────────────────────────
# FONTE 3: Scraping Registro Imprese (fallback)
# ─────────────────────────────────────────

def scrape_registro_imprese(data_da, data_a):
    """
    Fallback: scraping del portale Registro Imprese.
    Cerca le nuove iscrizioni nella provincia di Firenze.
    NOTA: può essere soggetto a CAPTCHA/blocchi.
    """
    log.info("📡 Fonte 3: Registro Imprese (fallback scraping)...")
    risultati = []

    # Tentativo di accesso alla ricerca avanzata
    search_url = "https://www.registroimprese.it/ricerca-imprese"
    params = {
        "provincia": "FI",
        "dataIscrizioneDal": data_da.replace("-", "/"),
        "dataIscrizioneAl": data_a.replace("-", "/"),
        "stato": "A",  # Attive
    }

    resp = safe_get(search_url, params=params)
    if not resp:
        log.warning("  → Registro Imprese non raggiungibile")
        return risultati

    try:
        soup = BeautifulSoup(resp.text, "lxml")

        # Cerca tabella risultati (struttura tipica del portale)
        tabella = soup.find("table", {"class": ["results-table", "table-imprese", "datatable"]})
        if not tabella:
            tabella = soup.find("table")

        if tabella:
            righe = tabella.find_all("tr")[1:]  # salta header
            log.info(f"  → Trovate {len(righe)} righe nella tabella")

            for riga in righe[:MAX_RESULTS]:
                celle = riga.find_all("td")
                if len(celle) >= 3:
                    nome = celle[0].get_text(strip=True)
                    data_isc = celle[1].get_text(strip=True) if len(celle) > 1 else ""
                    indirizzo = celle[2].get_text(strip=True) if len(celle) > 2 else ""
                    forma = celle[3].get_text(strip=True) if len(celle) > 3 else "N/D"
                    ateco = celle[4].get_text(strip=True) if len(celle) > 4 else ""

                    if nome and nome != "N/D":
                        risultati.append({
                            "id": genera_id(nome, data_isc, indirizzo),
                            "denominazione": nome.strip().title(),
                            "data_iscrizione": normalizza_data(data_isc),
                            "indirizzo": indirizzo.strip().title(),
                            "comune": "Firenze",
                            "provincia": "FI",
                            "codice_ateco": ateco.strip(),
                            "desc_ateco": "N/D",
                            "forma_giuridica": forma.strip(),
                            "partita_iva": "",
                            "stato": "Attiva",
                            "fonte": "Registro Imprese",
                            "estratto_il": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
        else:
            log.warning("  → Tabella risultati non trovata (possibile CAPTCHA)")
    except Exception as e:
        log.error(f"  → Errore scraping Registro Imprese: {e}")

    return risultati


# ─────────────────────────────────────────
# FONTE 4: Dati Demo / Seed (sempre disponibile)
# ─────────────────────────────────────────

def genera_dati_demo(data_da, data_a):
    """
    Genera dati realistici di esempio quando le fonti online non sono disponibili.
    Usati come seed iniziale per testare la dashboard.
    """
    log.info("📡 Fonte 4: Generazione dati demo realistici...")

    settori = [
        ("56.10.11", "Ristoranti con somministrazione"),
        ("47.11.10", "Supermercati e ipermercati"),
        ("86.21.00", "Studi medici e odontoiatrici"),
        ("62.01.00", "Produzione software e consulenza informatica"),
        ("82.11.00", "Servizi di supporto alle imprese"),
        ("90.01.09", "Altre rappresentazioni artistiche"),
        ("47.71.10", "Commercio abbigliamento"),
        ("68.20.01", "Locazione immobiliare"),
        ("74.10.21", "Graphic design e comunicazione"),
        ("55.10.00", "Alberghi e strutture simili"),
        ("85.59.20", "Corsi di formazione professionale"),
        ("43.22.01", "Installazione impianti idraulici"),
        ("96.09.09", "Altre attività di servizi alla persona"),
        ("49.41.00", "Trasporto merci su strada"),
        ("41.20.00", "Costruzione edifici residenziali"),
    ]

    forme = [
        "Società a Responsabilità Limitata",
        "Ditta Individuale",
        "Società in Nome Collettivo",
        "Società per Azioni",
        "Cooperativa",
        "Impresa Familiare",
    ]

    vie_firenze = [
        "Via Guelfa", "Borgo San Lorenzo", "Via dei Servi",
        "Lungarno Corsini", "Via della Vigna Nuova", "Piazza della Repubblica",
        "Via Tornabuoni", "Via dei Calzaiuoli", "Viale Gramsci",
        "Via Bolognese", "Via Senese", "Via Pisana",
        "Viale Michelangelo", "Via Masaccio", "Borgo Ognissanti",
        "Via delle Porte Nuove", "Via Benedetto Marcello", "Via Paisiello",
    ]

    comuni_fi = [
        "Firenze", "Scandicci", "Sesto Fiorentino", "Campi Bisenzio",
        "Bagno a Ripoli", "Fiesole", "Empoli", "Pontassieve",
    ]

    import random
    random.seed(42)

    data_inizio = datetime.strptime(data_da, "%Y-%m-%d")
    data_fine = datetime.strptime(data_a, "%Y-%m-%d")
    delta = (data_fine - data_inizio).days

    nomi_prefissi = [
        "Arte e", "Studio", "Progetto", "Officina", "Bottega",
        "Il", "La", "Casa", "Centro", "Agenzia", "Laboratorio",
    ]
    nomi_suffissi = [
        "Toscana", "Fiorentina", "Italia", "Group", "Solutions",
        "Services", "Design", "Studio", "& Co.", "Professional",
    ]
    nomi_base = [
        "Creativa", "Digitale", "Moderna", "Innovazione", "Futuro",
        "Tradizione", "Qualità", "Eccellenza", "Artigianale", "Premium",
    ]

    dati = []
    # Genera tra 15 e 40 imprese casuali nel periodo
    n_imprese = random.randint(15, 40)

    for i in range(n_imprese):
        giorno_offset = random.randint(0, max(delta, 0))
        data_isc = (data_inizio + timedelta(days=giorno_offset)).strftime("%Y-%m-%d")

        settore = random.choice(settori)
        forma = random.choice(forme)
        via = random.choice(vie_firenze)
        civico = random.randint(1, 150)
        comune = random.choice(comuni_fi)

        nome_parts = [
            random.choice(nomi_prefissi),
            random.choice(nomi_base),
            random.choice(nomi_suffissi),
        ]
        nome = " ".join(nome_parts)
        if "Srl" in forma or "Limitata" in forma:
            nome += " Srl"
        elif "Azioni" in forma:
            nome += " SpA"

        piva = f"0{random.randint(1000000000, 9999999999)}"

        dati.append({
            "id": genera_id(nome, data_isc, via),
            "denominazione": nome.title(),
            "data_iscrizione": data_isc,
            "indirizzo": f"{via}, {civico}",
            "comune": comune,
            "provincia": "FI",
            "codice_ateco": settore[0],
            "desc_ateco": settore[1],
            "forma_giuridica": forma,
            "partita_iva": piva,
            "stato": "Attiva",
            "fonte": "Dati Demo",
            "estratto_il": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    # Ordina per data discendente
    dati.sort(key=lambda x: x["data_iscrizione"], reverse=True)
    log.info(f"  → Generati {len(dati)} record demo")
    return dati


# ─────────────────────────────────────────
# ORCHESTRATORE PRINCIPALE
# ─────────────────────────────────────────

def deduplica(lista):
    """Rimuove duplicati basandosi sull'ID."""
    seen = set()
    unici = []
    for item in lista:
        if item["id"] not in seen:
            seen.add(item["id"])
            unici.append(item)
    return unici


def esegui_scraping(giorni=DAYS_LOOKBACK, forza_demo=False):
    """
    Esegue lo scraping da tutte le fonti disponibili.
    Ritorna la lista unificata di imprese ordinate per data.
    """
    log.info("=" * 60)
    log.info(f"🚀 Avvio scraping — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"   Provincia: {PROVINCIA_NAME} ({PROVINCIA_CODE})")
    log.info(f"   Periodo: ultimi {giorni} giorni")
    log.info("=" * 60)

    data_a = datetime.now().strftime("%Y-%m-%d")
    data_da = (datetime.now() - timedelta(days=giorni)).strftime("%Y-%m-%d")

    tutti_risultati = []

    if not forza_demo:
        # Fonte 1: OpenData Toscana
        r1 = scrape_opendata_toscana(data_da, data_a)
        tutti_risultati.extend(r1)

        # Fonte 2: Comune di Firenze (solo se fonte 1 vuota)
        if not r1:
            r2 = scrape_comune_firenze(data_da, data_a)
            tutti_risultati.extend(r2)

        # Fonte 3: Registro Imprese (solo se entrambe le fonti precedenti vuote)
        if not tutti_risultati:
            r3 = scrape_registro_imprese(data_da, data_a)
            tutti_risultati.extend(r3)

    # Fonte 4: Demo (sempre usata se tutto il resto fallisce o forzata)
    if not tutti_risultati or forza_demo:
        r4 = genera_dati_demo(data_da, data_a)
        tutti_risultati.extend(r4)

    # Deduplica e ordina
    risultati_finali = deduplica(tutti_risultati)
    risultati_finali.sort(key=lambda x: x.get("data_iscrizione", ""), reverse=True)

    log.info(f"✅ Totale imprese trovate: {len(risultati_finali)}")
    return risultati_finali


def salva_risultati(risultati):
    """Salva i risultati nel file JSON con metadati."""
    os.makedirs(DATA_DIR, exist_ok=True)

    output = {
        "metadata": {
            "ultimo_aggiornamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "provincia": PROVINCIA_NAME,
            "codice_provincia": PROVINCIA_CODE,
            "totale_imprese": len(risultati),
            "periodo_analizzato_giorni": DAYS_LOOKBACK,
            "data_da": (datetime.now() - timedelta(days=DAYS_LOOKBACK)).strftime("%Y-%m-%d"),
            "data_a": datetime.now().strftime("%Y-%m-%d"),
        },
        "imprese": risultati,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"💾 Dati salvati in: {OUTPUT_FILE}")
    return output


def carica_dati_esistenti():
    """Carica i dati salvati precedentemente."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Errore lettura dati esistenti: {e}")
    return None


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scraper Imprese Firenze")
    parser.add_argument("--giorni", type=int, default=DAYS_LOOKBACK,
                        help=f"Giorni da analizzare (default: {DAYS_LOOKBACK})")
    parser.add_argument("--demo", action="store_true",
                        help="Usa dati demo senza accedere alle fonti online")
    parser.add_argument("--dry-run", action="store_true",
                        help="Esegue lo scraping ma non salva i dati")
    args = parser.parse_args()

    risultati = esegui_scraping(giorni=args.giorni, forza_demo=args.demo)

    if not args.dry_run:
        salva_risultati(risultati)
        print(f"\n✅ Completato! {len(risultati)} imprese salvate in {OUTPUT_FILE}")
    else:
        print(f"\n✅ Dry-run completato! {len(risultati)} imprese trovate (non salvate)")
        for r in risultati[:5]:
            print(f"  → {r['data_iscrizione']} | {r['denominazione']} | {r['comune']}")
