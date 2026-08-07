#!/bin/bash
# ══════════════════════════════════════════════════════
# start.sh — Avvio Server Firenze Business Tracker
# ══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   🏛️  Firenze Business Tracker            ║"
echo "║   Server Multi-Utente v1.0               ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Verifica Python ──────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 non trovato. Installalo prima di continuare."
  exit 1
fi
echo "✅ Python: $(python3 --version)"

# ── 2. Crea / Attiva virtual environment ─────────────
if [ ! -d "venv" ]; then
  echo "📦 Creazione ambiente virtuale..."
  python3 -m venv venv
fi

source venv/bin/activate
echo "✅ Virtual environment attivato"

# ── 3. Installa dipendenze ───────────────────────────
echo "📦 Installazione dipendenze..."
pip install -q -r scraper/requirements.txt
echo "✅ Dipendenze installate"

# ── 4. Crea directory dati ──────────────────────────
mkdir -p data
echo "✅ Directory data/ pronta"

# ── 5. Prima esecuzione scraper (dati demo) ──────────
if [ ! -f "data/imprese_firenze.json" ]; then
  echo "🔄 Prima esecuzione: genero dati demo iniziali..."
  python3 scraper/scraper.py --demo
  echo "✅ Dati demo generati"
fi

# ── 6. Avvio server ──────────────────────────────────
echo ""
echo "🚀 Avvio server web..."
echo "🌐 Dashboard: http://0.0.0.0:5000"
echo "📡 API:       http://0.0.0.0:5000/api/imprese"
echo ""
echo "Premi Ctrl+C per fermare il server"
echo ""

# Usa gunicorn per produzione, flask per sviluppo
if command -v gunicorn &>/dev/null; then
  exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 4 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    "app:app"
else
  exec python3 app.py
fi
