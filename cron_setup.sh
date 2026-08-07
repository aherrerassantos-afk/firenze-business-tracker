#!/bin/bash
# ══════════════════════════════════════════════════════
# cron_setup.sh — Configura aggiornamento automatico
# Eseguire UNA SOLA VOLTA sul server
# ══════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$SCRIPT_DIR/venv/bin/python3"
SCRAPER="$SCRIPT_DIR/scraper/scraper.py"
LOG="$SCRIPT_DIR/cron.log"

echo "⏰ Configurazione cron job giornaliero..."

# Cron line: ogni giorno alle 06:00
CRON_LINE="0 6 * * * $PYTHON $SCRAPER >> $LOG 2>&1"

# Aggiunge solo se non esiste già
(crontab -l 2>/dev/null | grep -v "$SCRAPER"; echo "$CRON_LINE") | crontab -

echo "✅ Cron job configurato:"
echo "   Orario:  Ogni giorno alle 06:00"
echo "   Script:  $SCRAPER"
echo "   Log:     $LOG"
echo ""
crontab -l | grep "$SCRAPER"
echo ""
echo "✅ Setup completato!"
echo ""
echo "Comandi utili:"
echo "  crontab -l          → visualizza tutti i cron job"
echo "  crontab -r          → rimuove tutti i cron job"
echo "  tail -f $LOG → monitora log in tempo reale"
