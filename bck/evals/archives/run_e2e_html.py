"""
E2E HTML eval — pun agent loop preko /api/chat + visualizacija svakog
proizvoda na parent_id stablu.

Razlika u odnosu na run_categories_html.py:
- run_categories_html.py: SAMO klasifikacioni korak (jedan LLM poziv preko
  CLI-ja), gleda da li je Claude izabrao tačan category_id
- run_e2e_html.py: PUN agent loop preko /api/chat (kao test_e2e_visual.py)
  — Claude klasifikuje, search_products vrati proizvode, Claude formatira
  finalni odgovor. Skripta parsira proizvode iz tog odgovora, vezuje ih
  preko name lookup-a na njihov stvarni `categories_id` iz all-products.json,
  i renderuje HTML gdje vidiš routing drift (cat koji je Claude izabrao vs
  expected) PLUS result drift (gdje svaki proizvod realno živi na stablu vs
  expected).

Pretpostavke:
- Server radi na BASE_URL (default http://127.0.0.1:7778), kao i kod
  test_e2e_visual.py. Pokreni: `uvicorn app.main:app --reload --port 7778`
- ChatResponse vraća `tool_calls` polje (additivna izmjena u app/main.py)
- data/all-products.json je svjež (phpMyAdmin export); koristi se za
  name→categories_id lookup

Pokreni:
    python evals/run_e2e_html.py                    # 42 upita iz category_eval.json
    python evals/run_e2e_html.py --limit 5          # quick test
    python evals/run_e2e_html.py --queries path     # custom query set
    python evals/run_e2e_html.py --url http://...   # remote server

Output: docs/category-analysis/e2e-run-latest.html
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

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

EVAL_PATH = PROJECT_ROOT / "evals" / "category_eval.json"
CSV_PATH = PROJECT_ROOT / "data" / "categories.csv"
TOP50_PATH = PROJECT_ROOT / "data" / "categories.json"
PRODUCTS_JSON = PROJECT_ROOT / "data" / "all-products.json"
OUT_DIR = PROJECT_ROOT / "docs" / "category-analysis"

DEFAULT_URL = "http://127.0.0.1:7778"
DEFAULT_TIMEOUT_S = 180


# Regex koji prepoznaje single-line product format u Claude reply-ju.
# Identičan onome iz test_e2e_visual.py — single source of truth bi bila
# zajednička util-funkcija, ali oba fajla su mala pa duplicat ide.
PROD_RE = re.compile(
    r"!?\[?\]?\(?(?P<img>https?://\S+?)?\)?\s*"
    r"\*\*(?P<name>.+?)\*\*\s*—\s*(?P<price>[\d.,]+\s*KM)"
    r"(?:\s*—\s*(?P<avail>[^—\[]+?))?"
    r"(?:\s*—\s*\[[^\]]+\]\((?P<url>https?://\S+?)\))?\s*$"
)


def parse_products_from_reply(reply: str) -> list[dict]:
    """Izvuci product redove iz Markdown reply-ja. Vraća listu sa name/price/url."""
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
            "img": (g.get("img") or "").strip(),
            "avail": (g.get("avail") or "").strip(),
        })
    return out


def load_products_lookup() -> dict[str, str]:
    """name → categories_id. Iz all-products.json (phpMyAdmin export)."""
    if not PRODUCTS_JSON.exists():
        return {}
    data = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entry in data:
        if entry.get("type") != "table":
            continue
        for row in entry.get("data", []):
            name = (row.get("name") or "").strip()
            cid = (row.get("categories_id") or "").strip()
            if name and cid:
                lookup[name] = cid
    return lookup


def match_product_cat(product_name: str, lookup: dict[str, str]) -> str | None:
    """Pokušaj naći `categories_id` za product name. Strategija:
    1. Exact match (najčešći slučaj jer Claude reprodukuje name 1:1)
    2. Prefix match (Claude ponekad obrije zarez/spaces na kraju)
    3. Lowercase exact
    """
    if not product_name:
        return None
    if product_name in lookup:
        return lookup[product_name]
    pn_lower = product_name.lower()
    for name, cid in lookup.items():
        if name.lower() == pn_lower:
            return cid
    # Prefix: prvi 60 char-a kao stable prefix
    if len(product_name) >= 30:
        prefix = product_name[:60].lower()
        for name, cid in lookup.items():
            if name.lower().startswith(prefix):
                return cid
    return None


# ─── Stablo (kopija iz run_categories_html.py) ─────────────────────────────

def load_tree() -> tuple[dict, dict, dict, dict]:
    """Vrati (by_id, children_of, parents_of, top50)."""
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_id = {r["id"]: r for r in rows if r["status"] == "1"}
    children_of: dict[str, list[str]] = defaultdict(list)
    parents_of: dict[str, str] = {}
    for r in rows:
        if r["status"] != "1":
            continue
        children_of[r["parent_id"]].append(r["id"])
        if r["parent_id"] != "0":
            parents_of[r["id"]] = r["parent_id"]
    for k in children_of:
        children_of[k].sort(key=lambda x: int(by_id[x].get("sort_id", "0") or "0"))
    top50 = json.loads(TOP50_PATH.read_text(encoding="utf-8")) if TOP50_PATH.exists() else {}
    return by_id, dict(children_of), parents_of, top50


def ancestors_of(cat_id: str, parents_of: dict[str, str]) -> list[str]:
    chain: list[str] = []
    cur = parents_of.get(cat_id)
    while cur and cur != "0":
        chain.append(cur)
        cur = parents_of.get(cur)
    return chain


def classify_drift(
    expected: str, got: str | None,
    by_id: dict, parents_of: dict[str, str],
) -> str:
    """Vrati drift tip — identično run_categories_html.py."""
    if got is None:
        return "no_value"
    if got == expected:
        return "exact"
    if got not in by_id:
        return "unknown_cat"
    if got in ancestors_of(expected, parents_of):
        return "up_drift"
    if expected in ancestors_of(got, parents_of):
        return "down_drift"
    exp_p = parents_of.get(expected)
    got_p = parents_of.get(got)
    if exp_p and got_p == exp_p:
        return "sibling"
    return "hard_miss"


# ─── /api/chat klijent ─────────────────────────────────────────────────────

def call_chat_api(base_url: str, query: str, timeout: int) -> dict:
    """POST na /api/chat. Vraća dict sa reply, tools_used, tool_calls,
    iterations, escalated. Na grešku vraća {"error": "..."}."""
    try:
        r = httpx.post(
            f"{base_url}/api/chat",
            json={"message": query, "channel": "chat", "history": []},
            timeout=timeout,
        )
    except Exception as exc:
        return {"error": f"http_exc: {exc}"}
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    try:
        return r.json()
    except Exception as exc:
        return {"error": f"json_decode: {exc}"}


def extract_search_call(tool_calls: list[dict]) -> dict | None:
    """Iz tool_calls liste izvuci PRVI search_products poziv (najinformativniji
    za routing analizu). Vraća sve argumente: query, category_id, brand_id…"""
    for tc in tool_calls:
        if tc.get("tool_name") != "search_products":
            continue
        try:
            inp = json.loads(tc.get("input_json", "{}"))
        except json.JSONDecodeError:
            inp = {}
        return {
            "iteration": tc.get("iteration"),
            "query": inp.get("query"),
            "category_id": inp.get("category_id"),
            "brand_id": inp.get("brand_id"),
            "top_k": inp.get("top_k"),
            "max_price_km": inp.get("max_price_km"),
            "latency_ms": tc.get("latency_ms"),
        }
    return None


# ─── Build tree nodes sa eval overlay ─────────────────────────────────────

def build_tree_nodes(
    by_id: dict, children_of: dict, top50: dict, eval_results: list[dict],
) -> list[dict]:
    """Augmentuj svaki cat node sa: queries_targeting (expected==cat),
    products_landed (svaki proizvod koji je realno u toj cat), routing_hits
    (queries gdje je Claude izabrao tu cat)."""

    by_cat_targets: dict[str, list[int]] = defaultdict(list)      # idx u eval_results
    by_cat_chosen: dict[str, list[int]] = defaultdict(list)
    by_cat_products: dict[str, list[tuple[int, dict]]] = defaultdict(list)

    for i, r in enumerate(eval_results):
        by_cat_targets[r["expected"]].append(i)
        chosen = r.get("chosen_category_id")
        if chosen:
            by_cat_chosen[chosen].append(i)
        for p in r.get("products", []):
            if p.get("actual_cat"):
                by_cat_products[p["actual_cat"]].append((i, p))

    def subtree_top50(cid: str) -> int:
        c = 1 if cid in top50 else 0
        for k in children_of.get(cid, []):
            c += subtree_top50(k)
        return c

    def subtree_products(cid: str) -> int:
        c = top50.get(cid, {}).get("count", 0)
        for k in children_of.get(cid, []):
            c += subtree_products(k)
        return c

    def build(cid: str) -> dict:
        r = by_id[cid]
        return {
            "id": cid,
            "name": r["name"],
            "in_top50": cid in top50,
            "products_in_top50": top50.get(cid, {}).get("count", 0),
            "subtree_top50": subtree_top50(cid),
            "subtree_products": subtree_products(cid),
            "children": [build(c) for c in children_of.get(cid, [])],
            "eval": {
                "queries_targeting": by_cat_targets[cid],
                "queries_chosen": by_cat_chosen[cid],
                "products_landed": [
                    {"qi": qi, "name": p["name"], "drift": p["drift"]}
                    for qi, p in by_cat_products[cid]
                ],
            },
        }

    roots = sorted(children_of.get("0", []), key=lambda x: int(by_id[x].get("sort_id", "0") or "0"))
    tree = [build(r) for r in roots]
    tree.sort(key=lambda n: -n["subtree_products"])
    return tree


DRIFT_META = {
    "exact":       ("✓", "#6ee7a0", "Tačan cat"),
    "up_drift":    ("↑", "#ffd34a", "Predak expected cat-a"),
    "down_drift":  ("↓", "#ffd34a", "Dijete expected cat-a"),
    "sibling":     ("≈", "#ffa56a", "Brat (isti parent)"),
    "hard_miss":   ("✗", "#ff6b8a", "Drugi subtree"),
    "unknown_cat": ("?", "#c084fc", "Cat nije u CSV-u"),
    "no_value":    ("—", "#8a94a3", "Bez cat_id-a"),
}


# ─── HTML render ───────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!doctype html>
<html lang="bs">
<head>
<meta charset="utf-8">
<title>BitLab — E2E run sa drift overlay</title>
<style>
  :root {
    --bg:#0f1419; --panel:#161c24; --border:#232b36; --text:#d7dbe0;
    --muted:#8a94a3; --accent:#4cc2ff;
    --ok:#6ee7a0; --warn:#ffd34a; --err:#ff6b8a; --neutral:#8a94a3; --branch:#c084fc;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:-apple-system,"Segoe UI",Inter,system-ui,sans-serif;
    font-size:13px;line-height:1.45}
  header{padding:14px 24px;border-bottom:1px solid var(--border)}
  h1{margin:0 0 3px;font-size:18px;font-weight:600}
  .sub{color:var(--muted);font-size:12px}
  main{padding:12px 24px 60px;max-width:1700px}
  .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
    gap:8px;margin:10px 0 14px}
  .stat{background:var(--panel);border:1px solid var(--border);
    border-radius:6px;padding:8px 12px}
  .stat .v{font-size:20px;font-weight:600;color:var(--accent)}
  .stat .l{color:var(--muted);font-size:11px;text-transform:uppercase;
    letter-spacing:0.05em}
  .stat.exact .v{color:var(--ok)} .stat.miss .v{color:var(--err)}
  .stat.drift .v{color:var(--warn)}
  .layout{display:grid;grid-template-columns:430px 1fr;gap:14px}
  @media(max-width:1000px){.layout{grid-template-columns:1fr}}
  aside.queries{background:var(--panel);border:1px solid var(--border);
    border-radius:6px;padding:6px;max-height:85vh;overflow-y:auto}
  .qcard{padding:7px 9px;border-radius:5px;cursor:pointer;
    border-left:3px solid transparent;margin:3px 0}
  .qcard:hover{background:rgba(76,194,255,0.06)}
  .qcard.selected{background:rgba(76,194,255,0.12);border-left-color:var(--accent)}
  .qcard .qtext{font-weight:500}
  .qcard .qmeta{color:var(--muted);font-size:11px;margin-top:2px;
    font-family:ui-monospace,Menlo,monospace}
  .qcard .qrouting{font-size:11px;margin-top:3px}
  .qcard .qroute-icon{display:inline-block;width:14px;text-align:center;
    font-weight:700;margin-right:3px}
  .qcard .qprods{font-size:11px;color:var(--muted);margin-top:3px;
    display:flex;gap:4px;flex-wrap:wrap}
  .qcard .qprods span{padding:0 5px;border-radius:8px;border:1px solid var(--border);
    background:rgba(255,255,255,0.03)}
  .qcard .qprods span.ok{color:var(--ok);border-color:rgba(110,231,160,0.3);
    background:rgba(110,231,160,0.08)}
  .qcard .qprods span.warn{color:var(--warn);border-color:rgba(255,211,74,0.3);
    background:rgba(255,211,74,0.08)}
  .qcard .qprods span.err{color:var(--err);border-color:rgba(255,107,138,0.3);
    background:rgba(255,107,138,0.08)}
  .detail{background:var(--panel);border:1px solid var(--border);
    border-radius:6px;padding:12px 14px;margin-bottom:14px}
  .detail h3{margin:0 0 8px;font-size:14px}
  .detail .kv{display:grid;grid-template-columns:130px 1fr;gap:3px 12px;
    color:var(--muted);font-size:12px;margin-bottom:6px}
  .detail .kv span:nth-child(odd){text-align:right;color:var(--muted)}
  .detail .kv span:nth-child(even){color:var(--text)}
  .prodlist{display:flex;flex-direction:column;gap:5px;margin-top:8px}
  .prod{display:flex;gap:9px;align-items:center;padding:5px 8px;
    border:1px solid var(--border);border-radius:5px;
    background:rgba(255,255,255,0.02)}
  .prod .drift{font-weight:700;width:18px;text-align:center;font-size:13px}
  .prod .pn{flex:1;font-size:12px}
  .prod .pn b{font-weight:600}
  .prod .pn .nm{color:var(--text)}
  .prod .pn .cm{display:block;color:var(--muted);font-size:11px;margin-top:2px}
  .prod .pp{color:var(--ok);font-weight:600;font-size:12px;white-space:nowrap}
  .prod a{color:var(--accent);text-decoration:none;font-size:11px}
  section.tree-section{background:var(--panel);border:1px solid var(--border);
    border-radius:6px;padding:8px 12px}
  ul.tree,ul.tree ul{list-style:none;padding-left:0;margin:0}
  ul.tree ul{padding-left:16px;border-left:1px dashed var(--border)}
  li.node{margin:1px 0}
  .row{display:flex;align-items:center;gap:6px;padding:3px 5px;border-radius:4px}
  .row:hover{background:rgba(76,194,255,0.06)}
  .row.expected{box-shadow:inset 3px 0 0 var(--warn);
    background:rgba(255,211,74,0.10)}
  .row.chosen{box-shadow:inset 3px 0 0 var(--err);
    background:rgba(255,107,138,0.10)}
  .row.expected.chosen{box-shadow:inset 3px 0 0 var(--ok);
    background:rgba(110,231,160,0.10)}
  .row.has-product{outline:1px dashed rgba(110,231,160,0.4);outline-offset:-1px}
  .toggle{display:inline-block;width:12px;color:var(--muted);cursor:pointer;
    user-select:none;text-align:center;font-family:ui-monospace,monospace;font-size:10px}
  .toggle.leaf{color:transparent;cursor:default}
  .id{color:var(--muted);font-family:ui-monospace,monospace;font-size:11px;
    min-width:38px;text-align:right}
  .name{font-weight:500}
  .name.branch{color:var(--branch)}
  .badge{display:inline-block;padding:0 6px;border-radius:9px;font-size:10px;
    margin-left:4px;background:rgba(255,255,255,0.04);color:var(--muted);
    border:1px solid var(--border);font-weight:500}
  .badge.prod-ct{background:rgba(110,231,160,0.13);color:var(--ok);
    border-color:rgba(110,231,160,0.3)}
  .badge.chosen{background:rgba(255,107,138,0.13);color:var(--err);
    border-color:rgba(255,107,138,0.3)}
  .badge.target{background:rgba(255,211,74,0.13);color:var(--warn);
    border-color:rgba(255,211,74,0.3)}
  .badge.top50{background:rgba(255,157,74,0.13);color:#ff9d4a;
    border-color:rgba(255,157,74,0.3)}
  .hidden{display:none!important}
  .filters{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 10px}
  .filters button{background:var(--panel);color:var(--text);border:1px solid var(--border);
    padding:4px 9px;border-radius:4px;cursor:pointer;font-size:11px}
  .filters button.active{background:var(--accent);color:#0a0d11;
    border-color:var(--accent);font-weight:600}
  .legend{color:var(--muted);font-size:11px;margin:4px 0 8px;
    display:flex;flex-wrap:wrap;gap:6px 12px}
  .legend code{background:var(--panel);padding:1px 5px;border-radius:3px;
    border:1px solid var(--border);color:var(--text)}
  .placeholder{color:var(--muted);text-align:center;padding:60px 20px;font-size:13px}
</style>
</head>
<body>
<header>
  <h1>BitLab — E2E run sa per-product drift overlay</h1>
  <div class="sub" id="meta"></div>
</header>
<main>

<div class="stats" id="stats"></div>

<div class="legend">
  <span><code style="color:var(--ok)">✓</code> Exact</span>
  <span><code style="color:var(--warn)">↑ ↓</code> Up/Down drift (predak/dijete)</span>
  <span><code style="color:#ffa56a">≈</code> Sibling</span>
  <span><code style="color:var(--err)">✗</code> Hard miss</span>
  <span>U drvetu: <code style="color:var(--warn)">žuto</code> = expected cat,
    <code style="color:var(--err)">crveno</code> = Claude izabrao,
    <code style="color:var(--ok)">zeleno</code> = oba poklapaju se</span>
</div>

<div class="filters" id="filters"></div>

<div class="layout">
  <aside class="queries" id="queries"></aside>
  <div>
    <div class="detail" id="detail">
      <div class="placeholder">Klikni upit lijevo da vidiš routing odluku,
        proizvode i drift.</div>
    </div>
    <section class="tree-section">
      <ul class="tree" id="tree"></ul>
    </section>
  </div>
</div>

</main>
<script>
const RUN = __DATA_PLACEHOLDER__;
const DRIFT_META = __DRIFT_META_PLACEHOLDER__;

document.getElementById("meta").textContent =
  `${RUN.meta.base_url}  ·  ${RUN.results.length} upita  ·  ` +
  `ran ${RUN.meta.run_at}  ·  trajanje ~${RUN.meta.duration_s}s`;

// Summary statistike
const totalQ = RUN.results.length;
const exactRoute = RUN.results.filter(r => r.routing_drift === "exact").length;
const totalProds = RUN.results.reduce((a,r) => a + (r.products?.length || 0), 0);
const exactProds = RUN.results.reduce((a,r) =>
  a + (r.products?.filter(p => p.drift === "exact").length || 0), 0);
const driftProds = RUN.results.reduce((a,r) =>
  a + (r.products?.filter(p => p.drift === "up_drift" || p.drift === "down_drift" || p.drift === "sibling").length || 0), 0);
const missProds = totalProds - exactProds - driftProds;
const noResultQs = RUN.results.filter(r => (r.products?.length || 0) === 0).length;

document.getElementById("stats").innerHTML = [
  ["exact", `${exactRoute}/${totalQ}`, "Routing exact"],
  ["drift", `${totalQ - exactRoute}`, "Routing drift"],
  ["exact", totalProds, "Vraćeno proizvoda"],
  ["exact", exactProds, "Produkti u exact cat"],
  ["drift", driftProds, "Produkti u up/down/sibling"],
  ["miss", missProds, "Produkti u hard-miss cat"],
  ["miss", noResultQs, "Queries bez proizvoda"],
].map(([cls,v,l]) =>
  `<div class="stat ${cls}"><div class="v">${v}</div><div class="l">${l}</div></div>`
).join("");

// Filteri
const filtersEl = document.getElementById("filters");
filtersEl.innerHTML = `
  <button data-filter="all" class="active">Sve (${totalQ})</button>
  <button data-filter="route_fail">Routing fail (${totalQ - exactRoute})</button>
  <button data-filter="prod_drift">Imaju drift proizvoda</button>
  <button data-filter="no_results">Bez proizvoda (${noResultQs})</button>
  <button data-filter="escalated">Eskalirano</button>
`;

// Query list
const queriesEl = document.getElementById("queries");
function findNodeName(cid) {
  let f = null;
  (function w(ns) { for (const n of ns) { if (n.id === cid) { f = n.name; return; } w(n.children); if (f) return; }})(RUN.tree);
  return f || "?";
}

queriesEl.innerHTML = RUN.results.map((r, i) => {
  const dm = DRIFT_META[r.routing_drift] || ["?", "var(--muted)", ""];
  const expName = findNodeName(r.expected);
  const chosenName = r.chosen_category_id ? findNodeName(r.chosen_category_id) : "—";
  const nProds = r.products?.length || 0;
  const prodBadges = (r.products || []).map(p => {
    const cls = p.drift === "exact" ? "ok"
              : (p.drift === "up_drift" || p.drift === "down_drift" || p.drift === "sibling") ? "warn"
              : "err";
    return `<span class="${cls}" title="${p.actual_cat || '?'} ${p.actual_cat_name || ''}">${DRIFT_META[p.drift]?.[0] || '?'} ${p.actual_cat || '?'}</span>`;
  }).join("");

  return `<div class="qcard" data-idx="${i}" data-route="${r.routing_drift}"
    data-nprods="${nProds}" data-escalated="${r.escalated ? 1 : 0}">
    <div class="qtext">${r.query}</div>
    <div class="qmeta">exp: ${r.expected} ${expName}</div>
    <div class="qrouting">
      <span class="qroute-icon" style="color:${dm[1]}">${dm[0]}</span>
      Claude: ${r.chosen_category_id || "(none)"} ${chosenName}
      ${r.chosen_brand_id ? ` · brand ${r.chosen_brand_id}` : ""}
      · ${nProds} proizv.
    </div>
    ${prodBadges ? `<div class="qprods">${prodBadges}</div>` : ""}
  </div>`;
}).join("");

// Detail panel
function showDetail(idx) {
  const r = RUN.results[idx];
  const dm = DRIFT_META[r.routing_drift] || ["?", "", ""];
  const expName = findNodeName(r.expected);
  const chosenName = r.chosen_category_id ? findNodeName(r.chosen_category_id) : "—";

  const prodsHtml = (r.products || []).map(p => {
    const pdm = DRIFT_META[p.drift] || ["?", "var(--muted)"];
    return `<div class="prod">
      <span class="drift" style="color:${pdm[1]}" title="${pdm[2] || ''}">${pdm[0]}</span>
      <div class="pn">
        <span class="nm">${p.name}</span>
        <span class="cm">cat ${p.actual_cat || '?'} ${p.actual_cat_name || ''}</span>
      </div>
      <span class="pp">${p.price}</span>
      ${p.url ? `<a href="${p.url}" target="_blank">otvori →</a>` : ""}
    </div>`;
  }).join("") || `<div class="placeholder">Nije vraćeno proizvoda
    (Claude možda nije pozvao search_products ili je reply tekstualan).</div>`;

  const toolsHtml = (r.tools_used || []).map(t => `<code>${t}</code>`).join(" → ") || "—";
  const errHtml = r.error ? `<div style="color:var(--err);margin-top:8px">⚠ ${r.error}</div>` : "";

  document.getElementById("detail").innerHTML = `
    <h3>"${r.query}"</h3>
    <div class="kv">
      <span>Expected cat:</span><span>${r.expected} ${expName}</span>
      <span>Claude izabrao:</span><span style="color:${dm[1]}">${dm[0]} ${r.chosen_category_id || "(none)"} ${chosenName} (${r.routing_drift})</span>
      ${r.chosen_brand_id ? `<span>Brand filter:</span><span>${r.chosen_brand_id}</span>` : ""}
      <span>Tool chain:</span><span>${toolsHtml}</span>
      <span>Iteracije:</span><span>${r.iterations || "?"} ${r.escalated ? "· ESKALIRANO" : ""}</span>
      <span>Latency:</span><span>${r.latency_s}s</span>
    </div>
    <div class="prodlist">${prodsHtml}</div>
    ${errHtml}
  `;

  document.querySelectorAll(".qcard.selected").forEach(c => c.classList.remove("selected"));
  document.querySelector(`.qcard[data-idx="${idx}"]`)?.classList.add("selected");

  // Tree highlights
  document.querySelectorAll(".row").forEach(row => {
    row.classList.remove("expected", "chosen", "has-product");
  });
  const expRow = document.querySelector(`.row[data-id="${r.expected}"]`);
  expRow?.classList.add("expected");
  if (r.chosen_category_id) {
    const chRow = document.querySelector(`.row[data-id="${r.chosen_category_id}"]`);
    chRow?.classList.add("chosen");
  }
  (r.products || []).forEach(p => {
    if (p.actual_cat) {
      document.querySelector(`.row[data-id="${p.actual_cat}"]`)?.classList.add("has-product");
    }
  });

  // Auto-expand ancestors za expected i chosen
  function expandAnc(cid) {
    let el = document.querySelector(`li.node[data-id="${cid}"]`);
    while (el) {
      const ul = el.parentElement;
      if (ul && ul.classList.contains("hidden")) {
        ul.classList.remove("hidden");
        const parentLi = ul.parentElement;
        const tog = parentLi?.querySelector(":scope > .row > .toggle");
        if (tog) tog.textContent = "▼";
      }
      el = ul?.parentElement?.closest("li.node");
    }
  }
  if (r.expected) expandAnc(r.expected);
  if (r.chosen_category_id) expandAnc(r.chosen_category_id);
  (r.products || []).forEach(p => { if (p.actual_cat) expandAnc(p.actual_cat); });
  expRow?.scrollIntoView({behavior:"smooth", block:"center"});
}

// Tree
const treeEl = document.getElementById("tree");
function renderNode(n) {
  const isBranch = n.children.length > 0;
  const li = document.createElement("li");
  li.className = "node";
  li.dataset.id = n.id;
  const row = document.createElement("div");
  row.className = "row";
  row.dataset.id = n.id;

  const tog = document.createElement("span");
  tog.className = "toggle" + (isBranch ? "" : " leaf");
  tog.textContent = isBranch ? "▼" : "·";
  row.appendChild(tog);

  const id = document.createElement("span");
  id.className = "id"; id.textContent = n.id;
  row.appendChild(id);

  const nm = document.createElement("span");
  nm.className = "name" + (isBranch ? " branch" : "");
  nm.textContent = n.name;
  row.appendChild(nm);

  if (n.in_top50) {
    const b = document.createElement("span");
    b.className = "badge top50"; b.textContent = n.products_in_top50;
    row.appendChild(b);
  }
  if (n.eval.queries_targeting.length > 0) {
    const b = document.createElement("span");
    b.className = "badge target";
    b.textContent = `→ ${n.eval.queries_targeting.length}`;
    b.title = "queries targeting this cat";
    row.appendChild(b);
  }
  if (n.eval.queries_chosen.length > 0) {
    const b = document.createElement("span");
    b.className = "badge chosen";
    b.textContent = `claude ${n.eval.queries_chosen.length}`;
    b.title = "queries where Claude chose this cat";
    row.appendChild(b);
  }
  if (n.eval.products_landed.length > 0) {
    const b = document.createElement("span");
    b.className = "badge prod-ct";
    b.textContent = `× ${n.eval.products_landed.length}`;
    b.title = "products returned in this cat";
    row.appendChild(b);
  }

  li.appendChild(row);
  if (isBranch) {
    const ul = document.createElement("ul");
    n.children.forEach(c => ul.appendChild(renderNode(c)));
    li.appendChild(ul);
    tog.addEventListener("click", () => {
      const h = ul.classList.toggle("hidden");
      tog.textContent = h ? "▶" : "▼";
    });
  }
  return li;
}
RUN.tree.forEach(r => treeEl.appendChild(renderNode(r)));

// Wire up clicks
document.querySelectorAll(".qcard").forEach(c => {
  c.addEventListener("click", () => showDetail(parseInt(c.dataset.idx, 10)));
});

// Filter
filtersEl.addEventListener("click", e => {
  if (e.target.tagName !== "BUTTON") return;
  filtersEl.querySelectorAll("button").forEach(b => b.classList.remove("active"));
  e.target.classList.add("active");
  const f = e.target.dataset.filter;
  document.querySelectorAll(".qcard").forEach(card => {
    const route = card.dataset.route;
    const np = parseInt(card.dataset.nprods, 10);
    const esc = card.dataset.escalated === "1";
    let show = true;
    if (f === "all") show = true;
    else if (f === "route_fail") show = route !== "exact";
    else if (f === "prod_drift") show = (np > 0) && card.querySelector(".qprods span.warn, .qprods span.err");
    else if (f === "no_results") show = np === 0;
    else if (f === "escalated") show = esc;
    card.classList.toggle("hidden", !show);
  });
});

// Otvori prvi failing za brzi inspect
const firstFail = RUN.results.findIndex(r => r.routing_drift !== "exact");
if (firstFail >= 0) showDetail(firstFail);
else if (RUN.results.length > 0) showDetail(0);
</script>
</body>
</html>
"""


def render_html(eval_results, tree_nodes, meta):
    data = {"meta": meta, "results": eval_results, "tree": tree_nodes}
    html = HTML_TEMPLATE
    html = html.replace("__DATA_PLACEHOLDER__", json.dumps(data, ensure_ascii=False))
    html = html.replace("__DRIFT_META_PLACEHOLDER__", json.dumps(DRIFT_META, ensure_ascii=False))
    return html


# ─── Main ──────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> int:
    queries_path = Path(args.queries) if args.queries else EVAL_PATH
    if not queries_path.exists():
        print(f"Nema {queries_path}", file=sys.stderr)
        return 1

    cases = json.loads(queries_path.read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[: args.limit]

    # Provjeri da server radi
    try:
        h = httpx.get(f"{args.url}/healthz", timeout=10)
        if h.status_code != 200:
            print(f"Server na {args.url} odgovara {h.status_code} — uvjeri se da je živ.", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Server na {args.url} nedostupan: {e}", file=sys.stderr)
        print(f"Pokreni: uvicorn app.main:app --reload --port 7778", file=sys.stderr)
        return 1

    by_id, children_of, parents_of, top50 = load_tree()
    products_lookup = load_products_lookup()
    print(f"E2E run: {len(cases)} upita · {args.url} · {len(products_lookup):,} product lookup entries")
    print("─" * 80)

    out_path = Path(args.out) if args.out else OUT_DIR / "e2e-run-latest.html"
    checkpoint_path = out_path.with_suffix(".checkpoint.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    eval_results: list[dict] = []
    t_start = time.perf_counter()

    for i, case in enumerate(cases, 1):
        q = case["query"]
        expected = case["expected_category_id"]
        t0 = time.perf_counter()
        api_resp = call_chat_api(args.url, q, args.timeout)
        dt = time.perf_counter() - t0

        if "error" in api_resp:
            row = {
                "query": q, "expected": expected,
                "chosen_category_id": None, "chosen_brand_id": None,
                "routing_drift": "no_value",
                "products": [], "tools_used": [], "iterations": 0,
                "escalated": False, "error": api_resp["error"], "latency_s": round(dt, 1),
            }
            eval_results.append(row)
            print(f"  {i:2}. ERR {q[:50]:50s} → {api_resp['error'][:30]}")
            continue

        tool_calls = api_resp.get("tool_calls", [])
        search_call = extract_search_call(tool_calls)
        chosen_cat = search_call.get("category_id") if search_call else None
        chosen_brand = search_call.get("brand_id") if search_call else None

        # Parse proizvode iz reply Markdown
        reply = api_resp.get("reply", "")
        parsed_prods = parse_products_from_reply(reply)
        products: list[dict] = []
        for p in parsed_prods:
            actual_cat = match_product_cat(p["name"], products_lookup)
            actual_cat_name = by_id.get(actual_cat, {}).get("name", "") if actual_cat else ""
            drift = classify_drift(expected, actual_cat, by_id, parents_of)
            products.append({
                "name": p["name"], "price": p["price"], "url": p["url"],
                "img": p["img"], "avail": p["avail"],
                "actual_cat": actual_cat, "actual_cat_name": actual_cat_name,
                "drift": drift,
            })

        routing_drift = classify_drift(expected, chosen_cat, by_id, parents_of)

        row = {
            "query": q, "expected": expected,
            "chosen_category_id": chosen_cat, "chosen_brand_id": chosen_brand,
            "routing_drift": routing_drift,
            "products": products,
            "tools_used": api_resp.get("tools_used", []),
            "iterations": api_resp.get("iterations", 0),
            "escalated": api_resp.get("escalated", False),
            "error": None, "latency_s": round(dt, 1),
        }
        eval_results.append(row)

        icon = DRIFT_META.get(routing_drift, ("?",))[0]
        prod_drift_summary = "".join({
            "exact": "✓", "up_drift": "↑", "down_drift": "↓",
            "sibling": "≈", "hard_miss": "✗", "unknown_cat": "?", "no_value": "—",
        }.get(p["drift"], "?") for p in products)
        print(f"  {i:2}. {icon} {q[:42]:42s} cat={chosen_cat or '—':>4} "
              f"[{len(products)}p {prod_drift_summary or '∅'}] [{dt:.1f}s]")

        # Inkrementalni checkpoint
        checkpoint_path.write_text(
            json.dumps({"results": eval_results, "url": args.url}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    duration = int(time.perf_counter() - t_start)
    meta = {
        "base_url": args.url,
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration_s": duration,
        "queries_path": str(queries_path.relative_to(PROJECT_ROOT)),
    }

    tree_nodes = build_tree_nodes(by_id, children_of, top50, eval_results)
    html = render_html(eval_results, tree_nodes, meta)
    out_path.write_text(html, encoding="utf-8")

    routing_exact = sum(1 for r in eval_results if r["routing_drift"] == "exact")
    total_p = sum(len(r["products"]) for r in eval_results)
    exact_p = sum(1 for r in eval_results for p in r["products"] if p["drift"] == "exact")
    print("─" * 80)
    print(f"Routing exact: {routing_exact}/{len(eval_results)} = {100*routing_exact/len(eval_results):.0f}%")
    print(f"Proizvodi exact: {exact_p}/{total_p}" + (f" = {100*exact_p/total_p:.0f}%" if total_p else ""))
    print(f"Trajanje: {duration}s · HTML: {out_path}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="E2E HTML eval — pun agent loop preko /api/chat")
    p.add_argument("--url", default=DEFAULT_URL, help=f"Server URL (default {DEFAULT_URL})")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    p.add_argument("--limit", type=int, default=None, help="Pokreni prvih N upita")
    p.add_argument("--queries", default=None, help="Path do queries JSON (default category_eval.json)")
    p.add_argument("--out", default=None, help="Output HTML path")
    args = p.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
