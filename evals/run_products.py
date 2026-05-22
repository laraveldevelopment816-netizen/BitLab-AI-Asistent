"""run_products.py — engine za pretragu proizvoda (kvalifikovani upiti, cold scenario).

Šalje svaki upit iz `evals/sets/products_cold.json` na `/api/chat` i mjeri:
- da li je Claude pozvao `search_products` (overview je WRONG_TOOL za kvalifikovan upit)
- da li je proslijedio očekivane filtere (`category_id`, `brand_id`, `max_price_km`)
- da li su vraćeni proizvodi relevantni (in-subtree + brand match + u cjenovnom opsegu)

Eval set ima dva tipa entry-ja, oba sa unifikovanim shape-om
`{query, history, expect, tags}`:

- pozitivni — `expect.tool="search_products"` + `category_id` + opciono
  `args_subset` (brand_id, max_price_km) + `min_results`. Engine provjerava
  routing, args, i da li su rezultati relevantni.
- negativni — `expect.tool=null` + `failure_reason`
  (brand_not_carried / price_unreachable / not_in_catalog / combo_impossible);
  sistem treba odbiti, ne lažno vratiti proizvode.

Verdict pipeline: `routing_verdict` → `args_verdict` (NOVO za products) →
`result_verdict` → `overall_verdict` (PASS / WARN / FAIL).

Pokretanje:
    python evals/run_products.py                           # cijeli set (21)
    python evals/run_products.py --limit 5 --label smoke   # smoke
    python evals/run_products.py --url https://staging.aiasistent.bitlab.rs
    python evals/run_products.py --label v2-prompt-fix     # A/B compare
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "categories.csv"
PRODUCTS_PATH = PROJECT_ROOT / "data" / "all-products.json"
DEFAULT_EVAL_PATH = PROJECT_ROOT / "evals" / "sets" / "products_cold.json"

DEFAULT_URL = "http://127.0.0.1:7778"
# Hard testing override: sa SEARCH_TOP_K_OVERRIDE=5287 + max_output_tokens=64000,
# Claude generiše markdown za 100+ proizvoda — može potrajati 5-10 minuta.
# VRATITI NA 180 prije produkcije / merge-a. Vidi pratnju u app/config.py
# (max_output_tokens) i .env (SEARCH_TOP_K_OVERRIDE).
DEFAULT_TIMEOUT_S = 900


# Markdown product line regex — identičan onome u `test_e2e_visual.py` i
# `run_e2e_html.py`. Ova lokalna kopija je svjesno duplikat — eval skripte
# se ne smiju zavisiti od jedne drugog.
PROD_RE = re.compile(
    r"!?\[?\]?\(?(?P<img>https?://\S+?)?\)?\s*"
    r"\*\*(?P<name>.+?)\*\*\s*—\s*(?P<price>[\d.,]+\s*KM)"
    r"(?:\s*—\s*(?P<avail>[^—\[]+?))?"
    r"(?:\s*—\s*\[[^\]]+\]\((?P<url>https?://\S+?)\))?\s*$"
)


# ─── Loader-i ────────────────────────────────────────────────────────────

def load_tree() -> tuple[dict[str, dict], dict[str, list[str]]]:
    """Vrati (by_id, children_of) iz `data/categories.csv` — samo aktivne cat-ove."""
    by_id: dict[str, dict] = {}
    children_of: dict[str, list[str]] = defaultdict(list)
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("status") != "1":
                continue
            cid = (r.get("id") or "").strip()
            pid = (r.get("parent_id") or "").strip()
            if not cid:
                continue
            by_id[cid] = r
            if pid and pid != "0":
                children_of[pid].append(cid)
    return by_id, dict(children_of)


def descendants(cat_id: str, children_of: dict[str, list[str]]) -> set[str]:
    """{cat_id + svi descendant-i}."""
    out = {cat_id}
    for c in children_of.get(cat_id, []):
        out |= descendants(c, children_of)
    return out


def load_product_lookup() -> dict:
    """Učitaj `data/all-products.json` i napravi više lookup-a + per-cat count.

    Vraća dict sa ključevima:
    - `by_name`: ime → categories_id (egzakt)
    - `by_name_lower`: ime.lower() → categories_id (case-insensitive)
    - `by_urlhash`: urlhash → categories_id (full slug, npr. "G45626-apple-iphone-13-pro-128gb")
    - `by_urlhash_prefix`: "G45626" → categories_id (stabilan kratki ID prije prvog "-")
    - `products_per_cat`: cat_id → broj proizvoda u toj kategoriji (za subtree count)

    URL hash je STABILAN identifier — ne mijenja se kad Claude reformuliše ime
    proizvoda u reply-ju. Name lookup ostaje kao fallback.
    """
    out: dict = {
        "by_name": {},
        "by_name_lower": {},
        "by_urlhash": {},
        "by_urlhash_prefix": {},
        "products_per_cat": defaultdict(int),
    }
    if not PRODUCTS_PATH.exists():
        out["products_per_cat"] = dict(out["products_per_cat"])
        return out
    data = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    for entry in data:
        if entry.get("type") != "table":
            continue
        for row in entry.get("data", []):
            name = (row.get("name") or "").strip()
            cid = (row.get("categories_id") or "").strip()
            urlhash = (row.get("urlhash") or "").strip()
            if not cid:
                continue
            out["products_per_cat"][cid] += 1
            if name:
                out["by_name"][name] = cid
                out["by_name_lower"][name.lower()] = cid
            if urlhash:
                out["by_urlhash"][urlhash] = cid
                prefix = urlhash.split("-", 1)[0]
                if prefix:
                    out["by_urlhash_prefix"][prefix] = cid
    out["products_per_cat"] = dict(out["products_per_cat"])
    return out


# ─── HTTP runtime ────────────────────────────────────────────────────────

def chat_call(client: httpx.Client, url: str, query: str) -> dict:
    """Pošalji query na /api/chat. Vrati raw response dict, ili dict sa
    "_error" ključem ako request padne."""
    try:
        r = client.post(
            f"{url}/api/chat",
            json={"message": query, "channel": "chat", "history": []},
            timeout=DEFAULT_TIMEOUT_S,
        )
        if r.status_code != 200:
            return {"_error": f"HTTP {r.status_code}: {r.text[:200]}"}
        return r.json()
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def parse_products(reply: str) -> list[dict]:
    """Izvuci product redove iz Markdown reply-ja."""
    out: list[dict] = []
    for raw in reply.split("\n"):
        line = raw.strip().lstrip("-0123456789. ").strip()
        if not line:
            continue
        m = PROD_RE.match(line)
        if not m:
            continue
        g = m.groupdict()
        out.append({
            "name": (g.get("name") or "").strip(),
            "price": (g.get("price") or "").strip(),
            "url": (g.get("url") or "").strip(),
        })
    return out


def extract_tool_calls(tool_calls: list[dict]) -> list[dict]:
    """Izvuci routing-relevantne pozive (`search_products` + `category_overview`)
    sa parsed argumentima. Svaki dict ima `tool` polje za razlikovanje."""
    out: list[dict] = []
    for tc in tool_calls or []:
        name = tc.get("tool_name")
        if name not in ("search_products", "category_overview"):
            continue
        try:
            args = json.loads(tc.get("input_json") or "{}")
        except json.JSONDecodeError:
            args = {}
        if name == "search_products":
            out.append({
                "tool": "search_products",
                "iteration": tc.get("iteration"),
                "query": args.get("query", ""),
                "category_id": args.get("category_id"),
                "brand_id": args.get("brand_id"),
                "top_k": args.get("top_k"),
                "max_price_km": args.get("max_price_km"),
                "latency_ms": tc.get("latency_ms"),
            })
        else:  # category_overview
            out.append({
                "tool": "category_overview",
                "iteration": tc.get("iteration"),
                "category_id": args.get("cat_id"),
                "latency_ms": tc.get("latency_ms"),
            })
    return out


def _url_to_slug(url: str) -> str:
    """Iz product URL-a (https://webshop.bitlab.rs/G61925-foo.html) izvuci slug
    bez ekstenzije ("G61925-foo"). URL-decode-uje sve (npr. %20 → razmak),
    pošto urlhash u bazi može imati doslovne razmake. Vraća prazno ako URL
    nije parse-abilan."""
    if not url:
        return ""
    last = url.rsplit("/", 1)[-1]
    if last.endswith(".html"):
        last = last[:-5]
    last = unquote(last)  # %20 → " ", %C5%A1 → "š", itd.
    return last.strip()


def match_product_cat(name: str, url: str, lookup: dict) -> tuple[str | None, str]:
    """Best-effort mapping proizvoda iz reply-ja na categories_id.

    Probava redom: URL hash (stabilan), URL prefix (G-kod), egzakt ime,
    lower-case ime, ime kao prefix DB imena (pokriva slučaj kad DB ima sufiks
    model-koda tipa ",MG684J/A"). Vraća (cat_id, način_pogotka) — `način`
    pomaže debugu (vidiš kako je matched).
    """
    # 1) URL — stabilan identifier (ne ovisi o reformulaciji imena)
    slug = _url_to_slug(url)
    if slug:
        cid = lookup["by_urlhash"].get(slug)
        if cid:
            return cid, "urlhash"
        prefix = slug.split("-", 1)[0]
        if prefix:
            cid = lookup["by_urlhash_prefix"].get(prefix)
            if cid:
                return cid, "urlhash_prefix"

    # 2) Ime — egzakt
    if name:
        cid = lookup["by_name"].get(name)
        if cid:
            return cid, "name"
        n_low = name.lower()
        cid = lookup["by_name_lower"].get(n_low)
        if cid:
            return cid, "name_lower"
        # 3) Prefix substring — npr. reply "Apple iPhone 17 256GB White eSim"
        #    a DB ima "Apple iPhone 17 256GB White eSim,MG684J/A"
        for k, v in lookup["by_name_lower"].items():
            if k.startswith(n_low) or n_low.startswith(k):
                return v, "name_prefix"

    return None, "miss"


# ─── Per-query analiza ──────────────────────────────────────────────────

def routing_verdict(
    routed_tool: str | None,
    routed_cat: str | None,
    expected_tool: str | None,
    expected_cat: str,
    expected_subtree: set[str],
) -> str:
    """Klasifikacija Claude-ovog routing-a za products engine.

    Pozitivni (expected_tool="search_products"):
    - EXACT_PARENT: search_products sa tačno očekivanim cat_id.
    - DESCENDANT: search_products sa cat_id iz očekivanog subtree-a.
    - OUT: search_products sa cat_id van subtree-a, ili bez cat-a.
    - WRONG_TOOL: Claude pozvao category_overview umjesto search_products
      (overview za kvalifikovan upit je promašaj).
    - NULL: nijedan routing tool pozvan.

    Negativni (expected_tool=None):
    - NEG_PASS: nijedan routing tool pozvan (sistem odbio).
    - NEG_REGRESSION: Claude lažno pozvao search/overview sa nepostojećom kombinacijom.
    """
    if expected_tool is None:
        if routed_tool is None:
            return "NEG_PASS"
        return "NEG_REGRESSION"

    if routed_tool is None:
        return "NULL"
    if routed_tool != expected_tool:
        return "WRONG_TOOL"
    # search_products + nije proslijedio cat
    if routed_cat is None:
        return "OUT"
    if routed_cat == expected_cat:
        return "EXACT_PARENT"
    if routed_cat in expected_subtree:
        return "DESCENDANT"
    return "OUT"


def args_verdict(routed_args: dict, expected_args: dict | None) -> str:
    """Provjera da li je Claude prosledio očekivane filtere (brand_id, max_price_km).

    - ARGS_NA: entry ne specifikuje `expect.args_subset` — ne mjeri se.
    - ARGS_PASS: svi očekivani filteri se poklapaju.
    - ARGS_PARTIAL: barem jedan se poklapa, ali ne svi.
    - ARGS_MISSING: nijedan očekivani filter nije proslijeđen.
    """
    if not expected_args:
        return "ARGS_NA"
    matched = 0
    total = 0
    for k, v in expected_args.items():
        total += 1
        actual = routed_args.get(k)
        if actual is None:
            continue
        # poređenje kao string da brand_id "11" matchuje i int 11
        if str(actual) == str(v):
            matched += 1
    if matched == total:
        return "ARGS_PASS"
    if matched > 0:
        return "ARGS_PARTIAL"
    return "ARGS_MISSING"


def parse_price_km(price_str: str) -> float | None:
    """'1.299,90 KM' → 1299.90. BCS format (tačka kao thousands, zarez kao decimal)."""
    if not price_str:
        return None
    s = price_str.replace("KM", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def result_verdict(
    n_returned: int,
    n_in_subtree: int,
    n_in_price_range: int | None,
    min_results: int,
    routed_tool: str | None,
) -> str:
    """Da li je end-user dobio relevantne proizvode.

    - NA: nije pozvao search (overview / nijedan) — mjeri se kroz routing_verdict.
    - FAIL: 0 vraćenih, ili 0 u očekivanoj porodici, ili ispod min_results.
    - WARN: ima u porodici ali ispod min_results, ili price filter nije ispoštovan.
    - PASS: ≥min_results u porodici (+ u cjenovnom opsegu ako je filter specifikovan).
    """
    if routed_tool != "search_products":
        return "NA"
    if n_returned == 0:
        return "FAIL"
    if n_in_subtree == 0:
        return "FAIL"
    if n_in_subtree < min_results:
        return "WARN"
    # ako je price filter specifikovan, sve relevantne mora biti i u opsegu
    if n_in_price_range is not None and n_in_price_range < min_results:
        return "WARN"
    return "PASS"


def overall_verdict(routing: str, args: str, result: str) -> str:
    """Sjedinjeni per-upit verdict: PASS / WARN / FAIL.

    - Negativni: NEG_PASS → PASS, NEG_REGRESSION → FAIL.
    - Pozitivni: routing mora dobro, args bar parcijalno, result PASS/WARN.
    - NULL/OUT/WRONG_TOOL → FAIL (sistem promašio route).
    """
    if routing == "NEG_PASS":
        return "PASS"
    if routing in ("NEG_REGRESSION", "NULL", "OUT", "WRONG_TOOL"):
        return "FAIL"
    # routing OK (EXACT_PARENT / DESCENDANT)
    if args == "ARGS_MISSING":
        return "FAIL"
    if args == "ARGS_PARTIAL":
        return "WARN" if result in ("PASS", "WARN") else "FAIL"
    # args OK (ARGS_PASS) ili NA → result odlučuje
    if result == "NA":
        return "PASS"
    return result if result in ("PASS", "WARN", "FAIL") else "FAIL"


# ─── HTML ───────────────────────────────────────────────────────────────

HTML = r"""<!doctype html>
<html lang="bs">
<head>
<meta charset="utf-8">
<title>Rutiranje po kategorijama — ponašanje uživo</title>
<style>
  :root {
    --bg:#0f1419; --panel:#161c24; --border:#232b36; --text:#d7dbe0;
    --muted:#8a94a3; --accent:#4cc2ff;
    --ok:#6ee7a0; --fail:#ff6b8a; --na:#8a94a3; --warn:#ffd34a;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:-apple-system,"Segoe UI",Inter,system-ui,sans-serif;
    font-size:13px;line-height:1.45}
  header{padding:16px 24px;border-bottom:1px solid var(--border);position:relative}
  header .model-badge{position:absolute;top:14px;right:24px;background:rgba(76,194,255,0.10);
    border:1px solid rgba(76,194,255,0.35);color:var(--accent);padding:6px 12px;
    border-radius:14px;font-size:12px;font-weight:500;font-family:ui-monospace,monospace}
  header .model-badge .lab{color:var(--muted);font-size:10px;text-transform:uppercase;
    letter-spacing:0.06em;margin-right:6px;font-weight:600;font-family:inherit}
  h1{margin:0 0 4px;font-size:18px;font-weight:600}
  .sub{color:var(--muted);font-size:12px}
  main{padding:14px 24px 60px;max-width:1400px}
  h2{font-size:13px;color:var(--muted);text-transform:uppercase;
    letter-spacing:0.07em;margin:18px 0 8px;font-weight:600}
  .verdict-banner{padding:14px 18px;border-radius:8px;font-size:15px;
    font-weight:600;margin:12px 0 18px}
  .verdict-banner.fail{background:rgba(255,107,138,0.10);
    border:1px solid rgba(255,107,138,0.4);color:var(--fail)}
  .verdict-banner.pass{background:rgba(110,231,160,0.10);
    border:1px solid rgba(110,231,160,0.4);color:var(--ok)}
  .verdict-banner.warn{background:rgba(255,211,74,0.10);
    border:1px solid rgba(255,211,74,0.4);color:var(--warn)}
  .verdict-banner small{display:block;font-size:12px;color:var(--muted);
    font-weight:400;margin-top:3px}
  .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
    gap:8px;margin:8px 0 18px}
  .stat{background:var(--panel);border:1px solid var(--border);
    border-radius:6px;padding:9px 12px}
  .stat .v{font-size:22px;font-weight:600;color:var(--accent)}
  .stat .l{color:var(--muted);font-size:11px;text-transform:uppercase;
    letter-spacing:0.05em}
  .stat.fail .v{color:var(--fail)}
  .stat.pass .v{color:var(--ok)}
  .stat.warn .v{color:var(--warn)}
  table.leaderboard{width:100%;border-collapse:collapse;
    background:var(--panel);border:1px solid var(--border);border-radius:6px;
    overflow:hidden;margin-bottom:18px}
  table.leaderboard th,table.leaderboard td{padding:7px 10px;
    border-bottom:1px solid var(--border);text-align:left;font-size:12px;vertical-align:top}
  table.leaderboard th{background:rgba(255,255,255,0.02);color:var(--muted);
    text-transform:uppercase;letter-spacing:0.05em;font-weight:600;font-size:11px}
  table.leaderboard tr:last-child td{border-bottom:none}
  table.leaderboard td.id{color:var(--muted);font-family:ui-monospace,monospace}
  table.leaderboard td.num,table.leaderboard th.num{text-align:left;font-family:ui-monospace,monospace}
  table.leaderboard td.q{font-weight:500}
  .badge{display:inline-block;padding:1px 7px;border-radius:8px;
    font-size:10px;font-weight:600;letter-spacing:0.04em;font-family:ui-monospace,monospace}
  .badge.pass{background:rgba(110,231,160,0.18);color:var(--ok)}
  .badge.warn{background:rgba(255,211,74,0.18);color:var(--warn)}
  .badge.fail{background:rgba(255,107,138,0.18);color:var(--fail)}
  .badge.na{background:rgba(255,255,255,0.04);color:var(--na)}
  .badge.exact_parent{background:rgba(110,231,160,0.18);color:var(--ok)}
  .badge.descendant{background:rgba(110,231,160,0.18);color:var(--ok)}
  .badge.null{background:rgba(76,194,255,0.18);color:var(--accent)}
  .badge.out{background:rgba(255,211,74,0.18);color:var(--warn)}
  .badge.overview_pass{background:rgba(110,231,160,0.18);color:var(--ok)}
  .badge.overview_wrong{background:rgba(255,107,138,0.18);color:var(--fail)}
  .badge.wrong_tool{background:rgba(255,107,138,0.18);color:var(--fail)}
  .badge.neg_pass{background:rgba(110,231,160,0.18);color:var(--ok)}
  .badge.neg_regression{background:rgba(255,107,138,0.18);color:var(--fail)}
  .badge.args_pass{background:rgba(110,231,160,0.18);color:var(--ok)}
  .badge.args_partial{background:rgba(255,211,74,0.18);color:var(--warn)}
  .badge.args_missing{background:rgba(255,107,138,0.18);color:var(--fail)}
  .badge.args_na{background:rgba(255,255,255,0.04);color:var(--na)}
  details.qdetail{background:var(--panel);border:1px solid var(--border);
    border-radius:6px;padding:8px 14px;margin-bottom:8px}
  details.qdetail summary{cursor:pointer;font-weight:500;list-style:none;outline:none}
  details.qdetail summary::-webkit-details-marker{display:none}
  details.qdetail summary::before{content:"▶ ";color:var(--muted);font-size:9px}
  details.qdetail[open] summary::before{content:"▼ "}
  details.qdetail .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}
  details.qdetail .section{background:rgba(0,0,0,0.15);border-radius:4px;padding:8px 10px;font-size:12px}
  details.qdetail .section h3{margin:0 0 6px;font-size:11px;color:var(--muted);
    text-transform:uppercase;letter-spacing:0.05em;font-weight:600}
  details.qdetail .toolcall{font-family:ui-monospace,monospace;font-size:11px;color:var(--text);
    background:rgba(0,0,0,0.25);padding:4px 6px;border-radius:3px;margin:2px 0}
  details.qdetail ul.products{margin:4px 0;padding-left:18px}
  details.qdetail ul.products li{margin:2px 0}
  details.qdetail ul.products li.in-subtree{color:var(--ok)}
  details.qdetail ul.products li.out-subtree{color:var(--warn)}
  details.qdetail .reply{font-family:ui-monospace,monospace;font-size:11px;color:var(--muted);
    white-space:pre-wrap;max-height:200px;overflow:auto;background:rgba(0,0,0,0.25);
    padding:6px 8px;border-radius:3px}
  details.qdetail .err{color:var(--fail);font-family:ui-monospace,monospace;font-size:12px}
</style>
</head>
<body>
<header>
  <h1>Rutiranje po kategorijama — ponašanje uživo (/api/chat)</h1>
  <div class="sub" id="meta"></div>
  <div class="model-badge" id="model-badge"><span class="lab">model</span><span id="model-name">—</span></div>
</header>
<main>

<div id="verdict"></div>

<h2>Pregled</h2>
<div class="stats" id="stats"></div>

<h2>Tabela po upitima</h2>
<table class="leaderboard">
  <thead><tr>
    <th>Upit (očekivana kategorija)</th>
    <th>Rutovano na (kategorija)</th>
    <th>Kako je rutovao</th>
    <th>Filteri</th>
    <th class="num">Vraćeno</th>
    <th class="num">U porodici</th>
    <th class="num">U cijeni</th>
    <th>Ishod</th>
    <th class="num">Iter</th>
    <th class="num">Trajanje</th>
  </tr></thead>
  <tbody id="leaderboard"></tbody>
</table>

<h2>Detalji po upitu (kliknite red da otvorite)</h2>
<div id="details"></div>

</main>
<script>
const DATA = __DATA_PLACEHOLDER__;

document.getElementById("meta").textContent =
  `Pokrenuto ${DATA.meta.run_at}  ·  Server: ${DATA.meta.url}  ·  Tag: ${DATA.meta.label || "—"}  ` +
  `·  Upita: ${DATA.meta.n_queries}  ·  Ukupno trajalo: ${DATA.meta.wall_s.toFixed(1)}s`;

// Model badge gore desno — skrati puno ime modela za prijatniji prikaz
// (npr. "claude-sonnet-4-6" → "Sonnet 4.6", "claude-haiku-4-5-20251001" → "Haiku 4.5")
function shortModelName(m) {
  if (!m || m === "?") return "—";
  const mat = /claude-([a-z]+)-(\d+)-(\d+)/i.exec(m);
  if (mat) {
    const family = mat[1].charAt(0).toUpperCase() + mat[1].slice(1);
    return `${family} ${mat[2]}.${mat[3]}`;
  }
  return m;
}
const modelTxt = shortModelName(DATA.meta.chat_model);
const effortTxt = (DATA.meta.chat_model_effort && DATA.meta.chat_model_effort !== "?")
  ? DATA.meta.chat_model_effort : "";
const backendTxt = (DATA.meta.llm_backend && DATA.meta.llm_backend !== "?")
  ? DATA.meta.llm_backend : "";
const badgeParts = [modelTxt];
if (effortTxt) badgeParts.push(effortTxt);
if (backendTxt) badgeParts.push("via " + backendTxt);
document.getElementById("model-name").textContent = badgeParts.join(" · ");

// Prevod tehničkih enum-a u prirodan jezik (crnogorski ijekavica)
const ROUTING_LABEL = {
  "EXACT_PARENT": "pretraga — tačna kategorija",
  "DESCENDANT": "pretraga — podkategorija iz iste porodice",
  "NULL": "bez kategorijskog filtera",
  "OUT": "pretraga — van porodice",
  "WRONG_TOOL": "pogrešan alat (pregled porodice umjesto pretrage)",
  "NEG_PASS": "negativan — sistem pravilno odbio",
  "NEG_REGRESSION": "negativan — regresija (lažno rutirao)",
  "NA": "—",
};
const ARGS_LABEL = {
  "ARGS_PASS": "filteri tačni",
  "ARGS_PARTIAL": "filteri parcijalni",
  "ARGS_MISSING": "filteri nedostaju",
  "ARGS_NA": "—",
};
const RESULT_LABEL = {
  "PASS": "prošlo",
  "WARN": "upozorenje",
  "FAIL": "promašaj",
  "NA": "ne primjenjuje se",
};
function routingLabel(v) { return ROUTING_LABEL[v] || v; }
function argsLabel(v) { return ARGS_LABEL[v] || v; }
function resultLabel(v) { return RESULT_LABEL[v] || v; }

// Glavni baner — koristi ukupni ishod (routing + args + result) sjedinjen u jedan signal
const v = DATA.summary;
let vClass, vTitle, vBody;
if (v.fail_count === 0 && v.warn_count === 0) {
  vClass = "pass";
  vTitle = "✓ Sve prošlo — Claude pravilno rutira proizvode";
  vBody = `${v.pass_count} prošlo od ${v.total} upita.`;
} else if (v.fail_count > 0) {
  vClass = "fail";
  vTitle = `✗ ${v.fail_count} upita promašeno`;
  vBody = `${v.pass_count} prošlo, ${v.warn_count} upozorenje, ${v.fail_count} promašaj od ${v.total} upita. ` +
    `Razrada: pretraga ${v.search_pass_count||0}/${v.search_warn_count||0}/${v.search_fail_count||0} (P/W/F); ` +
    `filteri ${v.args_pass_count||0}/${v.args_partial_count||0}/${v.args_missing_count||0} (tačni/parcijalni/nedostaju); ` +
    `negativni ${v.neg_pass_count||0}/${v.neg_regression_count||0} (odbijen/regresija); ` +
    `pogrešan alat ${v.wrong_tool_count||0}.`;
} else {
  vClass = "warn";
  vTitle = `⚠ ${v.warn_count} upita sa upozorenjem — slabi rezultati`;
  vBody = `${v.pass_count} prošlo, ${v.warn_count} upozorenje od ${v.total} upita.`;
}
document.getElementById("verdict").innerHTML =
  `<div class="verdict-banner ${vClass}">${vTitle}<small>${vBody}</small></div>`;

// Pregled — sažete kartice po metrikama (products engine)
document.getElementById("stats").innerHTML = [
  ["", `${v.total}`, "Ukupno upita"],
  ["pass", `${v.pass_count}`, "Ukupno prošlo"],
  ["warn", `${v.warn_count}`, "Ukupno upozorenje"],
  ["fail", `${v.fail_count}`, "Ukupno promašaj"],
  ["pass", `${v.args_pass_count || 0}`, "Filteri tačni"],
  ["warn", `${v.args_partial_count || 0}`, "Filteri parcijalni"],
  ["fail", `${v.args_missing_count || 0}`, "Filteri nedostaju"],
  ["", `${v.search_pass_count || 0}`, "Pretraga — prošlo"],
  ["", `${v.search_fail_count || 0}`, "Pretraga — promašaj"],
  ["pass", `${v.neg_pass_count || 0}`, "Negativni — pravilno odbijen"],
  ["fail", `${v.neg_regression_count || 0}`, "Negativni — regresija"],
  ["fail", `${v.wrong_tool_count || 0}`, "Pogrešan alat"],
  ["", `${v.total_returned}`, "Ukupno vraćeno proizvoda"],
].map(([cls, val, lab]) =>
  `<div class="stat ${cls}"><div class="v">${val}</div><div class="l">${lab}</div></div>`
).join("");

// Helper — ime kategorije za dati cat_id (iz DATA.cat_names)
function catName(cid) {
  if (cid === null || cid === undefined || cid === "") return null;
  return (DATA.cat_names || {})[String(cid)] || null;
}
function routedDisplay(cid) {
  if (cid === null || cid === undefined || cid === "") return "—";
  const nm = catName(cid);
  return nm ? `${cid} <span style="color:var(--muted)">(${escapeHtml(nm)})</span>` : `${cid}`;
}

// Leaderboard
document.getElementById("leaderboard").innerHTML = DATA.rows.map(r => {
  const rt = r.routing_verdict.toLowerCase();
  const av = (r.args_verdict || "ARGS_NA").toLowerCase();
  const ovr = (r.overall_verdict || r.result_verdict).toLowerCase();
  const parentName = catName(r.expected_cat_id);
  const parentTxt = parentName ? `očekivana kat. ${r.expected_cat_id} — ${parentName}` : `očekivana kat. ${r.expected_cat_id}`;
  const inPriceTxt = (r.n_in_price_range === null || r.n_in_price_range === undefined) ? "—" : r.n_in_price_range;
  return `<tr>
    <td class="q">${escapeHtml(r.query)}<br><span style="color:var(--muted);font-size:10px">${escapeHtml(parentTxt)}</span></td>
    <td class="id">${routedDisplay(r.routed_cat_id)}</td>
    <td><span class="badge ${rt}">${routingLabel(r.routing_verdict)}</span></td>
    <td><span class="badge ${av}">${argsLabel(r.args_verdict || "ARGS_NA")}</span></td>
    <td class="num">${r.n_returned}</td>
    <td class="num">${r.n_in_subtree}</td>
    <td class="num">${inPriceTxt}</td>
    <td><span class="badge ${ovr}">${resultLabel(r.overall_verdict || r.result_verdict)}</span></td>
    <td class="num">${r.iterations}</td>
    <td class="num">${r.latency_ms}ms</td>
  </tr>`;
}).join("");

// Per-query details
document.getElementById("details").innerHTML = DATA.rows.map(r => {
  if (r.error) {
    return `<details class="qdetail"><summary>${escapeHtml(r.query)} — <span class="err">${escapeHtml(r.error)}</span></summary></details>`;
  }
  const calls = r.tool_calls || [];
  const callsHtml = calls.length
    ? calls.map(c => {
        const catTxt = c.category_id ?? "—";
        const catNm = catName(c.category_id);
        const catDisp = catNm ? `${catTxt} (${escapeHtml(catNm)})` : catTxt;
        if (c.tool === "category_overview") {
          return `<div class="toolcall">iteracija ${c.iteration} · <b>pregled porodice</b> · ` +
            `roditelj=${catDisp} · (${c.latency_ms ?? "?"}ms)</div>`;
        }
        return `<div class="toolcall">iteracija ${c.iteration} · <b>pretraga proizvoda</b> "${escapeHtml(c.query || "")}" · ` +
          `kategorija=${catDisp} · brend=${c.brand_id ?? "—"} · ` +
          `top_k=${c.top_k ?? "podrazumijevani"} · max_cijena=${c.max_price_km ?? "—"} · ` +
          `(${c.latency_ms ?? "?"}ms)</div>`;
      }).join("")
    : `<div class="toolcall" style="color:var(--muted)">— Claude nije pozvao alat za rutiranje —</div>`;
  // Prevod debug-flag-a (kako smo mapirali proizvod iz Claude-ovog odgovora
  // na red u bazi) u ljudski jezik.
  const VIA_LABEL = {
    "urlhash": "prepoznat preko URL adrese",
    "urlhash_prefix": "prepoznat preko G-koda iz URL-a",
    "name": "prepoznat po imenu (egzaktno)",
    "name_lower": "prepoznat po imenu",
    "name_prefix": "prepoznat po dijelu imena",
  };
  const productsHtml = r.products.length
    ? `<ul class="products">${r.products.map(p => {
        const viaTxt = p.match_via && VIA_LABEL[p.match_via] ? ` · ${VIA_LABEL[p.match_via]}` : "";
        const inTxt = p.in_subtree
          ? " ✓ pogodak u porodici"
          : (p.cat_id ? ` ✗ van porodice (kategorija ${p.cat_id})` : " ✗ nije pronađen u bazi proizvoda");
        return `<li class="${p.in_subtree ? "in-subtree" : "out-subtree"}">` +
        `${escapeHtml(p.name)} <span style="color:var(--muted);font-size:10px">` +
        `${inTxt}${viaTxt}</span></li>`;
      }).join("")}</ul>`
    : `<div style="color:var(--muted);font-size:11px">— Nijedan proizvod nije izvučen iz odgovora —</div>`;
  const parentNm = catName(r.expected_cat_id);
  const famTxt = parentNm ? `porodica ${parentNm}` : "porodica";
  const sumVerdict = r.overall_verdict || r.result_verdict;
  return `<details class="qdetail">
    <summary>${escapeHtml(r.query)} — <span class="badge ${sumVerdict.toLowerCase()}">${resultLabel(sumVerdict)}</span> ${r.n_in_subtree} pogodaka od ${r.n_returned} vraćenih proizvoda (${famTxt} ima ${r.subtree_total} proizvoda)</summary>
    <div class="grid">
      <div class="section">
        <h3>Šta je Claude pozvao</h3>
        ${callsHtml}
      </div>
      <div class="section">
        <h3>Vraćeni proizvodi (mapiranje na kategoriju)</h3>
        ${productsHtml}
      </div>
    </div>
    <div class="section" style="margin-top:10px">
      <h3>Sirov odgovor Claude-a</h3>
      <div class="reply">${escapeHtml(r.reply)}</div>
    </div>
  </details>`;
}).join("");

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
</script>
</body>
</html>
"""


def render(data: dict) -> str:
    return HTML.replace("__DATA_PLACEHOLDER__", json.dumps(data, ensure_ascii=False))


# ─── Main flow ──────────────────────────────────────────────────────────

def default_out_path(label: str | None) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{label}" if label else ""
    fname = f"products{suffix}-{ts}.html"
    runs_dir = PROJECT_ROOT / "evals" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir / fname


def main() -> int:
    p = argparse.ArgumentParser(description="Engine za pretragu proizvoda (kvalifikovani upiti)")
    p.add_argument("--url", default=DEFAULT_URL,
                   help=f"Base URL servera (default: {DEFAULT_URL})")
    p.add_argument("--out", default=None,
                   help="Output HTML path (default: evals/runs/products[-label]-{TS}.html)")
    p.add_argument("--queries", default=str(DEFAULT_EVAL_PATH),
                   help=f"Path do query-set JSON-a (default: {DEFAULT_EVAL_PATH})")
    p.add_argument("--label", default="",
                   help="Label (npr. v1, v2-prompt-tweak) — ulazi u filename + meta")
    p.add_argument("--limit", type=int, default=None,
                   help="Pokreni samo prvih N upita (quick smoke test)")
    args = p.parse_args()

    eval_path = Path(args.queries)
    if not eval_path.exists():
        print(f"GREŠKA: {eval_path} ne postoji.", file=sys.stderr)
        return 1
    queries: list[dict] = json.loads(eval_path.read_text(encoding="utf-8"))
    if args.limit:
        queries = queries[:args.limit]

    by_id, children_of = load_tree()
    product_lookup = load_product_lookup()
    products_per_cat = product_lookup["products_per_cat"]

    # Healthz prije nego pucamo seriju — i izvuci stvarni model + effort + backend
    # koje server koristi za /api/chat (zavisi od LLM_BACKEND).
    chat_model = "?"
    chat_effort = "?"
    llm_backend = "?"
    try:
        with httpx.Client() as client:
            r = client.get(f"{args.url}/healthz", timeout=10)
            hz = r.json()
            chat_model = hz.get("chat_model", "?")
            chat_effort = hz.get("chat_model_effort", "?")
            llm_backend = hz.get("llm_backend", "?")
            print(f"provjera servera: {r.status_code}  model: {chat_model}  "
                  f"napor: {chat_effort}  backend: {llm_backend}")
    except Exception as e:
        print(f"GREŠKA: server nedostupan na {args.url}: {e}", file=sys.stderr)
        return 1

    print(f"Pokrećem {len(queries)} upita ka {args.url} …")
    rows: list[dict] = []
    t_wall = time.monotonic()

    with httpx.Client() as client:
        for i, q in enumerate(queries, 1):
            query = q["query"]
            # Novi unifikovani entry shape (evals/sets/products_cold.json):
            #   { "query", "history", "expect": {tool, category_id, args_subset?,
            #      min_results?, failure_reason?}, "tags" }
            expect = q.get("expect") or {}
            expected_cat = (expect.get("category_id") or "") if expect.get("category_id") else ""
            expected_tool = expect.get("tool")
            expected_args = expect.get("args_subset") or None
            expected_min_results = int(expect.get("min_results") or 1)
            failure_reason = expect.get("failure_reason")
            tags = q.get("tags") or []
            label = f"{query} ({', '.join(tags)})" if tags else query
            subtree = descendants(expected_cat, children_of) if expected_cat else set()
            subtree_product_count = sum(products_per_cat.get(c, 0) for c in subtree)

            print(f"  [{i:3}/{len(queries)}] {query!r:<40}", end=" ", flush=True)
            t0 = time.monotonic()
            resp = chat_call(client, args.url, query)
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            if "_error" in resp:
                print(f"GREŠKA ({elapsed_ms}ms): {resp['_error']}")
                rows.append({
                    "query": query, "expected_cat_id": expected_cat,
                    "expected_tool": expected_tool,
                    "expected_args": expected_args,
                    "expected_min_results": expected_min_results,
                    "failure_reason": failure_reason,
                    "tags": tags,
                    "category_label": label,
                    "error": resp["_error"],
                    "routed_tool": None,
                    "routed_cat_id": None, "routing_verdict": "NA",
                    "args_verdict": "ARGS_NA",
                    "n_returned": 0, "n_in_subtree": 0,
                    "n_in_price_range": None,
                    "subtree_total": subtree_product_count,
                    "result_verdict": "FAIL", "overall_verdict": "FAIL",
                    "iterations": 0,
                    "latency_ms": elapsed_ms, "products": [],
                    "tool_calls": [], "reply": "",
                })
                continue

            reply = resp.get("reply", "")
            tool_calls_raw = resp.get("tool_calls", [])
            iterations = resp.get("iterations", 0)
            tool_calls_parsed = extract_tool_calls(tool_calls_raw)

            # Routing — uzmi prvi routing-relevantan poziv.
            if tool_calls_parsed:
                routed_tool = tool_calls_parsed[0]["tool"]
                routed_cat = tool_calls_parsed[0]["category_id"]
                routed_args = {
                    k: tool_calls_parsed[0].get(k)
                    for k in ("brand_id", "max_price_km", "top_k")
                    if tool_calls_parsed[0].get(k) is not None
                }
            else:
                routed_tool = None
                routed_cat = None
                routed_args = {}
            r_verdict = routing_verdict(routed_tool, routed_cat, expected_tool, expected_cat, subtree)
            a_verdict = args_verdict(routed_args, expected_args)

            products_raw = parse_products(reply)
            products: list[dict] = []
            n_in_subtree = 0
            n_in_price_range = 0
            max_price_km = (expected_args or {}).get("max_price_km")
            for p_ in products_raw:
                cid, via = match_product_cat(p_["name"], p_.get("url", ""), product_lookup)
                in_st = cid in subtree if cid else False
                if in_st:
                    n_in_subtree += 1
                price = parse_price_km(p_.get("price", ""))
                in_price = (max_price_km is not None and price is not None and price <= float(max_price_km))
                if in_price:
                    n_in_price_range += 1
                products.append({
                    "name": p_["name"],
                    "cat_id": cid,
                    "in_subtree": in_st,
                    "price_km": price,
                    "in_price_range": in_price,
                    "match_via": via,
                })

            n_in_price_range_val: int | None = n_in_price_range if max_price_km is not None else None
            res_verdict = result_verdict(
                len(products), n_in_subtree, n_in_price_range_val,
                expected_min_results, routed_tool,
            )
            ovr_verdict = overall_verdict(r_verdict, a_verdict, res_verdict)
            # Stdout — prirodan jezik (crnogorski ijekavica)
            verdict_label = {"PASS": "prošlo", "WARN": "upozorenje", "FAIL": "promašaj"}.get(ovr_verdict, ovr_verdict)
            routing_label = {
                "EXACT_PARENT": "tačna kategorija",
                "DESCENDANT": "podkategorija",
                "NULL": "bez filtera",
                "OUT": "van porodice",
                "WRONG_TOOL": "pogrešan alat",
                "NEG_PASS": "negativan — pravilno odbijen",
                "NEG_REGRESSION": "negativan — regresija",
                "NA": "—",
            }.get(r_verdict, r_verdict)
            args_label = {
                "ARGS_PASS": "filteri tačni",
                "ARGS_PARTIAL": "filteri parcijalni",
                "ARGS_MISSING": "filteri nedostaju",
                "ARGS_NA": "—",
            }.get(a_verdict, a_verdict)
            print(f"{verdict_label:<10} ruta='{routing_label}' filteri='{args_label}' "
                  f"vraćeno={len(products)} u_porodici={n_in_subtree} "
                  f"u_cijeni={n_in_price_range_val if n_in_price_range_val is not None else '—'} "
                  f"({elapsed_ms}ms)")

            rows.append({
                "query": query,
                "expected_cat_id": expected_cat,
                "expected_tool": expected_tool,
                "expected_args": expected_args,
                "expected_min_results": expected_min_results,
                "failure_reason": failure_reason,
                "tags": tags,
                "category_label": label,
                "routed_tool": routed_tool,
                "routed_cat_id": routed_cat,
                "routed_args": routed_args,
                "routing_verdict": r_verdict,
                "args_verdict": a_verdict,
                "n_returned": len(products),
                "n_in_subtree": n_in_subtree,
                "n_in_price_range": n_in_price_range_val,
                "subtree_total": subtree_product_count,
                "result_verdict": res_verdict,
                "overall_verdict": ovr_verdict,
                "iterations": iterations,
                "latency_ms": elapsed_ms,
                "products": products,
                "tool_calls": tool_calls_parsed,
                "reply": reply,
                "error": None,
            })

    wall_s = time.monotonic() - t_wall

    # Aggregates
    pass_n = sum(1 for r in rows if r["overall_verdict"] == "PASS")
    warn_n = sum(1 for r in rows if r["overall_verdict"] == "WARN")
    fail_n = sum(1 for r in rows if r["overall_verdict"] == "FAIL")
    # Search-only granularnost (samo za pozitivne entry-je koji su išli kroz search)
    search_pass_n = sum(1 for r in rows if r["result_verdict"] == "PASS")
    search_warn_n = sum(1 for r in rows if r["result_verdict"] == "WARN")
    search_fail_n = sum(1 for r in rows if r["result_verdict"] == "FAIL")
    # Routing breakdown
    exact_n = sum(1 for r in rows if r["routing_verdict"] == "EXACT_PARENT")
    desc_n = sum(1 for r in rows if r["routing_verdict"] == "DESCENDANT")
    out_n = sum(1 for r in rows if r["routing_verdict"] == "OUT")
    null_n = sum(1 for r in rows if r["routing_verdict"] == "NULL")
    wrong_tool_n = sum(1 for r in rows if r["routing_verdict"] == "WRONG_TOOL")
    neg_pass_n = sum(1 for r in rows if r["routing_verdict"] == "NEG_PASS")
    neg_regression_n = sum(1 for r in rows if r["routing_verdict"] == "NEG_REGRESSION")
    # Args breakdown (provjera filtera — products-specific signal)
    args_pass_n = sum(1 for r in rows if r.get("args_verdict") == "ARGS_PASS")
    args_partial_n = sum(1 for r in rows if r.get("args_verdict") == "ARGS_PARTIAL")
    args_missing_n = sum(1 for r in rows if r.get("args_verdict") == "ARGS_MISSING")
    total_returned = sum(r["n_returned"] for r in rows)
    # Prosjek u_porodici računamo SAMO preko search_products redova.
    search_rows = [r for r in rows if r["routed_tool"] == "search_products"]
    avg_in_subtree = (sum(r["n_in_subtree"] for r in search_rows) / len(search_rows)
                      if search_rows else 0.0)

    # cat_id → ime kategorije (potrebno HTML-u za prijateljskije badge-ove
    # u tabeli — "175 (Mobiteli)" umjesto golog "175").
    cat_names: dict[str, str] = {}
    for cid, row_data in by_id.items():
        name = (row_data.get("name") or "").strip()
        if name:
            cat_names[cid] = name

    data = {
        "meta": {
            "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": args.url,
            "label": args.label,
            "n_queries": len(rows),
            "wall_s": wall_s,
            "chat_model": chat_model,
            "chat_model_effort": chat_effort,
            "llm_backend": llm_backend,
        },
        "cat_names": cat_names,
        "summary": {
            "total": len(rows),
            "pass_count": pass_n,
            "warn_count": warn_n,
            "fail_count": fail_n,
            "search_pass_count": search_pass_n,
            "search_warn_count": search_warn_n,
            "search_fail_count": search_fail_n,
            "exact_parent_count": exact_n,
            "descendant_count": desc_n,
            "out_count": out_n,
            "null_count": null_n,
            "wrong_tool_count": wrong_tool_n,
            "neg_pass_count": neg_pass_n,
            "neg_regression_count": neg_regression_n,
            "args_pass_count": args_pass_n,
            "args_partial_count": args_partial_n,
            "args_missing_count": args_missing_n,
            "total_returned": total_returned,
            "avg_in_subtree": avg_in_subtree,
        },
        "rows": rows,
    }

    out_path = Path(args.out).expanduser() if args.out else default_out_path(args.label or None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(data), encoding="utf-8")

    # Terminal sažetak (crnogorski ijekavica)
    print()
    print("─" * 72)
    print(f"Ukupno: {len(rows)} upita | ishod: prošlo={pass_n} upozorenje={warn_n} promašaj={fail_n}")
    print(f"Rute: tačna kategorija={exact_n}  podkategorija={desc_n}  van porodice={out_n}  "
          f"bez filtera={null_n}  pogrešan alat={wrong_tool_n}")
    print(f"Negativni: pravilno odbijen={neg_pass_n}  regresija={neg_regression_n}")
    print(f"Filteri: tačni={args_pass_n}  parcijalni={args_partial_n}  nedostaju={args_missing_n}")
    print(f"Trajanje: {wall_s:.1f}s | ukupno vraćeno proizvoda: {total_returned}")
    print(f"HTML izvještaj: {out_path}")
    print("─" * 72)
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
