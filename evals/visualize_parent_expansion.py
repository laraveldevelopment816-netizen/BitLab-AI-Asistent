"""
Before/after visualizer za parent_id expansion fix u rag.py.

Generiše HTML stranicu koja deterministički — bez LLM-a, bez servera, bez
embedding indeksa — pokazuje koliko proizvoda RAG hard filter VIDI po cat_id-u
prije i poslije fix-a. Radi nad stvarnim podacima iz `data/categories.csv` +
`data/all-products.json`.

Logika:
- BEFORE: produkcioni filter prije fix-a — `categories_id == cat_id` (equality).
  Za root cat 17 (Računari) ovo je 20 proizvoda, jer su ostali u djeci.
- AFTER: produkcioni filter sa fix-om — `categories_id IN {cat_id, descendants}`.
  Za cat 17 ovo je 197 jer uključuje sve Notebook/Tablet/Desktop child cat-ove.

DoD validacija: pokreni prije commit-a → vidi sve root cat-ove FAIL (pool
coverage < threshold). Pokreni poslije commit-a sa fix-om primijenjenim → vidi
sve PASS. Script sam ne dotiče rag.py — čista in-vivo simulacija oba modela
filtera na istom dataset-u. Tako se izolira "da li fix realno donosi razliku"
od "da li rag.py kod kompajlira/radi".

Output: ~/Downloads/parent-expansion-{YYYYMMDD-HHMMSS}.html (configurabilno --out)

Pokretanje:
    python evals/visualize_parent_expansion.py
    python evals/visualize_parent_expansion.py --out /path/to/report.html
    python evals/visualize_parent_expansion.py --threshold 30   # % pool coverage
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "categories.csv"
PRODUCTS_PATH = PROJECT_ROOT / "data" / "all-products.json"
RAG_PATH = PROJECT_ROOT / "app" / "rag.py"


def detect_fix_state() -> dict:
    """Inspektuj app/rag.py izvor da odluči da li je parent expansion fix
    već primijenjen u produkcijskom kodu.

    Heuristika sa tri provjere — sve tri moraju biti istinite da je fix
    primijenjen:
    1. funkcija `_load_cat_descendants` postoji u izvoru
    2. polje `self._cat_descendants` se inicijalizuje u ProductIndex
    3. filter koristi set membership umjesto `==` equality

    Vraća {applied: bool, evidence: list[(check_name, status)]}. Verdict
    banner u HTML-u i exit code skripte se odlučuju iz `applied`.
    """
    if not RAG_PATH.exists():
        return {"applied": False, "evidence": [("app/rag.py", "MISSING")]}

    src = RAG_PATH.read_text(encoding="utf-8")
    checks = [
        ("_load_cat_descendants helper",
         "def _load_cat_descendants" in src),
        ("self._cat_descendants polje",
         "self._cat_descendants" in src),
        ("set membership filter (not in valid_cats)",
         "not in valid_cats" in src or "in self._cat_descendants" in src),
    ]
    applied = all(ok for _, ok in checks)
    return {
        "applied": applied,
        "evidence": [(name, "YES" if ok else "NO") for name, ok in checks],
    }


def load_tree() -> tuple[dict[str, dict], dict[str, list[str]]]:
    """Vrati (by_id, children_of) za sve aktivne (status=1) cat-ove."""
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
    for k in children_of:
        children_of[k].sort(key=lambda x: int(by_id[x].get("sort_id", "0") or "0"))
    return by_id, dict(children_of)


def descendants(cat_id: str, children_of: dict[str, list[str]]) -> set[str]:
    """{cat_id + svi descendant-i} — isto što i rag._load_cat_descendants vrati."""
    out = {cat_id}
    for c in children_of.get(cat_id, []):
        out |= descendants(c, children_of)
    return out


def load_product_counts() -> Counter:
    """cat_id → broj proizvoda u all-products.json."""
    data = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    rows = next(e["data"] for e in data if e.get("type") == "table" and e.get("name") == "products")
    return Counter((p.get("categories_id") or "").strip() for p in rows)


def compute_delta(
    by_id: dict[str, dict],
    children_of: dict[str, list[str]],
    counts: Counter,
    threshold_pct: float,
    fix_applied: bool,
) -> dict[str, dict]:
    """Za svaki cat računa:
    - direct: pool koji equality filter vidi (samo cat sam)
    - subtree: pool koji set membership filter vidi (cat + descendant-i)
    - current: STVARNA produkcijska brojka, zavisi od fix_applied
    - alternative: hipotetička brojka u drugom modu

    Tako BEFORE HTML (fix_applied=False) prikazuje current=direct (mala
    brojka), a AFTER HTML (fix_applied=True) prikazuje current=subtree
    (velika brojka). Iste sirove brojke, ali "current" se mijenja — što je
    ono što DoD treba da pokaže.

    Verdict mehanika (na CURRENT brojke):
    - LEAF: nema djecu — direct == subtree. Verdict = "NA".
    - PASS: cat trenutno pokriva ≥ threshold% subtree pool-a (znači ili je
      leaf, ili je fix primijenjen, ili je root sa puno direct proizvoda).
    - FAIL: cat trenutno pokriva < threshold% — fix bi pomogao.
    """
    out: dict[str, dict] = {}
    for cid, row in by_id.items():
        kids = children_of.get(cid, [])
        is_leaf = len(kids) == 0
        direct = counts.get(cid, 0)
        subtree_set = descendants(cid, children_of)
        subtree = sum(counts.get(c, 0) for c in subtree_set)

        current = subtree if fix_applied else direct
        alternative = direct if fix_applied else subtree
        # Coverage = koliko subtree pool-a CURRENT mode pokriva
        coverage_pct = (100 * current / subtree) if subtree > 0 else 0.0

        if is_leaf:
            verdict = "NA"
        elif coverage_pct >= threshold_pct:
            verdict = "PASS"
        else:
            verdict = "FAIL"

        out[cid] = {
            "name": row["name"],
            "is_leaf": is_leaf,
            "n_children_recursive": len(subtree_set) - 1,
            "parent_id": (row.get("parent_id") or "").strip(),
            "direct": direct,
            "subtree": subtree,
            "current": current,
            "alternative": alternative,
            "delta": subtree - direct,  # potencijalni gain ili realizovani gain
            "coverage_pct": coverage_pct,
            "verdict": verdict,
        }
    return out


def build_tree_nodes(
    by_id: dict[str, dict],
    children_of: dict[str, list[str]],
    delta_map: dict[str, dict],
) -> list[dict]:
    """Build nested tree za HTML render. Sortiraj root-ove po delti silazno."""
    def node(cid: str) -> dict:
        d = delta_map[cid]
        return {
            "id": cid,
            "name": d["name"],
            "current": d["current"],
            "alternative": d["alternative"],
            "delta": d["delta"],
            "coverage_pct": d["coverage_pct"],
            "verdict": d["verdict"],
            "is_leaf": d["is_leaf"],
            "children": [node(c) for c in children_of.get(cid, [])],
        }

    roots = sorted(
        [c for c, info in by_id.items() if info.get("parent_id", "0") == "0"],
        key=lambda c: -delta_map[c]["delta"],
    )
    return [node(r) for r in roots]


HTML = r"""<!doctype html>
<html lang="bs">
<head>
<meta charset="utf-8">
<title>Parent expansion — before vs after</title>
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
  header{padding:16px 24px;border-bottom:1px solid var(--border)}
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
  table.leaderboard{width:100%;border-collapse:collapse;
    background:var(--panel);border:1px solid var(--border);border-radius:6px;
    overflow:hidden;margin-bottom:18px}
  table.leaderboard th,table.leaderboard td{padding:7px 10px;
    border-bottom:1px solid var(--border);text-align:left;font-size:12px}
  table.leaderboard th{background:rgba(255,255,255,0.02);color:var(--muted);
    text-transform:uppercase;letter-spacing:0.05em;font-weight:600;font-size:11px}
  table.leaderboard tr:last-child td{border-bottom:none}
  table.leaderboard td.id{color:var(--muted);font-family:ui-monospace,monospace}
  table.leaderboard td.num{text-align:right;font-family:ui-monospace,monospace}
  table.leaderboard td.delta{color:var(--ok);font-weight:600;text-align:right;
    font-family:ui-monospace,monospace}
  table.leaderboard td.bar{padding:0;width:38%}
  .barpair{display:flex;height:18px;font-size:10px;font-family:ui-monospace,monospace}
  .barpair .b1{background:rgba(255,107,138,0.5);
    border-right:2px solid var(--fail);min-width:2px}
  .barpair .b2{background:rgba(110,231,160,0.3);min-width:2px}
  .barpair .blab{padding:0 6px;color:var(--muted)}
  ul.tree,ul.tree ul{list-style:none;padding-left:0;margin:0}
  ul.tree ul{padding-left:18px;border-left:1px dashed var(--border)}
  li.node{margin:1px 0}
  .row{display:flex;align-items:center;gap:8px;padding:4px 6px;border-radius:4px}
  .row:hover{background:rgba(76,194,255,0.06)}
  .row.fail{box-shadow:inset 3px 0 0 var(--fail)}
  .row.pass{box-shadow:inset 3px 0 0 var(--ok)}
  .toggle{display:inline-block;width:12px;color:var(--muted);cursor:pointer;
    user-select:none;text-align:center;font-family:ui-monospace,monospace;font-size:10px}
  .toggle.leaf{color:transparent;cursor:default}
  .id{color:var(--muted);font-family:ui-monospace,monospace;font-size:11px;
    min-width:42px;text-align:right}
  .name{font-weight:500;flex:1}
  .before-after{font-family:ui-monospace,monospace;font-size:11px;color:var(--muted)}
  .before-after .b{color:var(--fail)}
  .before-after .a{color:var(--ok);font-weight:600}
  .before-after .d{color:var(--accent);font-weight:600;margin-left:6px}
  .verdict-badge{display:inline-block;padding:1px 7px;border-radius:8px;
    font-size:10px;font-weight:600;letter-spacing:0.04em}
  .verdict-badge.fail{background:rgba(255,107,138,0.18);color:var(--fail)}
  .verdict-badge.pass{background:rgba(110,231,160,0.18);color:var(--ok)}
  .verdict-badge.na{background:rgba(255,255,255,0.04);color:var(--na)}
  .filters{display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap}
  .filters button{background:var(--panel);color:var(--text);border:1px solid var(--border);
    padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px}
  .filters button.active{background:var(--accent);color:#0a0d11;
    border-color:var(--accent);font-weight:600}
  .hidden{display:none!important}
</style>
</head>
<body>
<header>
  <h1>Parent expansion — before vs after</h1>
  <div class="sub" id="meta"></div>
</header>
<main>

<div id="verdict"></div>

<h2>Summary</h2>
<div class="stats" id="stats"></div>

<h2 id="leaderboard-title">Top 15 root cats</h2>
<table class="leaderboard">
  <thead><tr>
    <th>Cat</th><th>Name</th>
    <th class="num" id="col-current">Current</th>
    <th class="num" id="col-alt">Alternative</th>
    <th class="num">Δ</th><th>Coverage</th>
  </tr></thead>
  <tbody id="leaderboard"></tbody>
</table>

<h2>Full tree (sortirano po delti)</h2>
<div class="filters">
  <button data-filter="all" class="active">Sve</button>
  <button data-filter="fail">Samo FAIL bez fix-a (delta > 0)</button>
  <button data-filter="leaves">Leaf cat-ovi (NA — bez promjene)</button>
</div>
<ul class="tree" id="tree"></ul>

</main>
<script>
const DATA = __DATA_PLACEHOLDER__;

document.getElementById("meta").textContent =
  `Generated ${DATA.meta.run_at}  ·  Data: ${DATA.meta.products_count} products, ` +
  `${DATA.meta.cats_count} active cats  ·  Threshold: ${DATA.meta.threshold}%`;

// Verdict banner i kolone — sve se mijenja prema fix_state.applied.
// Iste sirove brojke iz CSV+JSON, ali "current" mijenja smisao između
// runova: kod FAIL-a current=direct (mala), kod PASS-a current=subtree (velika).
const fix = DATA.fix_state;
const verdictEl = document.getElementById("verdict");
const evidenceHtml = fix.evidence.map(([name, status]) =>
  `<li><code style="color:${status==='YES'?'var(--ok)':'var(--fail)'}">${status}</code> ${name}</li>`
).join("");

// Postavi labele za "current" i "alternative" kolone prema stanju
if (fix.applied) {
  document.getElementById("col-current").textContent = "Sa fix-om (current)";
  document.getElementById("col-alt").textContent = "Bez fix-a (bilo bi)";
  document.getElementById("leaderboard-title").textContent =
    "Top 15 root cats — realizovani gain sa parent expansion fix-om";
} else {
  document.getElementById("col-current").textContent = "Bez fix-a (current)";
  document.getElementById("col-alt").textContent = "Sa fix-om (bilo bi)";
  document.getElementById("leaderboard-title").textContent =
    "Top 15 root cats — potencijalni gain ako se fix primijeni";
}

if (fix.applied) {
  verdictEl.innerHTML = `<div class="verdict-banner pass">
    ✓ PASS — rag.py parent expansion fix JE primijenjen
    <small>Trenutni produkcijski kod vraća ${DATA.summary.total_current.toLocaleString()}
    proizvoda kroz root cat upite (bilo bi ${DATA.summary.total_alternative.toLocaleString()}
    bez fix-a). Sve brojke ispod su REALIZED — ono što search() trenutno vraća.
    <ul style="margin:6px 0 0;padding-left:18px">${evidenceHtml}</ul></small>
  </div>`;
} else {
  verdictEl.innerHTML = `<div class="verdict-banner fail">
    ✗ FAIL — rag.py parent expansion fix NIJE primijenjen
    <small>Trenutni produkcijski kod vraća samo ${DATA.summary.total_current.toLocaleString()}
    proizvoda kroz root cat upite. Sa fix-om bi vraćao
    ${DATA.summary.total_alternative.toLocaleString()} — delta od
    +${(DATA.summary.total_alternative - DATA.summary.total_current).toLocaleString()}
    proizvoda. ${DATA.summary.fail_count} parent cat-ova ispod ${DATA.meta.threshold}%
    coverage threshold-a.
    <ul style="margin:6px 0 0;padding-left:18px">${evidenceHtml}</ul></small>
  </div>`;
}

// Stats — "Σ root pool" mijenja vrijednost između BEFORE i AFTER
const currentLabel = fix.applied ? "Σ root pool sa fix-om (current)" : "Σ root pool bez fix-a (current)";
const altLabel = fix.applied ? "Σ bez fix-a (bilo bi)" : "Σ sa fix-om (bilo bi)";
document.getElementById("stats").innerHTML = [
  ["", `${DATA.meta.products_count}`, "Total products"],
  ["", `${DATA.summary.root_count}`, "Root cats"],
  [fix.applied ? "pass" : "fail", `${DATA.summary.total_current.toLocaleString()}`, currentLabel],
  [fix.applied ? "fail" : "pass", `${DATA.summary.total_alternative.toLocaleString()}`, altLabel],
  ["fail", `${DATA.summary.fail_count}`, "Parents FAIL (current)"],
  ["pass", `${DATA.summary.pass_count}`, "Parents PASS (current)"],
].map(([cls, v, l]) =>
  `<div class="stat ${cls}"><div class="v">${v}</div><div class="l">${l}</div></div>`
).join("");

// Leaderboard — current je prominent kolona (boja prema verdict-u).
// Bar chart pokazuje current/alternative pozicije.
const maxAlt = Math.max(...DATA.leaderboard.map(r => Math.max(r.current, r.alternative))) || 1;
const currentColor = fix.applied ? "var(--ok)" : "var(--fail)";
const altColor = fix.applied ? "var(--fail)" : "var(--ok)";

document.getElementById("leaderboard").innerHTML = DATA.leaderboard.map(r => {
  const wCur = Math.max(2, 100 * r.current / maxAlt);
  const wAlt = Math.max(2, 100 * r.alternative / maxAlt);
  return `<tr>
    <td class="id">${r.id}</td>
    <td>${r.name}</td>
    <td class="num" style="color:${currentColor};font-weight:600">${r.current}</td>
    <td class="num" style="color:${altColor}">${r.alternative}</td>
    <td class="delta">${fix.applied ? "+" : "−"}${Math.abs(r.alternative - r.current)}</td>
    <td class="bar">
      <div class="barpair">
        <div class="b1" style="width:${wCur.toFixed(1)}%;background:${currentColor};opacity:0.5"></div>
        <span class="blab">${r.coverage_pct.toFixed(1)}% pool coverage</span>
      </div>
    </td>
  </tr>`;
}).join("");

// Tree
const treeEl = document.getElementById("tree");
function renderNode(n) {
  const isBranch = n.children.length > 0;
  const li = document.createElement("li");
  li.className = "node";
  li.dataset.id = n.id;
  li.dataset.verdict = n.verdict;

  const row = document.createElement("div");
  row.className = "row " + (n.verdict === "FAIL" ? "fail"
                          : n.verdict === "PASS" ? "pass" : "");

  const tog = document.createElement("span");
  tog.className = "toggle" + (isBranch ? "" : " leaf");
  tog.textContent = isBranch ? "▼" : "·";
  row.appendChild(tog);

  const id = document.createElement("span");
  id.className = "id"; id.textContent = n.id;
  row.appendChild(id);

  const nm = document.createElement("span");
  nm.className = "name"; nm.textContent = n.name;
  row.appendChild(nm);

  const ba = document.createElement("span");
  ba.className = "before-after";
  // Prikazi current (prominent) + alternative (mala anotacija)
  const curColor = fix.applied ? "var(--ok)" : "var(--fail)";
  if (n.is_leaf) {
    // Leaf: current = alternative; jednostavno
    ba.innerHTML = `<span style="color:${curColor};font-weight:600">${n.current}</span>`;
  } else {
    // Parent: current je primarna brojka, alternative kao sekundarna info
    const altColor = fix.applied ? "var(--fail)" : "var(--ok)";
    const annotation = n.delta > 0
      ? ` <span style="color:var(--muted);font-size:10px">(${fix.applied ? "was" : "with fix"}: <span style="color:${altColor}">${n.alternative}</span>)</span>`
      : "";
    ba.innerHTML = `<span style="color:${curColor};font-weight:600">${n.current}</span>${annotation}`;
  }
  row.appendChild(ba);

  const vb = document.createElement("span");
  vb.className = "verdict-badge " + n.verdict.toLowerCase();
  vb.textContent = n.verdict;
  row.appendChild(vb);

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
DATA.tree.forEach(r => treeEl.appendChild(renderNode(r)));

// Filters
document.querySelector(".filters").addEventListener("click", e => {
  if (e.target.tagName !== "BUTTON") return;
  document.querySelectorAll(".filters button").forEach(b => b.classList.remove("active"));
  e.target.classList.add("active");
  const f = e.target.dataset.filter;
  document.querySelectorAll("li.node").forEach(li => {
    const v = li.dataset.verdict;
    let show = true;
    if (f === "fail") show = (v === "FAIL");
    else if (f === "leaves") show = (v === "NA");
    li.classList.toggle("hidden", !show);
  });
});
</script>
</body>
</html>
"""


def render(
    delta_map: dict[str, dict],
    tree_nodes: list[dict],
    threshold: float,
    n_products: int,
    n_cats: int,
    fix_state: dict,
) -> str:
    """Generiši HTML sa svim brojkama unutar."""

    # Top 15 root cats po delti — sa current/alternative koji reflektuju
    # stanje rag.py-a (fix_state.applied).
    leaderboard = sorted(
        [
            {
                "id": cid, "name": d["name"],
                "current": d["current"], "alternative": d["alternative"],
                "delta": d["delta"], "coverage_pct": d["coverage_pct"],
            }
            for cid, d in delta_map.items()
            if d["parent_id"] == "0" and d["delta"] > 0
        ],
        key=lambda r: -r["delta"],
    )[:15]

    root_count = sum(1 for d in delta_map.values() if d["parent_id"] == "0")
    fail_count = sum(1 for d in delta_map.values() if d["verdict"] == "FAIL")
    pass_count = sum(1 for d in delta_map.values() if d["verdict"] == "PASS")
    total_current = sum(d["current"] for d in delta_map.values() if d["parent_id"] == "0")
    total_alternative = sum(d["alternative"] for d in delta_map.values() if d["parent_id"] == "0")

    data = {
        "meta": {
            "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "products_count": n_products,
            "cats_count": n_cats,
            "threshold": threshold,
        },
        "fix_state": fix_state,
        "summary": {
            "root_count": root_count,
            "fail_count": fail_count,
            "pass_count": pass_count,
            "total_current": total_current,
            "total_alternative": total_alternative,
        },
        "leaderboard": leaderboard,
        "tree": tree_nodes,
    }
    return HTML.replace("__DATA_PLACEHOLDER__", json.dumps(data, ensure_ascii=False))


def default_out_path() -> Path:
    """Vrati path do Downloads foldera za default output.

    Probava redom:
    1. Linux native: ~/Downloads
    2. WSL → Windows side: /mnt/c/Users/{USER}/Downloads gdje USER probava
       više varijabli (USER, USERNAME, USERPROFILE basename)
    3. WSL fallback: skenira /mnt/c/Users/*/Downloads/ — uzima prvi koji
       postoji (preskače Default, Public, All Users, system folder-e)
    4. Cwd ako ništa od navedenog nije dostupno
    """
    import os
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"parent-expansion-{ts}.html"

    candidates: list[Path] = []

    # 1. Linux native ~/Downloads
    candidates.append(Path.home() / "Downloads")

    # 2. WSL → Windows side: probaj poznate env varijable
    if Path("/mnt/c").exists():
        win_user_candidates: list[str] = []
        for env_var in ("USER", "USERNAME"):
            v = os.environ.get(env_var)
            if v:
                win_user_candidates.append(v)
        # USERPROFILE je tipa "C:\Users\Kule" — uzmi basename
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            win_user_candidates.append(userprofile.replace("\\", "/").rstrip("/").split("/")[-1])
        for u in win_user_candidates:
            candidates.append(Path(f"/mnt/c/Users/{u}/Downloads"))

        # 3. Fallback: skeniraj /mnt/c/Users/*/Downloads/, preskači system folder-e
        users_root = Path("/mnt/c/Users")
        if users_root.exists():
            skip = {"Default", "Default User", "All Users", "Public",
                    "defaultuser0", "WDAGUtilityAccount", "desktop.ini"}
            try:
                for d in users_root.iterdir():
                    if d.name in skip or not d.is_dir():
                        continue
                    dl = d / "Downloads"
                    if dl.exists() and dl.is_dir():
                        candidates.append(dl)
            except (PermissionError, OSError):
                pass

    for c in candidates:
        if c.exists() and c.is_dir():
            return c / fname

    # 4. Last resort: cwd
    return Path.cwd() / fname


def main() -> int:
    p = argparse.ArgumentParser(description="Parent expansion before/after visualizer")
    p.add_argument("--out", default=None, help="Output HTML path (default: ~/Downloads/parent-expansion-{TS}.html)")
    p.add_argument("--threshold", type=float, default=30.0,
                   help="Pool coverage threshold (%%) ispod kojeg je verdict FAIL")
    args = p.parse_args()

    if not CSV_PATH.exists():
        print(f"GREŠKA: {CSV_PATH} ne postoji.", file=sys.stderr)
        return 1
    if not PRODUCTS_PATH.exists():
        print(f"GREŠKA: {PRODUCTS_PATH} ne postoji.", file=sys.stderr)
        return 1

    by_id, children_of = load_tree()
    counts = load_product_counts()
    n_products = sum(counts.values())
    fix_state = detect_fix_state()
    delta_map = compute_delta(
        by_id, children_of, counts, args.threshold,
        fix_applied=fix_state["applied"],
    )
    tree_nodes = build_tree_nodes(by_id, children_of, delta_map)

    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render(delta_map, tree_nodes, args.threshold, n_products, len(by_id), fix_state),
        encoding="utf-8",
    )

    # Terminal summary
    fail_count = sum(1 for d in delta_map.values() if d["verdict"] == "FAIL")
    pass_count = sum(1 for d in delta_map.values() if d["verdict"] == "PASS")
    print("─" * 72)
    print(f"Analiza: {len(by_id)} aktivnih cat-ova, {n_products:,} proizvoda")
    print(f"Threshold pool coverage: {args.threshold}%")
    print()
    print("RAG.PY INSPEKCIJA:")
    for name, status in fix_state["evidence"]:
        mark = "✓" if status == "YES" else "✗"
        print(f"  {mark} {status:<4}  {name}")
    print()
    if fix_state["applied"]:
        print("VERDICT: ✓ PASS — parent expansion fix je primijenjen u rag.py")
        exit_code = 0
    else:
        print("VERDICT: ✗ FAIL — parent expansion fix NIJE primijenjen u rag.py")
        print(f"         {fail_count} root cat-ova ispod {args.threshold}% coverage threshold-a")
        exit_code = 1
    print()
    print(f"Top 10 root cats — current vs alternative pool:")
    leaderboard = sorted(
        [(cid, d) for cid, d in delta_map.items() if d["parent_id"] == "0" and d["delta"] > 0],
        key=lambda x: -x[1]["delta"],
    )[:10]
    cur_label = "with-fix" if fix_state["applied"] else "no-fix"
    alt_label = "no-fix" if fix_state["applied"] else "with-fix"
    print(f"  {'':>4}  {'name':<40}  {cur_label:>10}  {alt_label:>10}  delta")
    for cid, d in leaderboard:
        print(f"  cat {cid:>4}  {d['name']:<40}  {d['current']:>10}  {d['alternative']:>10}  +{d['delta']}")
    print()
    print(f"HTML:  {out_path}")
    print("─" * 72)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
