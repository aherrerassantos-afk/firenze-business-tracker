"""
app.py — Server Flask Multi-Utente
Firenze Business Tracker — API + Dashboard Web
"""

import os
import sys
import json
import logging
import threading
import schedule
import time
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

# Aggiungi il path per importare il modulo scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper.config import SERVER_HOST, SERVER_PORT, DEBUG_MODE, OUTPUT_FILE, LOG_FILE
from scraper.scraper import esegui_scraping, salva_risultati, carica_dati_esistenti

# ─────────────────────────────────────────
# App Flask
# ─────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)  # Abilita CORS per accesso da browser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# Stato globale aggiornamento
stato_aggiornamento = {
    "in_corso": False,
    "ultimo_aggiornamento": None,
    "ultimo_esito": None,
}


# ─────────────────────────────────────────
# Funzione aggiornamento dati
# ─────────────────────────────────────────

def aggiorna_dati(giorni=7, forza_demo=False):
    """Esegue lo scraping e salva i risultati."""
    global stato_aggiornamento
    if stato_aggiornamento["in_corso"]:
        log.info("Aggiornamento già in corso, skip.")
        return

    stato_aggiornamento["in_corso"] = True
    try:
        log.info("🔄 Avvio aggiornamento dati automatico...")
        risultati = esegui_scraping(giorni=giorni, forza_demo=forza_demo)
        salva_risultati(risultati)
        stato_aggiornamento["ultimo_aggiornamento"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stato_aggiornamento["ultimo_esito"] = f"✅ {len(risultati)} imprese aggiornate"
        log.info(f"✅ Aggiornamento completato: {len(risultati)} imprese")
    except Exception as e:
        stato_aggiornamento["ultimo_esito"] = f"❌ Errore: {str(e)}"
        log.error(f"❌ Errore aggiornamento: {e}")
    finally:
        stato_aggiornamento["in_corso"] = False


# ─────────────────────────────────────────
# Routes — API REST
# ─────────────────────────────────────────

@app.route("/")
def index():
    """Serve la dashboard principale."""
    return render_template("index.html")


@app.route("/api/imprese")
def api_imprese():
    """
    Ritorna la lista delle imprese.
    Query params:
      - giorni: int (default 7)
      - limit: int (default 100)
      - search: string (ricerca per nome)
      - comune: string (filtra per comune)
      - ateco: string (filtra per codice ATECO)
    """
    dati = carica_dati_esistenti()

    if not dati:
        # Prima esecuzione: genera dati demo
        log.info("Nessun dato trovato, genero dati demo per prima esecuzione...")
        risultati = esegui_scraping(forza_demo=True)
        dati = salva_risultati(risultati)

    imprese = dati.get("imprese", [])
    metadata = dati.get("metadata", {})

    # Filtri
    search = request.args.get("search", "").lower().strip()
    comune = request.args.get("comune", "").lower().strip()
    ateco = request.args.get("ateco", "").strip()
    limit = min(int(request.args.get("limit", 100)), 500)
    giorni = int(request.args.get("giorni", 7))

    # Applica filtri
    if search:
        imprese = [
            i for i in imprese
            if search in i.get("denominazione", "").lower()
            or search in i.get("indirizzo", "").lower()
            or search in i.get("desc_ateco", "").lower()
        ]
    if comune:
        imprese = [i for i in imprese if comune in i.get("comune", "").lower()]
    if ateco:
        imprese = [i for i in imprese if ateco in i.get("codice_ateco", "")]

    # Limita risultati
    imprese_filtrate = imprese[:limit]

    return jsonify({
        "success": True,
        "metadata": metadata,
        "filtri_applicati": {
            "search": search or None,
            "comune": comune or None,
            "ateco": ateco or None,
            "limit": limit,
            "giorni": giorni,
        },
        "totale_filtrato": len(imprese_filtrate),
        "totale_disponibile": len(imprese),
        "imprese": imprese_filtrate,
    })


@app.route("/api/stats")
def api_stats():
    """Statistiche aggregate sulle imprese."""
    dati = carica_dati_esistenti()
    if not dati:
        return jsonify({"success": False, "error": "Nessun dato disponibile"}), 404

    imprese = dati.get("imprese", [])
    metadata = dati.get("metadata", {})

    # Statistiche per comune
    per_comune = {}
    for imp in imprese:
        c = imp.get("comune", "N/D")
        per_comune[c] = per_comune.get(c, 0) + 1

    # Statistiche per settore ATECO
    per_ateco = {}
    for imp in imprese:
        desc = imp.get("desc_ateco", "N/D")
        per_ateco[desc] = per_ateco.get(desc, 0) + 1

    # Top 10
    top_comuni = sorted(per_comune.items(), key=lambda x: x[1], reverse=True)[:10]
    top_ateco = sorted(per_ateco.items(), key=lambda x: x[1], reverse=True)[:10]

    # Per forma giuridica
    per_forma = {}
    for imp in imprese:
        f = imp.get("forma_giuridica", "N/D")
        per_forma[f] = per_forma.get(f, 0) + 1

    # Trend giornaliero (ultimi 7 giorni)
    trend = {}
    for imp in imprese:
        data = imp.get("data_iscrizione", "")[:10]
        if data:
            trend[data] = trend.get(data, 0) + 1
    trend_ordinato = sorted(trend.items())

    return jsonify({
        "success": True,
        "metadata": metadata,
        "totale_imprese": len(imprese),
        "per_comune": dict(top_comuni),
        "top_settori": dict(top_ateco),
        "per_forma_giuridica": per_forma,
        "trend_giornaliero": trend_ordinato,
        "stato_aggiornamento": stato_aggiornamento,
    })


@app.route("/api/aggiorna", methods=["POST"])
def api_aggiorna():
    """Forza aggiornamento manuale dei dati."""
    if stato_aggiornamento["in_corso"]:
        return jsonify({"success": False, "message": "Aggiornamento già in corso"}), 409

    giorni = int(request.json.get("giorni", 7)) if request.json else 7
    forza_demo = request.json.get("demo", False) if request.json else False

    # Esegui in thread separato per non bloccare il server
    thread = threading.Thread(
        target=aggiorna_dati,
        kwargs={"giorni": giorni, "forza_demo": forza_demo},
        daemon=True,
    )
    thread.start()

    return jsonify({
        "success": True,
        "message": "Aggiornamento avviato in background",
        "giorni": giorni,
    })


@app.route("/api/stato")
def api_stato():
    """Stato corrente del sistema."""
    return jsonify({
        "success": True,
        "server": "Firenze Business Tracker",
        "versione": "1.0.0",
        "stato_aggiornamento": stato_aggiornamento,
        "dati_disponibili": os.path.exists(OUTPUT_FILE),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/comuni")
def api_comuni():
    """Lista dei comuni disponibili nei dati."""
    dati = carica_dati_esistenti()
    if not dati:
        return jsonify({"comuni": []})
    comuni = sorted(set(
        i.get("comune", "N/D") for i in dati.get("imprese", [])
    ))
    return jsonify({"comuni": comuni})


@app.route("/api/export/csv")
def api_export_csv():
    """Export dei dati in formato CSV."""
    import io
    import csv
    from flask import Response

    dati = carica_dati_esistenti()
    if not dati:
        return jsonify({"error": "Nessun dato"}), 404

    imprese = dati.get("imprese", [])

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "denominazione", "data_iscrizione", "comune", "indirizzo",
        "forma_giuridica", "codice_ateco", "desc_ateco",
        "partita_iva", "stato", "fonte", "estratto_il"
    ])
    writer.writeheader()
    for imp in imprese:
        writer.writerow({k: imp.get(k, "") for k in writer.fieldnames})

    data_oggi = datetime.now().strftime("%Y%m%d")
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=imprese_firenze_{data_oggi}.csv"
        },
    )


# ─────────────────────────────────────────
# Scheduler automatico
# ─────────────────────────────────────────

def avvia_scheduler():
    """Avvia il cron job giornaliero per aggiornamento automatico."""
    schedule.every().day.at("06:00").do(aggiorna_dati)
    log.info("⏰ Scheduler avviato: aggiornamento giornaliero alle 06:00")

    def runner():
        while True:
            schedule.run_pending()
            time.sleep(60)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()


# ─────────────────────────────────────────
# Avvio Server
# ─────────────────────────────────────────

if __name__ == "__main__":
    log.info("🚀 Firenze Business Tracker — Avvio server...")

    # Prima esecuzione: genera dati demo se non esistono
    if not os.path.exists(OUTPUT_FILE):
        log.info("📋 Prima esecuzione: genero dati demo iniziali...")
        aggiorna_dati(forza_demo=True)

    # Avvia scheduler automatico
    avvia_scheduler()

    # Avvia server Flask
    # Su Render.com la porta è definita dalla variabile d'ambiente $PORT
    port = int(os.environ.get("PORT", SERVER_PORT))
    log.info(f"🌐 Server in ascolto su http://{SERVER_HOST}:{port}")
    app.run(
        host=SERVER_HOST,
        port=port,
        debug=DEBUG_MODE,
        use_reloader=False,  # Disabilitato per non duplicare il scheduler
    )
