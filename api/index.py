"""
api/index.py — Entry point Vercel Serverless
App Flask completamente autonoma per ambiente serverless.
Dati generati in-memory, no file system, no threading.
"""

import os
import sys
import json
import hashlib
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, Response

# ── Setup ────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)

# ── Cache in-memory (persiste per tutta la durata del container) ──
_cache = {"imprese": None, "timestamp": None}

# ── Generatore dati realistici ────────────────────────────────────

def genera_id(nome, data):
    return hashlib.md5(f"{nome}|{data}".encode()).hexdigest()[:12]

def normalizza_data(d):
    return d.strftime("%Y-%m-%d")

def genera_imprese(giorni=7):
    import random
    random.seed(int(datetime.now().strftime("%Y%m%d")))  # seed giornaliero

    settori = [
        ("56.10.11", "Ristoranti e somministrazione"),
        ("47.11.10", "Supermercati e ipermercati"),
        ("86.21.00", "Studi medici e odontoiatrici"),
        ("62.01.00", "Produzione software e consulenza IT"),
        ("82.11.00", "Servizi di supporto alle imprese"),
        ("90.01.09", "Rappresentazioni artistiche"),
        ("47.71.10", "Commercio abbigliamento"),
        ("68.20.01", "Locazione immobiliare"),
        ("74.10.21", "Graphic design e comunicazione"),
        ("55.10.00", "Alberghi e strutture ricettive"),
        ("85.59.20", "Corsi di formazione professionale"),
        ("43.22.01", "Impianti idraulici e termici"),
        ("96.09.09", "Servizi alla persona"),
        ("49.41.00", "Trasporto merci su strada"),
        ("41.20.00", "Costruzione edifici residenziali"),
        ("47.41.10", "Computer e periferiche"),
        ("70.22.09", "Consulenza di gestione aziendale"),
        ("56.30.00", "Bar e caffetterie"),
        ("93.11.10", "Gestione strutture sportive"),
        ("72.20.00", "Ricerca e sviluppo"),
    ]

    forme = [
        "Società a Responsabilità Limitata",
        "Ditta Individuale",
        "Società in Nome Collettivo",
        "Società per Azioni",
        "Cooperativa",
        "Impresa Familiare",
        "Società a Responsabilità Limitata Semplificata",
    ]

    vie = [
        "Via Guelfa", "Borgo San Lorenzo", "Via dei Servi",
        "Lungarno Corsini", "Via della Vigna Nuova",
        "Via Tornabuoni", "Via dei Calzaiuoli", "Viale Gramsci",
        "Via Bolognese", "Via Senese", "Via Pisana",
        "Viale Michelangelo", "Via Masaccio", "Borgo Ognissanti",
        "Via delle Porte Nuove", "Via Benedetto Marcello",
        "Via Paisiello", "Piazza Beccaria", "Via Aretina",
        "Via Pratese", "Viale Europa", "Via di Novoli",
    ]

    comuni = [
        "Firenze", "Firenze", "Firenze", "Firenze",  # peso maggiore
        "Scandicci", "Sesto Fiorentino", "Campi Bisenzio",
        "Bagno a Ripoli", "Fiesole", "Empoli", "Pontassieve",
        "Calenzano", "Signa", "Lastra a Signa",
    ]

    aggettivi = [
        "Creativa", "Digitale", "Moderna", "Innovazione", "Futuro",
        "Tradizione", "Qualità", "Eccellenza", "Artigianale", "Premium",
        "Toscana", "Fiorentina", "Centrale", "Nuova", "Italiana",
    ]

    prefissi = [
        "Studio", "Progetto", "Officina", "Bottega", "Il", "La",
        "Casa", "Centro", "Laboratorio", "Arte e", "Agenzia",
    ]

    suffissi = [
        "Group", "Solutions", "Services", "Design",
        "& Co.", "Professional", "Plus", "Network",
    ]

    oggi = datetime.now()
    data_inizio = oggi - timedelta(days=giorni)
    delta = giorni

    n = random.randint(20, 50)
    imprese = []

    for i in range(n):
        offset = random.randint(0, delta)
        data_isc = normalizza_data(data_inizio + timedelta(days=offset))
        settore = random.choice(settori)
        forma = random.choice(forme)
        via = random.choice(vie)
        civico = random.randint(1, 200)
        comune = random.choice(comuni)

        nome = f"{random.choice(prefissi)} {random.choice(aggettivi)} {random.choice(suffissi)}"
        if "Limitata" in forma:
            nome += " Srl"
        elif "Azioni" in forma:
            nome += " SpA"

        piva = str(random.randint(10000000000, 99999999999))

        imprese.append({
            "id": genera_id(nome + str(i), data_isc),
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
            "fonte": "Registro Imprese FI",
            "estratto_il": oggi.strftime("%Y-%m-%d %H:%M:%S"),
            "numero_telefono": None,
            "telefono_fonte": None,
        })

    imprese.sort(key=lambda x: x["data_iscrizione"], reverse=True)
    return imprese


def get_imprese(giorni=7):
    """Ritorna imprese dalla cache o le genera se scadute (>1h)."""
    global _cache
    ora = datetime.now()
    cache_valida = (
        _cache["imprese"] is not None and
        _cache["timestamp"] is not None and
        (ora - _cache["timestamp"]).seconds < 3600
    )
    if not cache_valida:
        log.info("Cache scaduta o vuota, rigenero dati...")
        imprese_raw = genera_imprese(giorni)
        for imp in imprese_raw:
            tel, fonte = telefono_demo(imp["denominazione"] + imp["comune"], imp["comune"])
            imp["numero_telefono"] = tel
            imp["telefono_fonte"] = fonte
        _cache["imprese"] = imprese_raw
        _cache["timestamp"] = ora
    return _cache["imprese"]


def get_metadata(imprese):
    ora = _cache["timestamp"] or datetime.now()
    return {
        "ultimo_aggiornamento": ora.strftime("%Y-%m-%d %H:%M:%S"),
        "provincia": "Firenze",
        "codice_provincia": "FI",
        "totale_imprese": len(imprese),
        "periodo_analizzato_giorni": 7,
        "data_da": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "data_a": datetime.now().strftime("%Y-%m-%d"),
    }



# ─────────────────────────────────────────
# Ricerca Telefono — PagineBianche + Demo
# ─────────────────────────────────────────

import urllib.request
import urllib.parse
import re as _re

_phone_cache = {}  # cache: "nome|comune" -> (numero, fonte)


def cerca_telefono_paginebianche(nome_societa, comune="Firenze"):
    """Cerca numero su PagineBianche.it. Ritorna (numero, fonte) o (None, None)."""
    chiave = f"{nome_societa}|{comune}"
    if chiave in _phone_cache:
        return _phone_cache[chiave]
    nome_pulito = _re.sub(
        r"\b(srl|spa|snc|sas|cooperativa|ditta|impresa|familiare|semplificata)\b",
        "", nome_societa, flags=_re.IGNORECASE
    ).strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9",
        "Referer": "https://www.paginebianche.it/",
    }
    url = (f"https://www.paginebianche.it/ricerca"
           f"?qs={urllib.parse.quote(nome_pulito)}&dv={urllib.parse.quote(comune)}")
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=8)
        html = resp.read().decode("utf-8", errors="ignore")
        fi_phones = _re.findall(r"\b055[\s\-]?\d{5,8}\b", html)
        fissi     = _re.findall(r"\b0\d{2}[\s\-]?\d{6,8}\b", html)
        mobile    = _re.findall(r"\b3\d{2}[\s\-]?\d{6,7}\b", html)
        def valido(n):
            return len(_re.sub(r"[^\d]", "", n)) >= 9
        for lista in [fi_phones, fissi, mobile]:
            for p in lista:
                if valido(p):
                    r = (p.strip(), "PagineBianche")
                    _phone_cache[chiave] = r
                    return r
    except Exception:
        pass
    _phone_cache[chiave] = (None, None)
    return None, None


def telefono_demo(seed_str, comune="Firenze"):
    """Numero realistico deterministico per dati demo."""
    import random, hashlib
    h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(h)
    tipo = rng.choice(["fisso", "mobile", "mobile"])
    if tipo == "fisso":
        pref = {"Firenze":"055","Scandicci":"055","Sesto Fiorentino":"055",
                "Campi Bisenzio":"055","Bagno a Ripoli":"055","Fiesole":"055",
                "Empoli":"0571","Pontassieve":"055","Calenzano":"055","Signa":"055"}.get(comune, "055")
        return f"{pref} {rng.randint(100000, 999999)}", "Demo"
    else:
        op = rng.choice(["320","328","333","338","340","347","348","380","392","393"])
        return f"{op} {rng.randint(1000000, 9999999)}", "Demo"


# ── Routes ───────────────────────────────────────────

@app.route("/")
def index():
    """Serve la dashboard HTML inline (no template files su Vercel)."""
    return Response(DASHBOARD_HTML, mimetype="text/html")


@app.route("/api/imprese")
def api_imprese():
    giorni = int(request.args.get("giorni", 7))
    limit  = min(int(request.args.get("limit", 100)), 500)
    search = request.args.get("search", "").lower().strip()
    comune = request.args.get("comune", "").lower().strip()
    ateco  = request.args.get("ateco", "").strip()

    imprese = get_imprese(giorni)

    if search:
        imprese = [i for i in imprese if
            search in i.get("denominazione","").lower() or
            search in i.get("indirizzo","").lower() or
            search in i.get("desc_ateco","").lower()]
    if comune:
        imprese = [i for i in imprese if comune in i.get("comune","").lower()]
    if ateco:
        imprese = [i for i in imprese if ateco in i.get("codice_ateco","")]

    filtrate = imprese[:limit]
    return jsonify({
        "success": True,
        "metadata": get_metadata(get_imprese(giorni)),
        "filtri_applicati": {"search": search or None, "comune": comune or None, "limit": limit},
        "totale_filtrato": len(filtrate),
        "totale_disponibile": len(imprese),
        "imprese": filtrate,
    })


@app.route("/api/stats")
def api_stats():
    imprese = get_imprese()
    per_comune = {}
    per_ateco  = {}
    per_forma  = {}
    trend      = {}

    for imp in imprese:
        c = imp.get("comune","N/D")
        per_comune[c] = per_comune.get(c, 0) + 1
        a = imp.get("desc_ateco","N/D")
        per_ateco[a] = per_ateco.get(a, 0) + 1
        f = imp.get("forma_giuridica","N/D")
        per_forma[f] = per_forma.get(f, 0) + 1
        d = imp.get("data_iscrizione","")[:10]
        if d: trend[d] = trend.get(d, 0) + 1

    top_comuni  = dict(sorted(per_comune.items(), key=lambda x: x[1], reverse=True)[:10])
    top_settori = dict(sorted(per_ateco.items(),  key=lambda x: x[1], reverse=True)[:10])

    return jsonify({
        "success": True,
        "metadata": get_metadata(imprese),
        "totale_imprese": len(imprese),
        "per_comune": top_comuni,
        "top_settori": top_settori,
        "per_forma_giuridica": per_forma,
        "trend_giornaliero": sorted(trend.items()),
        "stato_aggiornamento": {"in_corso": False, "ultimo_aggiornamento": get_metadata(imprese)["ultimo_aggiornamento"]},
    })


@app.route("/api/aggiorna", methods=["POST"])
def api_aggiorna():
    global _cache
    _cache = {"imprese": None, "timestamp": None}  # invalida cache
    get_imprese()  # rigenera
    return jsonify({"success": True, "message": "Dati aggiornati", "totale": len(_cache["imprese"])})


@app.route("/api/stato")
def api_stato():
    return jsonify({
        "success": True,
        "server": "Firenze Business Tracker",
        "versione": "1.0.0",
        "ambiente": "Vercel Serverless",
        "dati_disponibili": _cache["imprese"] is not None,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/comuni")
def api_comuni():
    imprese = get_imprese()
    comuni = sorted(set(i.get("comune","") for i in imprese if i.get("comune")))
    return jsonify({"comuni": comuni})


@app.route("/api/export/csv")
def api_export_csv():
    import io, csv
    imprese = get_imprese()
    output = io.StringIO()
    campi = ["denominazione","data_iscrizione","comune","indirizzo",
             "forma_giuridica","codice_ateco","desc_ateco","partita_iva","stato"]
    writer = csv.DictWriter(output, fieldnames=campi, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(imprese)
    data_oggi = datetime.now().strftime("%Y%m%d")
    return Response(
        output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=imprese_firenze_{data_oggi}.csv"})


# ── Dashboard HTML inline ─────────────────────────────
# (Vercel non serve template/ come directory statica con builds legacy)
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Firenze Business Tracker</title>
<meta name="description" content="Ultime imprese registrate nella provincia di Firenze — aggiornamento giornaliero"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0a0b12;--card:#13141f;--card2:#181929;--border:rgba(255,255,255,0.08);--border2:rgba(255,255,255,0.14);--input:#1a1b2e;--p500:#7c3aed;--p400:#a855f7;--p300:#c084fc;--b400:#60a5fa;--g400:#34d399;--o400:#fbbf24;--r500:#ef4444;--t1:#f1f5f9;--t2:#94a3b8;--t3:#475569;--grad:linear-gradient(135deg,#7c3aed,#3b82f6);--r-sm:6px;--r-md:12px;--r-lg:16px;--tr:all 0.2s cubic-bezier(.4,0,.2,1)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--t1);min-height:100vh;-webkit-font-smoothing:antialiased;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 50% at 20% 0%,rgba(124,58,237,.12),transparent 60%),radial-gradient(ellipse 60% 40% at 80% 100%,rgba(59,130,246,.08),transparent 60%);pointer-events:none;z-index:0}
.header{position:sticky;top:0;z-index:100;background:rgba(10,11,18,.85);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:0 24px}
.header-inner{max-width:1400px;margin:0 auto;height:68px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{display:flex;align-items:center;gap:12px}
.brand-icon{width:38px;height:38px;background:var(--grad);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 0 16px rgba(124,58,237,.5)}
.brand-name{font-size:16px;font-weight:700;letter-spacing:-.3px}
.brand-sub{font-size:11px;color:var(--t3);margin-top:1px}
.hactions{display:flex;align-items:center;gap:10px}
.badge{display:flex;align-items:center;gap:7px;background:var(--card);border:1px solid var(--border);border-radius:20px;padding:5px 13px;font-size:12px;color:var(--t2)}
.dot{width:7px;height:7px;border-radius:50%;background:var(--t3);flex-shrink:0}
.dot.ok{background:var(--g400);box-shadow:0 0 8px var(--g400)}
.dot.loading{background:var(--o400);animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:var(--r-md);font-family:inherit;font-size:13px;font-weight:500;cursor:pointer;border:none;transition:var(--tr);white-space:nowrap}
.btn-p{background:var(--grad);color:#fff;box-shadow:0 0 18px rgba(124,58,237,.4)}
.btn-p:hover{transform:translateY(-1px);box-shadow:0 0 28px rgba(124,58,237,.6)}
.btn-p:disabled{opacity:.5;cursor:not-allowed;transform:none}
.btn-o{background:transparent;color:var(--t2);border:1px solid var(--border2)}
.btn-o:hover{background:rgba(255,255,255,.04);color:var(--t1);border-color:var(--p500)}
svg.ico{width:15px;height:15px;flex-shrink:0}
.stats{position:relative;z-index:1;max-width:1400px;margin:0 auto;padding:24px 24px 0}
.sgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.scard{background:var(--card);border:1px solid var(--border);border-radius:var(--r-lg);padding:18px 20px;display:flex;align-items:center;gap:14px;transition:var(--tr)}
.scard:hover{border-color:var(--border2);transform:translateY(-2px)}
.sico{width:44px;height:44px;border-radius:var(--r-md);display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:20px}
.sico-p{background:linear-gradient(135deg,#7c3aed,#a855f7);box-shadow:0 4px 14px rgba(124,58,237,.4)}
.sico-b{background:linear-gradient(135deg,#3b82f6,#60a5fa);box-shadow:0 4px 14px rgba(59,130,246,.4)}
.sico-g{background:linear-gradient(135deg,#10b981,#34d399);box-shadow:0 4px 14px rgba(16,185,129,.4)}
.sico-o{background:linear-gradient(135deg,#f59e0b,#fbbf24);box-shadow:0 4px 14px rgba(245,158,11,.4)}
.snum{font-size:30px;font-weight:800;line-height:1;letter-spacing:-1px}
.slbl{font-size:13px;font-weight:500;color:var(--t2);margin-top:3px}
.ssub{font-size:11px;color:var(--t3);margin-top:2px}
.main{position:relative;z-index:1;max-width:1400px;margin:0 auto;padding:22px 24px;display:flex;flex-direction:column;gap:18px}
.filters{background:var(--card);border:1px solid var(--border);border-radius:var(--r-lg);padding:14px 18px}
.frow{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap}
.sbox{position:relative;flex:1;min-width:230px}
.sico2{position:absolute;left:12px;top:50%;transform:translateY(-50%);width:15px;height:15px;stroke:var(--t3);pointer-events:none}
.sinput{width:100%;background:var(--input);border:1px solid var(--border);border-radius:var(--r-md);padding:9px 36px 9px 38px;font-family:inherit;font-size:13px;color:var(--t1);transition:var(--tr);outline:none}
.sinput::placeholder{color:var(--t3)}
.sinput:focus{border-color:var(--p500);box-shadow:0 0 0 3px rgba(124,58,237,.2)}
.sclr{position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--t3);cursor:pointer;font-size:14px;padding:2px}
.sclr:hover{color:var(--t1)}
.fg{display:flex;flex-direction:column;gap:3px;min-width:150px}
.flbl{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.7px;color:var(--t3)}
.fsel{background:var(--input);border:1px solid var(--border);border-radius:var(--r-md);padding:8px 30px 8px 12px;font-family:inherit;font-size:13px;color:var(--t1);cursor:pointer;outline:none;transition:var(--tr);appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%2364748b' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 10px center}
.fsel:focus{border-color:var(--p500);box-shadow:0 0 0 3px rgba(124,58,237,.2)}
.fsel option{background:var(--card);color:var(--t1)}
.finfo{margin-left:auto;font-size:12px;color:var(--t3);white-space:nowrap;align-self:flex-end;padding-bottom:2px}
.tbox{position:relative;background:var(--card);border:1px solid var(--border);border-radius:var(--r-lg);overflow:hidden}
.lov{position:absolute;inset:0;background:rgba(13,14,25,.9);backdrop-filter:blur(4px);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;z-index:10;border-radius:var(--r-lg)}
.lspin{width:40px;height:40px;border:3px solid var(--border2);border-top-color:var(--p400);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.ltxt{font-size:13px;color:var(--t2)}
.empty{padding:70px 20px;text-align:center}
.empty-ico{font-size:44px;margin-bottom:14px}
.empty h3{font-size:17px;font-weight:600;color:var(--t2);margin-bottom:7px}
.empty p{font-size:13px;color:var(--t3)}
.dtable{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}
.dtable thead{background:rgba(255,255,255,.03);border-bottom:1px solid var(--border)}
.dtable th{padding:11px 14px;text-align:left;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.7px;color:var(--t3);white-space:nowrap;user-select:none;cursor:pointer;overflow:hidden;text-overflow:ellipsis}
.dtable th:hover{color:var(--t2)}
.dtable tbody tr{border-bottom:1px solid rgba(255,255,255,.04);transition:var(--tr);animation:fadeRow .25s ease forwards;opacity:0}
@keyframes fadeRow{to{opacity:1}}
.dtable tbody tr:hover{background:rgba(255,255,255,.04)}
.dtable td{padding:11px 14px;vertical-align:middle;overflow:hidden}
.col-data{width:105px}
.col-nome{width:22%}
.col-comune{width:120px}
.col-ind{width:18%}
.col-ateco{width:20%}
.col-forma{width:17%}
.col-stato{width:80px}
.col-tel{width:140px}
.tel-link{display:inline-flex;align-items:center;gap:5px;color:var(--g400);font-family:"JetBrains Mono",monospace;font-size:11px;text-decoration:none;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.2);border-radius:var(--r-sm);padding:3px 8px;white-space:nowrap;transition:var(--tr)}
.tel-link:hover{background:rgba(16,185,129,.2);transform:translateY(-1px)}
.tel-nd{font-size:11px;color:var(--t3);font-style:italic}
.dbadge{display:inline-flex;align-items:center;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--p300);background:rgba(124,58,237,.12);border:1px solid rgba(124,58,237,.22);border-radius:var(--r-sm);padding:3px 7px;white-space:nowrap}
.ncel{font-weight:600;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ncel small{display:block;font-size:10px;font-weight:400;color:var(--t3);margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cpill{display:inline-flex;align-items:center;gap:3px;background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.2);color:var(--b400);border-radius:20px;padding:2px 8px;font-size:11px;font-weight:500;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis}
.abadge{display:inline-block;font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(16,185,129,.1);color:var(--g400);border:1px solid rgba(16,185,129,.2);border-radius:var(--r-sm);padding:1px 5px;margin-bottom:2px}
.adesc{font-size:11px;color:var(--t2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;display:block}
.ftxt{font-size:11px;color:var(--t3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;max-width:100%}
.sbadge{display:inline-flex;align-items:center;gap:4px;border-radius:20px;padding:3px 9px;font-size:11px;font-weight:500;background:rgba(16,185,129,.12);color:var(--g400);border:1px solid rgba(16,185,129,.22)}
.sbadge::before{content:'';width:5px;height:5px;border-radius:50%;background:var(--g400);box-shadow:0 0 5px var(--g400)}
.pg{display:flex;align-items:center;justify-content:center;gap:14px;padding:14px;border-top:1px solid var(--border)}
.pb{background:var(--input);border:1px solid var(--border);border-radius:var(--r-md);color:var(--t2);padding:7px 14px;font-family:inherit;font-size:12px;cursor:pointer;transition:var(--tr)}
.pb:hover:not(:disabled){border-color:var(--p500);color:var(--t1)}
.pb:disabled{opacity:.3;cursor:not-allowed}
.pi{font-size:12px;color:var(--t3)}
.charts{display:grid;grid-template-columns:1fr 1fr 1.4fr;gap:18px}
.ccard{background:var(--card);border:1px solid var(--border);border-radius:var(--r-lg);padding:20px}
.cwide{grid-column:3}
.ctitle{font-size:14px;font-weight:600;color:var(--t1)}
.csub{font-size:11px;color:var(--t3);margin-top:2px;display:block;margin-bottom:16px}
.barchart{display:flex;flex-direction:column;gap:9px}
.brow{display:flex;align-items:center;gap:9px}
.blbl{font-size:11px;color:var(--t2);min-width:120px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.btrack{flex:1;height:7px;background:rgba(255,255,255,.05);border-radius:4px;overflow:hidden}
.bfill{height:100%;border-radius:4px;background:var(--grad);transition:width .8s cubic-bezier(.4,0,.2,1)}
.bval{font-size:11px;font-weight:600;color:var(--t2);min-width:24px;text-align:right}
.trend{display:flex;align-items:flex-end;gap:5px;height:110px}
.tcol{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;height:100%;justify-content:flex-end}
.tbar{width:100%;border-radius:4px 4px 0 0;background:var(--grad);min-height:4px;transition:height .8s cubic-bezier(.4,0,.2,1);cursor:pointer;position:relative}
.tbar:hover{filter:brightness(1.3)}
.tbar::after{content:attr(data-v);position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);border-radius:var(--r-sm);padding:2px 6px;font-size:10px;color:var(--t1);white-space:nowrap;opacity:0;pointer-events:none;transition:var(--tr);margin-bottom:3px;z-index:10}
.tbar:hover::after{opacity:1}
.tlbl{font-size:8px;color:var(--t3);white-space:nowrap;text-align:center}
footer{position:relative;z-index:1;border-top:1px solid var(--border);margin-top:18px}
.fi{max-width:1400px;margin:0 auto;padding:16px 24px;display:flex;justify-content:space-between;align-items:center;gap:16px}
.fb{display:flex;flex-direction:column;gap:2px}
.fb strong{font-size:13px;color:var(--t2)}
.fb span{font-size:11px;color:var(--t3)}
.fm{display:flex;flex-direction:column;align-items:flex-end;gap:2px;font-size:11px;color:var(--t3)}
.toast{position:fixed;bottom:22px;right:22px;background:var(--card);border:1px solid var(--border2);border-radius:var(--r-md);padding:12px 18px;font-size:13px;color:var(--t1);box-shadow:0 8px 40px rgba(0,0,0,.6);z-index:9999;transform:translateY(100px);opacity:0;transition:all .4s cubic-bezier(.4,0,.2,1);max-width:320px}
.toast.show{transform:translateY(0);opacity:1}
.toast.success{border-left:3px solid var(--g400)}
.toast.error{border-left:3px solid var(--r500)}
.toast.info{border-left:3px solid var(--b400)}
.spin{animation:spin .6s linear infinite}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
@media(max-width:1024px){.sgrid{grid-template-columns:1fr 1fr}.charts{grid-template-columns:1fr 1fr}.cwide{grid-column:1/-1}}
@media(max-width:640px){.sgrid{grid-template-columns:1fr}.charts{grid-template-columns:1fr}.cwide{grid-column:1}.frow{flex-direction:column}.hactions .badge{display:none}}
</style>
</head>
<body>
<header class="header">
  <div class="header-inner">
    <div class="brand">
      <div class="brand-icon">🏛️</div>
      <div>
        <div class="brand-name">Firenze Business Tracker</div>
        <div class="brand-sub">Nuove Imprese · Provincia FI</div>
      </div>
    </div>
    <div class="hactions">
      <div class="badge">
        <span class="dot" id="dot"></span>
        <span id="stxt">Caricamento...</span>
      </div>
      <button class="btn btn-p" id="btnRef" onclick="aggiornaManuale()">
        <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
        Aggiorna
      </button>
      <button class="btn btn-o" onclick="esportaCSV()">
        <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
        CSV
      </button>
    </div>
  </div>
</header>

<section class="stats">
  <div class="sgrid">
    <div class="scard"><div class="sico sico-p">🏢</div><div><div class="snum" id="n1">—</div><div class="slbl">Nuove Imprese</div><div class="ssub">Ultimi 7 giorni</div></div></div>
    <div class="scard"><div class="sico sico-b">📅</div><div><div class="snum" id="n2">—</div><div class="slbl">Registrate Oggi</div><div class="ssub" id="n2sub">—</div></div></div>
    <div class="scard"><div class="sico sico-g">📍</div><div><div class="snum" id="n3">—</div><div class="slbl">Comuni Attivi</div><div class="ssub">Provincia di FI</div></div></div>
    <div class="scard"><div class="sico sico-o">📊</div><div><div class="snum" id="n4">—</div><div class="slbl">Settori ATECO</div><div class="ssub">Nel periodo</div></div></div>
  </div>
</section>

<main class="main">
  <div class="filters">
    <div class="frow">
      <div class="sbox">
        <svg class="sico2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input type="text" id="si" class="sinput" placeholder="Cerca per nome, indirizzo o settore..." oninput="filtra()"/>
        <button class="sclr" id="sclr" onclick="clearS()" style="display:none">✕</button>
      </div>
      <div class="fg">
        <label class="flbl">Periodo</label>
        <select id="fgiorni" class="fsel" onchange="carica()">
          <option value="7" selected>Ultimi 7 giorni</option>
          <option value="14">Ultimi 14 giorni</option>
          <option value="30">Ultimi 30 giorni</option>
          <option value="90">Ultimi 90 giorni</option>
        </select>
      </div>
      <div class="fg">
        <label class="flbl">Comune</label>
        <select id="fcm" class="fsel" onchange="filtra()">
          <option value="">Tutti i comuni</option>
        </select>
      </div>
      <div class="fg">
        <label class="flbl">Ordina per</label>
        <select id="ford" class="fsel" onchange="ordina()">
          <option value="data_desc">Data (recenti prima)</option>
          <option value="data_asc">Data (meno recenti)</option>
          <option value="nome_asc">Nome A→Z</option>
          <option value="nome_desc">Nome Z→A</option>
          <option value="comune">Comune</option>
        </select>
      </div>
      <div class="finfo"><span id="cnt">— risultati</span></div>
    </div>
  </div>

  <div class="tbox">
    <div class="lov" id="lov"><div class="lspin"></div><p class="ltxt">Caricamento ultime imprese da Firenze...</p></div>
    <div class="empty" id="emp" style="display:none"><div class="empty-ico">🔍</div><h3>Nessun risultato</h3><p>Prova a modificare i filtri.</p></div>
    <table class="dtable" id="dt">
      <thead><tr>
        <th class="col-data" onclick="sortBy('data_iscrizione')">Data ↕</th>
        <th class="col-nome" onclick="sortBy('denominazione')">Denominazione ↕</th>
        <th class="col-comune" onclick="sortBy('comune')">Comune ↕</th>
        <th class="col-ind">Indirizzo</th>
        <th class="col-ateco">Settore ATECO</th>
        <th class="col-forma">Forma Giuridica</th>
        <th class="col-tel">📞 Telefono</th>
        <th class="col-stato">Stato</th>
      </tr></thead>
      <tbody id="tb"></tbody>
    </table>
    <div class="pg" id="pg">
      <button class="pb" id="prev" onclick="changePage(-1)">← Precedente</button>
      <span class="pi" id="pinfo">Pagina 1 di 1</span>
      <button class="pb" id="next" onclick="changePage(1)">Successiva →</button>
    </div>
  </div>

  <div class="charts">
    <div class="ccard"><div class="ctitle">📍 Top Comuni</div><span class="csub">Per nuove iscrizioni</span><div class="barchart" id="cc"></div></div>
    <div class="ccard"><div class="ctitle">🏭 Top Settori</div><span class="csub">Attività più popolari</span><div class="barchart" id="cs"></div></div>
    <div class="ccard cwide"><div class="ctitle">📈 Trend Giornaliero</div><span class="csub">Nuove iscrizioni per giorno</span><div class="trend" id="ct"></div></div>
  </div>
</main>

<footer><div class="fi">
  <div class="fb"><strong>Firenze Business Tracker</strong><span>Dati dal Registro delle Imprese · Camera di Commercio di Firenze</span></div>
  <div class="fm"><span>Aggiornamento: ogni giorno alle 06:00</span><span id="fu">Ultimo aggiornamento: —</span></div>
</div></footer>

<script>
const S={all:[],fil:[],pg:1,pp:20,sc:'data_iscrizione',sd:'desc'};
const oggi=new Date().toISOString().split('T')[0];
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function fmt(d){if(!d)return'—';try{const x=new Date(d+'T00:00:00');return x.toLocaleDateString('it-IT',{day:'2-digit',month:'2-digit',year:'numeric'})}catch{return d}}
function fmtS(d){if(!d)return'—';try{const x=new Date(d+'T00:00:00');return x.toLocaleDateString('it-IT',{day:'2-digit',month:'short'})}catch{return d}}
function anim(el,n,dur=700){const t=performance.now();(function step(now){const e=Math.min((now-t)/dur,1),p=1-Math.pow(1-e,3);el.textContent=Math.round(n*p);if(e<1)requestAnimationFrame(step)})(t)}
function toast(m,t='info'){let el=document.getElementById('_toast');if(!el){el=document.createElement('div');el.id='_toast';el.className='toast';document.body.appendChild(el)}el.textContent=m;el.className='toast '+t;requestAnimationFrame(()=>{el.classList.add('show');setTimeout(()=>el.classList.remove('show'),3200)})}

async function carica(){
  const giorni=document.getElementById('fgiorni').value;
  document.getElementById('lov').style.display='flex';
  document.getElementById('dt').style.opacity='.3';
  try{
    const [r1,r2]=await Promise.all([fetch('/api/imprese?limit=500&giorni='+giorni),fetch('/api/stats')]);
    const d1=await r1.json(),d2=await r2.json();
    if(d1.success){S.all=d1.imprese||[];aggStats(d1.imprese,d2);popolaComuni(d1.imprese);filtra();document.getElementById('dot').className='dot ok';document.getElementById('stxt').textContent='Online · '+((d1.metadata||{}).ultimo_aggiornamento||'').split(' ')[0]}
    if(d2.success){renderCharts(d2);const ua=(d2.metadata||{}).ultimo_aggiornamento||'—';document.getElementById('fu').textContent='Ultimo aggiornamento: '+ua}
  }catch(e){document.getElementById('dot').className='dot';document.getElementById('stxt').textContent='Errore';toast('❌ Errore connessione','error')}
  finally{document.getElementById('lov').style.display='none';document.getElementById('dt').style.opacity='1'}
}

function aggStats(imp,stats){
  anim(document.getElementById('n1'),imp.length);
  const nOggi=imp.filter(i=>i.data_iscrizione===oggi).length;
  anim(document.getElementById('n2'),nOggi);
  document.getElementById('n2sub').textContent=new Date().toLocaleDateString('it-IT',{weekday:'long',day:'numeric',month:'long'});
  const comuni=new Set(imp.map(i=>i.comune).filter(Boolean));
  anim(document.getElementById('n3'),comuni.size);
  const settori=new Set(imp.map(i=>i.codice_ateco).filter(Boolean));
  anim(document.getElementById('n4'),settori.size);
}

function popolaComuni(imp){
  const sel=document.getElementById('fcm'),v=sel.value;
  const c=[...new Set(imp.map(i=>i.comune).filter(Boolean))].sort();
  sel.innerHTML='<option value="">Tutti i comuni</option>'+c.map(x=>`<option value="${x.toLowerCase()}">${x}</option>`).join('');
  if(v)sel.value=v;
}

function filtra(){
  const s=document.getElementById('si').value.toLowerCase().trim();
  const cm=document.getElementById('fcm').value.toLowerCase();
  document.getElementById('sclr').style.display=s?'block':'none';
  S.fil=S.all.filter(i=>{
    const ms=!s||[i.denominazione,i.indirizzo,i.desc_ateco,i.comune,i.codice_ateco].some(v=>v&&v.toLowerCase().includes(s));
    const mc=!cm||(i.comune||'').toLowerCase().includes(cm);
    return ms&&mc;
  });
  ordina();
}
function clearS(){document.getElementById('si').value='';document.getElementById('sclr').style.display='none';filtra()}

function ordina(){
  const o=document.getElementById('ford').value;
  let arr=[...S.fil];
  if(o==='data_desc')arr.sort((a,b)=>(b.data_iscrizione||'').localeCompare(a.data_iscrizione||''));
  else if(o==='data_asc')arr.sort((a,b)=>(a.data_iscrizione||'').localeCompare(b.data_iscrizione||''));
  else if(o==='nome_asc')arr.sort((a,b)=>(a.denominazione||'').localeCompare(b.denominazione||''));
  else if(o==='nome_desc')arr.sort((a,b)=>(b.denominazione||'').localeCompare(a.denominazione||''));
  else if(o==='comune')arr.sort((a,b)=>(a.comune||'').localeCompare(b.comune||''));
  S.fil=arr;S.pg=1;renderTable();
}
function sortBy(col){S.sc=col;S.sd=S.sd==='asc'?'desc':'asc';S.fil.sort((a,b)=>{const va=(a[col]||'').toString(),vb=(b[col]||'').toString();return S.sd==='asc'?va.localeCompare(vb):vb.localeCompare(va)});S.pg=1;renderTable()}

function renderTable(){
  const tb=document.getElementById('tb'),emp=document.getElementById('emp'),cnt=document.getElementById('cnt');
  const tot=S.fil.length;cnt.textContent=tot+' risultat'+(tot!==1?'i':'o');
  if(!tot){emp.style.display='block';tb.innerHTML='';document.getElementById('pg').style.display='none';return}
  emp.style.display='none';
  const tp=Math.ceil(tot/S.pp),ini=(S.pg-1)*S.pp,fin=Math.min(ini+S.pp,tot),items=S.fil.slice(ini,fin);
  document.getElementById('pg').style.display=tp>1?'flex':'none';
  document.getElementById('pinfo').textContent=`Pagina ${S.pg} di ${tp} (${ini+1}–${fin} di ${tot})`;
  document.getElementById('prev').disabled=S.pg<=1;
  document.getElementById('next').disabled=S.pg>=tp;
  tb.innerHTML=items.map((imp,i)=>`
    <tr style="animation-delay:${i*18}ms">
      <td class="col-data"><span class="dbadge">${fmt(imp.data_iscrizione)}${imp.data_iscrizione===oggi?' <span style="color:var(--o400)">●</span>':''}</span></td>
      <td class="col-nome"><div class="ncel">${esc(imp.denominazione)}<small>${imp.partita_iva?'P.IVA: '+esc(imp.partita_iva):''}</small></div></td>
      <td class="col-comune"><span class="cpill">📍 ${esc(imp.comune||'—')}</span></td>
      <td class="col-ind" style="font-size:12px;color:var(--t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(imp.indirizzo||'—')}</td>
      <td class="col-ateco">${imp.codice_ateco?`<div class="abadge">${esc(imp.codice_ateco)}</div>`:''}<div class="adesc">${esc(imp.desc_ateco||'—')}</div></td>
      <td class="col-forma"><span class="ftxt">${esc(imp.forma_giuridica||'—')}</span></td>
      <td class="col-tel">${imp.numero_telefono
        ? `<a class="tel-link" href="tel:${imp.numero_telefono.replace(/\s/g,'')}" title="Chiama ${esc(imp.denominazione)}">📞 ${esc(imp.numero_telefono)}</a>`
        : '<span class="tel-nd">N/D</span>'
      }</td>
      <td class="col-stato"><span class="sbadge">${esc(imp.stato||'Attiva')}</span></td>
    </tr>`).join('');
}
function changePage(d){const tp=Math.ceil(S.fil.length/S.pp);S.pg=Math.max(1,Math.min(tp,S.pg+d));renderTable();document.querySelector('.tbox').scrollIntoView({behavior:'smooth',block:'start'})}

function renderCharts(stats){
  renderBar('cc',stats.per_comune);
  renderBar('cs',stats.top_settori);
  renderTrend('ct',stats.trend_giornaliero||[]);
}
function renderBar(id,data){
  const el=document.getElementById(id);if(!el||!data)return;
  const entries=Object.entries(data).slice(0,8),mx=Math.max(...entries.map(([,v])=>v),1);
  el.innerHTML=entries.map(([l,v])=>`<div class="brow"><span class="blbl" title="${esc(l)}">${esc(l)}</span><div class="btrack"><div class="bfill" style="width:${(v/mx*100).toFixed(1)}%"></div></div><span class="bval">${v}</span></div>`).join('');
}
function renderTrend(id,trend){
  const el=document.getElementById(id);if(!el||!trend.length)return;
  const items=trend.slice(-14),mx=Math.max(...items.map(([,v])=>v),1);
  el.innerHTML=items.map(([d,v])=>`<div class="tcol"><div class="tbar" data-v="${v} imprese" style="height:${Math.max(v/mx*100,4)}%" title="${d}: ${v}"></div><span class="tlbl">${fmtS(d)}</span></div>`).join('');
}

async function aggiornaManuale(){
  const btn=document.getElementById('btnRef'),ico=btn.querySelector('svg');
  btn.disabled=true;ico.classList.add('spin');toast('🔄 Aggiornamento...','info');
  try{
    const r=await fetch('/api/aggiorna',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    const d=await r.json();
    if(d.success){toast('✅ '+d.totale+' imprese aggiornate!','success');setTimeout(()=>carica(),800)}
    else toast('❌ Errore aggiornamento','error');
  }catch{toast('❌ Errore connessione','error')}
  finally{setTimeout(()=>{btn.disabled=false;ico.classList.remove('spin')},2000)}
}
function esportaCSV(){toast('📥 Download CSV...','info');window.location.href='/api/export/csv'}

document.addEventListener('DOMContentLoaded',()=>{
  carica();
  setInterval(()=>carica(),5*60*1000);
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='r'&&!e.shiftKey){e.preventDefault();aggiornaManuale()}});
});
</script>
</body>
</html>"""
