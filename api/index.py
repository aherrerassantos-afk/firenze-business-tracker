"""
api/index.py — Entry point Vercel per Flask
Vercel esegue questo file come serverless function.
I dati vengono generati on-demand (no file persistenti su Vercel).
"""
import sys
import os

# Aggiungi la root del progetto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa l'app Flask dal file principale
from app import app

# Vercel cerca una variabile chiamata `app` o `handler`
# Flask app è già configurata in app.py
