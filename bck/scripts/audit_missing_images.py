"""
Audit: nađi sve proizvode u indeksu čije `cover` slike vraćaju 302 redirect
na homepage (= slika ne postoji na webshop strani).

Cover polje u products.meta.json sadrži ime fajla u
`https://webshop.bitlab.rs/files/products/img/{cover}`. Webshop server
ima 302 fallback koji preusmjerava sve missing fajlove na homepage —
browser pokuša loadovati to kao sliku, dobije HTML, onerror sakrije
<img> → korisnik vidi placeholder.

Ovo je data-quality problem koji webshop admin treba da riješi (re-upload
slike ili clear cover polje u DB-u). Naš job je da ih nabrojimo.

Pokreni: python scripts/audit_missing_images.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
META_PATH = PROJECT_ROOT / "data" / "products.meta.json"
OUT_PATH = PROJECT_ROOT / "data" / "missing_images.json"

WEBSHOP = "https://webshop.bitlab.rs"
HOMEPAGE_REDIRECT = WEBSHOP  # 302 sa Location: homepage = missing


async def check_one(client: httpx.AsyncClient, sifra: str, name: str, cover: str) -> dict | None:
    """Vrati dict ako je slika missing, None ako je OK."""
    url = f"{WEBSHOP}/files/products/img/{cover}"
    try:
        resp = await client.head(url, follow_redirects=False, timeout=10)
    except Exception as exc:
        return {"sifra": sifra, "name": name, "cover": cover, "url": url, "error": str(exc)}

    if resp.status_code == 200:
        return None  # OK
    if resp.status_code in (301, 302, 303, 307, 308):
        loc = resp.headers.get("location", "")
        if loc.rstrip("/") == HOMEPAGE_REDIRECT.rstrip("/"):
            return {"sifra": sifra, "name": name, "cover": cover, "url": url,
                    "issue": "302 → homepage (slika ne postoji)"}
        return {"sifra": sifra, "name": name, "cover": cover, "url": url,
                "issue": f"redirect to {loc}"}
    return {"sifra": sifra, "name": name, "cover": cover, "url": url,
            "issue": f"HTTP {resp.status_code}"}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="Ograniči na N proizvoda (0 = svi)")
    ap.add_argument("--concurrency", type=int, default=20,
                    help="Paralelni HTTP requestovi (default 20)")
    args = ap.parse_args()

    if not META_PATH.exists():
        print(f"Nema {META_PATH}", file=sys.stderr)
        sys.exit(1)

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    products = meta["products"]

    candidates = [
        (pid, p.get("sifra", ""), p.get("name", ""), p.get("cover") or "")
        for pid, p in products.items()
        if p.get("cover")
    ]
    if args.limit:
        candidates = candidates[: args.limit]

    print(f"Provjera {len(candidates):,} proizvoda sa cover poljem (concurrency={args.concurrency})...")

    sem = asyncio.Semaphore(args.concurrency)
    missing: list[dict] = []

    async with httpx.AsyncClient() as client:
        async def worker(item):
            pid, sifra, name, cover = item
            async with sem:
                result = await check_one(client, sifra, name, cover)
                if result:
                    missing.append(result)
                if (len(missing) % 50 == 0) and missing:
                    print(f"  ... pronađeno {len(missing)} missing do sada")

        await asyncio.gather(*[worker(item) for item in candidates])

    OUT_PATH.write_text(
        json.dumps({"checked": len(candidates), "missing": missing}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ Provjereno: {len(candidates):,}")
    print(f"❌ Missing: {len(missing):,} ({100*len(missing)/len(candidates):.1f}%)")
    print(f"📄 Output: {OUT_PATH.relative_to(PROJECT_ROOT)}")
    if missing:
        print("\nPrvih 10 primjera:")
        for m in missing[:10]:
            print(f"  · sifra={m['sifra']:<10} cover={m['cover']:<40} {m.get('issue','?')}")
            print(f"    {m['name'][:80]}")


if __name__ == "__main__":
    asyncio.run(main())
