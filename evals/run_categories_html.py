"""
HTML category-eval visualizer — pokreće stvarne upite kroz `claude` CLI
i renderuje interaktivni izvještaj sa overlay-em na parent_id stablu.

Razlika u odnosu na run_categories_cli.py:
- run_categories_cli.py → terminal pass/fail tabela
- run_categories_html.py → HTML stranica sa drift klasifikacijom
  (exact / up_drift / down_drift / sibling / hard_miss / no_tool /
  no_category / wrong_tool / unknown_cat), per-query timeline i tree
  overlay sa zelenim/crvenim/žutim badge-evima po cat-u.

Tok:
1. Učitaj upite iz evals/category_eval.json (default), ili --queries path.
2. Učitaj parent_id stablo iz data/categories.csv.
3. Za svaki upit pokreni `claude --model {MODEL} -p` sa system_prompt("chat")
   + tools schema, parsiraj JSON odgovor, izvuci category_id i brand_id.
4. Klasifikuj drift svakog upita prema poziciji u stablu.
5. Renderuj HTML u docs/category-analysis/eval-run-latest.html.

Sequential (bez paralelizma) zbog jednostavnosti — ~30s po upitu * 42 upita
≈ 20 minuta za pun set. Inkrementalni checkpoint se piše nakon svakog upita
da prekid ne izgubi rad.

Pokreni:
    python evals/run_categories_html.py
    python evals/run_categories_html.py --limit 5
    python evals/run_categories_html.py --model claude-sonnet-4-6
    python evals/run_categories_html.py --out docs/eval-custom.html
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.system_prompts import system_prompt  # noqa: E402
from app.tools import ALL_TOOLS  # noqa: E402

EVAL_PATH = PROJECT_ROOT / "evals" / "category_eval.json"
CSV_PATH = PROJECT_ROOT / "data" / "categories.csv"
TOP50_PATH = PROJECT_ROOT / "data" / "categories.json"
OUT_DIR = PROJECT_ROOT / "docs" / "category-analysis"

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_TIMEOUT_S = 300


# ─── CLI classifier (replicira run_categories_cli.py) ──────────────────────

JSON_INSTRUCTION = """
Ti si AI asistent za prodaju (BitLab). Imaš listu alata. Za korisnikov upit,
odluči koji alat bi pozvao i sa kojim argumentima. Odgovori ISKLJUČIVO jednim
JSON objektom, bez ikakvog dodatnog teksta, markdown fence-a, niti komentara.

Format odgovora (striktno):
{"tool": "<naziv_alata>", "input": {<argumenti>}}

Dostupni alati:
"""


def _build_prompt(user_query: str) -> str:
    tools_text = json.dumps(ALL_TOOLS, ensure_ascii=False, indent=2)
    base_sys = system_prompt("chat")
    return (
        f"{base_sys}\n\n---\n{JSON_INSTRUCTION}\n{tools_text}\n\n"
        f"---\nKorisnikov upit: {user_query}\n\nJSON odgovor:"
    )


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("\n", 1)[0] if "\n" in text else text[:-3]
    text = re.sub(r"^(?:json|JSON)\s*[,:]?\s*", "", text.strip())
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    return text.strip()


def classify_query(query: str, model: str, timeout: int) -> dict:
    """Pokreni `claude` CLI, parsiraj JSON, vrati tool/category/brand info."""
    prompt = _build_prompt(query)
    try:
        result = subprocess.run(
            ["claude", "--model", model, "-p", "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"tool_name": None, "category_id": None, "brand_id": None,
                "error": f"timeout ({timeout}s)"}

    if result.returncode != 0:
        return {"tool_name": None, "category_id": None, "brand_id": None,
                "error": f"CLI exit {result.returncode}: {result.stderr.strip()[:200]}"}

    try:
        envelope = json.loads(result.stdout)
        raw_output = envelope.get("result", result.stdout)
    except json.JSONDecodeError:
        raw_output = result.stdout

    cleaned = _strip_fences(raw_output)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return {"tool_name": None, "category_id": None, "brand_id": None,
                "error": f"JSON parse fail: {exc} | raw: {cleaned[:120]}"}

    tool_name = parsed.get("tool")
    tool_input = parsed.get("input") or {}
    return {
        "tool_name": tool_name,
        "category_id": tool_input.get("category_id") if tool_name == "search_products" else None,
        "brand_id": tool_input.get("brand_id") if tool_name == "search_products" else None,
        "error": None,
    }


# ─── Stablo iz CSV-a ───────────────────────────────────────────────────────

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

    top50: dict = {}
    if TOP50_PATH.exists():
        top50 = json.loads(TOP50_PATH.read_text(encoding="utf-8"))

    return by_id, dict(children_of), parents_of, top50


def ancestors_of(cat_id: str, parents_of: dict[str, str]) -> list[str]:
    chain: list[str] = []
    cur = parents_of.get(cat_id)
    while cur and cur != "0":
        chain.append(cur)
        cur = parents_of.get(cur)
    return chain


def classify_drift(
    expected: str,
    got: str | None,
    tool_name: str | None,
    by_id: dict,
    parents_of: dict[str, str],
) -> str:
    """Vrati drift tip — koristi se za boju i sortiranje u HTML-u."""
    if tool_name is None:
        return "no_tool"
    if tool_name != "search_products":
        return "wrong_tool"
    if got is None:
        return "no_category"
    if got == expected:
        return "exact"
    if got not in by_id:
        return "unknown_cat"
    exp_ancestors = ancestors_of(expected, parents_of)
    got_ancestors = ancestors_of(got, parents_of)
    if got in exp_ancestors:
        return "up_drift"  # got je predak od expected
    if expected in got_ancestors:
        return "down_drift"  # got je dijete od expected
    exp_parent = parents_of.get(expected)
    got_parent = parents_of.get(got)
    if exp_parent and got_parent == exp_parent:
        return "sibling"
    return "hard_miss"


# ─── Build augmented tree za HTML render ───────────────────────────────────

def build_tree_nodes(
    by_id: dict,
    children_of: dict[str, list[str]],
    top50: dict,
    eval_results: list[dict],
) -> list[dict]:
    """Vrati listu root nodova; svaki ima `eval` field sa hit/miss listama."""

    # Index eval rezultata po cat_id
    by_cat_got: dict[str, list[dict]] = defaultdict(list)
    by_cat_expected: dict[str, list[dict]] = defaultdict(list)
    for r in eval_results:
        if r["got"]:
            by_cat_got[r["got"]].append(r)
        by_cat_expected[r["expected"]].append(r)

    def subtree_top50(cid: str) -> int:
        cnt = 1 if cid in top50 else 0
        for c in children_of.get(cid, []):
            cnt += subtree_top50(c)
        return cnt

    def subtree_products(cid: str) -> int:
        cnt = top50.get(cid, {}).get("count", 0)
        for c in children_of.get(cid, []):
            cnt += subtree_products(c)
        return cnt

    def build(cid: str) -> dict:
        r = by_id[cid]
        exp_hits = [q for q in by_cat_expected[cid] if q["drift"] == "exact"]
        exp_missed = [q for q in by_cat_expected[cid] if q["drift"] != "exact"]
        false_hits = [q for q in by_cat_got[cid] if q["expected"] != cid]
        return {
            "id": cid,
            "name": r["name"],
            "in_top50": cid in top50,
            "products_in_top50": top50.get(cid, {}).get("count", 0),
            "subtree_top50": subtree_top50(cid),
            "subtree_products": subtree_products(cid),
            "children": [build(c) for c in children_of.get(cid, [])],
            "eval": {
                "exact": len(exp_hits),
                "missed": len(exp_missed),
                "false": len(false_hits),
                "exact_queries": exp_hits,
                "missed_queries": exp_missed,
                "false_queries": false_hits,
            },
        }

    roots = sorted(children_of.get("0", []), key=lambda x: int(by_id[x].get("sort_id", "0") or "0"))
    tree = [build(r) for r in roots]
    tree.sort(key=lambda n: -n["subtree_products"])
    return tree


# ─── HTML render ───────────────────────────────────────────────────────────

DRIFT_META = {
    "exact":       ("✓", "#6ee7a0", "Tačno pogođen cat_id"),
    "up_drift":    ("↑", "#ffd34a", "Pogodio root umjesto djeteta (bi prošlo sa parent expansion)"),
    "down_drift":  ("↓", "#ffd34a", "Pogodio dijete umjesto root-a"),
    "sibling":     ("≈", "#ffa56a", "Drugi child istog parent-a (semantički blizu)"),
    "hard_miss":   ("✗", "#ff6b8a", "Potpuno pogrešna kategorija"),
    "unknown_cat": ("?", "#c084fc", "Cat_id koji ne postoji u CSV-u (ghost)"),
    "no_category": ("∅", "#8a94a3", "search_products bez category_id"),
    "no_tool":     ("—", "#8a94a3", "Nije pozvao nijedan tool"),
    "wrong_tool":  ("⊘", "#8a94a3", "Pozvao drugi tool (npr. get_faq)"),
}


HTML_TEMPLATE = r"""<!doctype html>
<html lang="bs">
<head>
<meta charset="utf-8">
<title>BitLab — Category eval run</title>
<style>
  :root {
    --bg: #0f1419; --panel: #161c24; --border: #232b36;
    --text: #d7dbe0; --muted: #8a94a3; --accent: #4cc2ff;
    --ok: #6ee7a0; --warn: #ffd34a; --err: #ff6b8a; --neutral: #8a94a3;
    --branch: #c084fc;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, "Segoe UI", Inter, system-ui, sans-serif;
    font-size: 13px; line-height: 1.45; }
  header { padding: 16px 24px; border-bottom: 1px solid var(--border); }
  h1 { margin: 0 0 4px; font-size: 18px; font-weight: 600; }
  .sub { color: var(--muted); font-size: 12px; }
  main { padding: 14px 24px 80px; max-width: 1500px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 8px; margin: 12px 0 16px; }
  .stat { background: var(--panel); border: 1px solid var(--border);
    border-radius: 6px; padding: 8px 12px; }
  .stat .v { font-size: 20px; font-weight: 600; }
  .stat.exact .v { color: var(--ok); }
  .stat.up_drift .v, .stat.down_drift .v { color: var(--warn); }
  .stat.sibling .v { color: #ffa56a; }
  .stat.hard_miss .v { color: var(--err); }
  .stat.no_tool .v, .stat.no_category .v, .stat.wrong_tool .v { color: var(--neutral); }
  .stat.unknown_cat .v { color: var(--branch); }
  .stat.passrate .v { color: var(--accent); }
  .stat .l { color: var(--muted); font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.05em; }
  .filters { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 14px; }
  .filters button { background: var(--panel); color: var(--text);
    border: 1px solid var(--border); padding: 4px 10px; border-radius: 4px;
    cursor: pointer; font-size: 12px; }
  .filters button:hover { border-color: var(--accent); }
  .filters button.active { background: var(--accent); color: #0a0d11;
    border-color: var(--accent); font-weight: 600; }
  .layout { display: grid; grid-template-columns: 380px 1fr; gap: 16px; }
  @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }
  aside.queries { background: var(--panel); border: 1px solid var(--border);
    border-radius: 6px; padding: 6px; max-height: 80vh; overflow-y: auto; }
  .qcard { padding: 7px 10px; border-radius: 5px; cursor: pointer;
    border-left: 3px solid transparent; margin: 2px 0; }
  .qcard:hover { background: rgba(76,194,255,0.06); }
  .qcard.selected { background: rgba(76,194,255,0.12);
    border-left-color: var(--accent); }
  .qcard .qtext { font-weight: 500; }
  .qcard .qmeta { color: var(--muted); font-size: 11px; margin-top: 2px;
    font-family: ui-monospace, Menlo, monospace; }
  .qcard .drift-icon { display: inline-block; width: 16px; text-align: center;
    font-weight: 700; margin-right: 4px; }
  section.tree-section { background: var(--panel); border: 1px solid var(--border);
    border-radius: 6px; padding: 10px 14px; }
  ul.tree, ul.tree ul { list-style: none; padding-left: 0; margin: 0; }
  ul.tree ul { padding-left: 18px; border-left: 1px dashed var(--border); }
  li.node { margin: 1px 0; }
  .row { display: flex; align-items: center; gap: 6px; padding: 3px 6px;
    border-radius: 4px; }
  .row:hover { background: rgba(76,194,255,0.06); }
  .row.expected-hit { box-shadow: inset 3px 0 0 var(--ok); }
  .row.expected-target { box-shadow: inset 3px 0 0 var(--warn);
    background: rgba(255,211,74,0.08); }
  .row.got-target { box-shadow: inset 3px 0 0 var(--err);
    background: rgba(255,107,138,0.08); }
  .toggle { display: inline-block; width: 12px; color: var(--muted);
    cursor: pointer; user-select: none; text-align: center;
    font-family: ui-monospace, Menlo, monospace; font-size: 10px; }
  .toggle.leaf { color: transparent; cursor: default; }
  .id { color: var(--muted); font-family: ui-monospace, Menlo, monospace;
    font-size: 11px; min-width: 38px; text-align: right; }
  .name { font-weight: 500; }
  .name.branch { color: var(--branch); }
  .badge { display: inline-block; padding: 0 6px; border-radius: 9px;
    font-size: 10px; margin-left: 4px; background: rgba(255,255,255,0.04);
    color: var(--muted); border: 1px solid var(--border); font-weight: 500; }
  .badge.ok { background: rgba(110,231,160,0.13); color: var(--ok);
    border-color: rgba(110,231,160,0.3); }
  .badge.warn { background: rgba(255,211,74,0.13); color: var(--warn);
    border-color: rgba(255,211,74,0.3); }
  .badge.err { background: rgba(255,107,138,0.13); color: var(--err);
    border-color: rgba(255,107,138,0.3); }
  .badge.top50 { background: rgba(255,157,74,0.13); color: #ff9d4a;
    border-color: rgba(255,157,74,0.3); }
  .hidden { display: none !important; }
  .legend { color: var(--muted); font-size: 11px; margin: 6px 0 10px;
    display: flex; flex-wrap: wrap; gap: 8px 14px; }
  .legend span code { background: var(--panel); padding: 1px 5px;
    border-radius: 3px; border: 1px solid var(--border); color: var(--text); }
</style>
</head>
<body>
<header>
  <h1>BitLab — Category eval run</h1>
  <div class="sub" id="meta"></div>
</header>
<main>

<div class="stats" id="stats"></div>

<div class="legend">
  <span><code style="color:var(--ok)">✓</code> Exact (got==expected)</span>
  <span><code style="color:var(--warn)">↑</code> Up-drift (got je predak — bi prošlo sa parent expansion)</span>
  <span><code style="color:var(--warn)">↓</code> Down-drift (got je dijete)</span>
  <span><code style="color:#ffa56a">≈</code> Sibling (isti parent)</span>
  <span><code style="color:var(--err)">✗</code> Hard miss</span>
  <span><code style="color:var(--neutral)">∅ — ⊘</code> No category / No tool / Wrong tool</span>
</div>

<div class="filters" id="filters"></div>

<div class="layout">
  <aside class="queries" id="queries"></aside>
  <section class="tree-section">
    <ul class="tree" id="tree"></ul>
  </section>
</div>

</main>
<script>
const RUN = __DATA_PLACEHOLDER__;
const DRIFT_META = __DRIFT_META_PLACEHOLDER__;

const metaEl = document.getElementById("meta");
metaEl.textContent = `model: ${RUN.meta.model}  ·  ran: ${RUN.meta.run_at}  ·  ${RUN.results.length} upita  ·  trajanje ~${RUN.meta.duration_s}s`;

const statsEl = document.getElementById("stats");
const driftCounts = {};
for (const r of RUN.results) {
  driftCounts[r.drift] = (driftCounts[r.drift] || 0) + 1;
}
const exact = driftCounts.exact || 0;
const upDrift = driftCounts.up_drift || 0;
const passWithExpand = exact + upDrift;
const total = RUN.results.length;

const statItems = [
  ["passrate", "Pass rate", `${exact}/${total} = ${(100*exact/total).toFixed(0)}%`],
  ["passrate", "+ Up-drift", `${passWithExpand}/${total} = ${(100*passWithExpand/total).toFixed(0)}%`],
  ["exact", "Exact ✓", exact],
  ["up_drift", "Up-drift ↑", upDrift],
  ["down_drift", "Down-drift ↓", driftCounts.down_drift || 0],
  ["sibling", "Sibling ≈", driftCounts.sibling || 0],
  ["hard_miss", "Hard miss ✗", driftCounts.hard_miss || 0],
  ["unknown_cat", "Unknown cat", driftCounts.unknown_cat || 0],
  ["no_category", "No category", driftCounts.no_category || 0],
  ["no_tool", "No tool", driftCounts.no_tool || 0],
  ["wrong_tool", "Wrong tool", driftCounts.wrong_tool || 0],
];
statsEl.innerHTML = statItems.map(([cls, label, val]) =>
  `<div class="stat ${cls}"><div class="v">${val}</div><div class="l">${label}</div></div>`
).join("");

// Filters
const driftTypes = ["all", "failures", ...Object.keys(DRIFT_META)];
const filtersEl = document.getElementById("filters");
filtersEl.innerHTML = driftTypes.map(d => {
  const label = d === "all" ? `Sve (${total})`
              : d === "failures" ? `Failures (${total - exact})`
              : `${DRIFT_META[d][0]} ${d} (${driftCounts[d] || 0})`;
  return `<button data-filter="${d}">${label}</button>`;
}).join("");
filtersEl.querySelector('[data-filter="all"]').classList.add("active");

// Query list
const queriesEl = document.getElementById("queries");
const driftOrder = ["hard_miss", "wrong_tool", "no_tool", "no_category",
                    "unknown_cat", "sibling", "down_drift", "up_drift", "exact"];
const sortedResults = [...RUN.results].sort((a, b) => {
  const ai = driftOrder.indexOf(a.drift), bi = driftOrder.indexOf(b.drift);
  if (ai !== bi) return ai - bi;
  return a.query.localeCompare(b.query);
});

function findNodeName(cid) {
  let found = null;
  function walk(nodes) {
    for (const n of nodes) {
      if (n.id === cid) { found = n.name; return; }
      walk(n.children);
      if (found) return;
    }
  }
  walk(RUN.tree);
  return found || "?";
}

queriesEl.innerHTML = sortedResults.map((r, i) => {
  const [icon, color, _] = DRIFT_META[r.drift];
  const expectedName = findNodeName(r.expected);
  const gotName = r.got ? findNodeName(r.got) : (r.tool_name || "(no tool)");
  const gotLabel = r.got ? `${r.got} ${gotName}` : (r.tool_name || "—");
  return `<div class="qcard" data-idx="${i}" data-drift="${r.drift}"
    data-expected="${r.expected}" data-got="${r.got || ''}">
    <div class="qtext"><span class="drift-icon" style="color:${color}">${icon}</span>${r.query}</div>
    <div class="qmeta">exp: ${r.expected} ${expectedName}  ←  got: ${gotLabel}</div>
  </div>`;
}).join("");

// Tree rendering
const treeEl = document.getElementById("tree");

function renderNode(n) {
  const isBranch = n.children.length > 0;
  const li = document.createElement("li");
  li.className = "node";
  li.dataset.id = n.id;

  const row = document.createElement("div");
  row.className = "row";
  row.dataset.id = n.id;

  const toggle = document.createElement("span");
  toggle.className = "toggle" + (isBranch ? "" : " leaf");
  toggle.textContent = isBranch ? "▼" : "·";
  row.appendChild(toggle);

  const id = document.createElement("span");
  id.className = "id";
  id.textContent = n.id;
  row.appendChild(id);

  const name = document.createElement("span");
  name.className = "name" + (isBranch ? " branch" : "");
  name.textContent = n.name;
  row.appendChild(name);

  if (n.in_top50) {
    const b = document.createElement("span");
    b.className = "badge top50";
    b.textContent = `${n.products_in_top50}`;
    b.title = `${n.products_in_top50} proizvoda — u top-50 koje AI vidi`;
    row.appendChild(b);
  }
  if (n.eval.exact > 0) {
    const b = document.createElement("span");
    b.className = "badge ok";
    b.textContent = `✓ ${n.eval.exact}`;
    b.title = "Upiti koji su tačno pogodili ovaj cat";
    row.appendChild(b);
  }
  if (n.eval.missed > 0) {
    const b = document.createElement("span");
    b.className = "badge warn";
    b.textContent = `→ ${n.eval.missed}`;
    b.title = "Upiti koji su trebali ovamo ali su otišli negdje drugo";
    row.appendChild(b);
  }
  if (n.eval.false > 0) {
    const b = document.createElement("span");
    b.className = "badge err";
    b.textContent = `✗ ${n.eval.false}`;
    b.title = "Upiti koji su pogrešno landali ovdje";
    row.appendChild(b);
  }

  li.appendChild(row);

  if (isBranch) {
    const ul = document.createElement("ul");
    n.children.forEach(c => ul.appendChild(renderNode(c)));
    li.appendChild(ul);
    toggle.addEventListener("click", () => {
      const collapsed = ul.classList.toggle("hidden");
      toggle.textContent = collapsed ? "▶" : "▼";
    });
  }
  return li;
}

RUN.tree.forEach(root => treeEl.appendChild(renderNode(root)));

// Selection: click query → highlight expected + got
function clearHighlights() {
  document.querySelectorAll(".row").forEach(r => {
    r.classList.remove("expected-target", "got-target", "expected-hit");
  });
}
function expandAncestors(cid) {
  let el = document.querySelector(`li.node[data-id="${cid}"]`);
  while (el) {
    if (el.parentElement && el.parentElement.classList.contains("hidden")) {
      el.parentElement.classList.remove("hidden");
      const parentLi = el.parentElement.parentElement;
      const tog = parentLi?.querySelector(":scope > .row > .toggle");
      if (tog) tog.textContent = "▼";
    }
    el = el.parentElement?.closest("li.node");
  }
}

document.querySelectorAll(".qcard").forEach(card => {
  card.addEventListener("click", () => {
    document.querySelectorAll(".qcard.selected").forEach(c => c.classList.remove("selected"));
    card.classList.add("selected");
    clearHighlights();
    const exp = card.dataset.expected;
    const got = card.dataset.got;
    const drift = card.dataset.drift;
    if (exp) expandAncestors(exp);
    if (got && got !== exp) expandAncestors(got);
    const expRow = document.querySelector(`.row[data-id="${exp}"]`);
    const gotRow = got ? document.querySelector(`.row[data-id="${got}"]`) : null;
    if (drift === "exact") {
      expRow?.classList.add("expected-hit");
    } else {
      expRow?.classList.add("expected-target");
      gotRow?.classList.add("got-target");
    }
    expRow?.scrollIntoView({behavior: "smooth", block: "center"});
  });
});

// Filters
filtersEl.addEventListener("click", e => {
  if (e.target.tagName !== "BUTTON") return;
  filtersEl.querySelectorAll("button").forEach(b => b.classList.remove("active"));
  e.target.classList.add("active");
  const f = e.target.dataset.filter;
  document.querySelectorAll(".qcard").forEach(card => {
    const d = card.dataset.drift;
    let show = true;
    if (f === "all") show = true;
    else if (f === "failures") show = (d !== "exact");
    else show = (d === f);
    card.classList.toggle("hidden", !show);
  });
});
</script>
</body>
</html>
"""


def render_html(
    eval_results: list[dict],
    tree_nodes: list[dict],
    meta: dict,
) -> str:
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

    by_id, children_of, parents_of, top50 = load_tree()

    print(f"Eval (HTML): {len(cases)} upita · model={args.model} · timeout={args.timeout}s")
    print("─" * 80)

    eval_results: list[dict] = []
    t_start = time.perf_counter()
    out_path = Path(args.out) if args.out else OUT_DIR / "eval-run-latest.html"
    checkpoint_path = out_path.with_suffix(".checkpoint.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    for i, case in enumerate(cases, 1):
        q = case["query"]
        expected = case["expected_category_id"]
        t0 = time.perf_counter()
        r = classify_query(q, args.model, args.timeout)
        dt = time.perf_counter() - t0

        drift = "no_tool" if r.get("error") else classify_drift(
            expected, r["category_id"], r["tool_name"], by_id, parents_of
        )
        row = {
            "query": q,
            "expected": expected,
            "expected_label": case.get("category_label", ""),
            "got": r["category_id"],
            "tool_name": r["tool_name"],
            "brand_id": r.get("brand_id"),
            "drift": drift,
            "error": r.get("error"),
            "latency_s": round(dt, 2),
        }
        eval_results.append(row)

        icon = DRIFT_META.get(drift, ("?", "", ""))[0]
        got_str = r["category_id"] or (r["tool_name"] or "—")
        print(f"  {i:2}. {icon} {q[:50]:50s} → exp={expected:>4} got={got_str:>5}  [{drift}, {dt:.1f}s]")

        # Inkrementalni checkpoint nakon svakog upita
        checkpoint_path.write_text(
            json.dumps({"results": eval_results, "model": args.model}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    duration = int(time.perf_counter() - t_start)
    meta = {
        "model": args.model,
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration_s": duration,
        "queries_path": str(queries_path.relative_to(PROJECT_ROOT)),
    }

    tree_nodes = build_tree_nodes(by_id, children_of, top50, eval_results)
    html = render_html(eval_results, tree_nodes, meta)
    out_path.write_text(html, encoding="utf-8")

    exact = sum(1 for r in eval_results if r["drift"] == "exact")
    up_drift = sum(1 for r in eval_results if r["drift"] == "up_drift")
    print("─" * 80)
    print(f"Pass rate (strict): {exact}/{len(eval_results)} = {100*exact/len(eval_results):.0f}%")
    print(f"Pass rate (+ up-drift): {exact + up_drift}/{len(eval_results)} = "
          f"{100*(exact+up_drift)/len(eval_results):.0f}%")
    print(f"HTML: {out_path}")
    print(f"Checkpoint: {checkpoint_path}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="HTML category eval visualizer (preko Claude CLI)")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model za CLI (default: {DEFAULT_MODEL})")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                   help=f"Timeout u sekundama po pozivu (default: {DEFAULT_TIMEOUT_S})")
    p.add_argument("--limit", type=int, default=None, help="Pokreni samo prvih N upita (za quick test)")
    p.add_argument("--queries", default=None, help="Path do queries JSON (default: evals/category_eval.json)")
    p.add_argument("--out", default=None, help="Output HTML path (default: docs/category-analysis/eval-run-latest.html)")
    args = p.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
