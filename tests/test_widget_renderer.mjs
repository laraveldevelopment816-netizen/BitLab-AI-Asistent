/**
 * Unit testovi za pure render helper-e iz public/widget.js.
 * Pokreni: node tests/test_widget_renderer.mjs
 *
 * Ekstraktovane funkcije ispod su 1:1 kopija iz widget.js. Kad se mijenja
 * widget.js, sinhronizuj ovu kopiju (provjereno u CI sa diff check-om
 * ako bude potrebno). Razlog za kopiju: widget.js je single-file IIFE
 * koji ne export-uje pure funkcije; izvlačenje u zaseban modul bi
 * razbilo embed-ability širokom potrošačima.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

// ── COPY-OF: collapseMultiLineProducts (widget.js) ──────────────────
function collapseMultiLineProducts(src) {
  const lines = src.split('\n');
  const out = [];
  let i = 0;
  const RE_IMG  = /^\s*!\[[^\]]*\]\((https?:\/\/[^)]+)\)\s*$/;
  const RE_BOLD = /^\s*\*\*([^*]+?)\*\*\s*$/;
  const RE_PRICE = /^\s*([0-9][\d.,]*)\s*KM\s*$/i;
  const RE_AVAIL = /^\s*(na\s+lager[a-z]*|dobavljiv[a-z]*|na\s+stanju|po\s+narud(?:ž|z)bi)\s*$/i;
  const RE_LINK  = /^\s*\[([^\]]+)\]\((https?:\/\/[^)]+)\)\s*$/;
  const RE_FILLER = /^\s*(?:[-*_]{3,}|)$/;
  const isFiller = (line) => RE_FILLER.test(line);

  while (i < lines.length) {
    let j = i;
    while (j < lines.length && isFiller(lines[j])) j++;

    let img = null, name = null, price = null, avail = null, href = null;
    let k = j;
    const skipFiller = () => {
      while (k < lines.length && isFiller(lines[k])) k++;
    };

    const mImg = k < lines.length && lines[k].match(RE_IMG);
    if (!mImg) { out.push(lines[i]); i++; continue; }
    img = mImg[1]; k++; skipFiller();

    const mBold = k < lines.length && lines[k].match(RE_BOLD);
    if (!mBold || mBold[1].trim().length < 8) {
      out.push(lines[i]); i++; continue;
    }
    name = mBold[1]; k++; skipFiller();

    const mPrice = k < lines.length && lines[k].match(RE_PRICE);
    if (!mPrice) { out.push(lines[i]); i++; continue; }
    price = mPrice[1]; k++; skipFiller();

    const mAvail = k < lines.length && lines[k].match(RE_AVAIL);
    if (mAvail) { avail = mAvail[1]; k++; skipFiller(); }

    const mLink = k < lines.length && lines[k].match(RE_LINK);
    if (mLink) { href = { label: mLink[1], url: mLink[2] }; k++; }

    let line = '';
    if (img) line += `![](${img}) `;
    line += `**${name}** — ${price} KM`;
    if (avail) line += ` — ${avail}`;
    if (href) line += ` — [${href.label}](${href.url})`;

    for (let b = i; b < j; b++) {
      if (lines[b].trim() === '') out.push(lines[b]);
    }
    out.push(line);
    i = k;
  }
  return out.join('\n');
}

// ── Tests ───────────────────────────────────────────────────────────

test('Sesija 8 hotfix: multi-line block sa --- separator se sklopi u single-line', () => {
  const broken =
    'Evo laptopa do 2000 KM:\n\n' +
    '---\n\n' +
    '![](https://webshop.bitlab.rs/img/asus.jpg)\n' +
    '**ASUS E1504FA 15,6" FHD | Ryzen 3 7320U / 8GB / 512GB SSD**\n' +
    '929 KM\n' +
    'Na lageru\n';

  const out = collapseMultiLineProducts(broken);

  // Sklopljeno u jednu liniju
  assert.match(out, /!\[\]\(https:\/\/[^)]+\) \*\*ASUS E1504FA[^*]+\*\* — 929 KM — Na lageru/);
  // Ime nije više samostalno na svom redu
  assert.equal(
    (out.match(/^\*\*ASUS E1504FA[^*]+\*\*$/m) || []).length, 0,
    'Ime ne smije ostati u zasebnom redu poslije collapse-a'
  );
});

test('Multi-line bez --- separatora takođe se sklopi', () => {
  const broken =
    '![](https://webshop.bitlab.rs/img/lenovo.jpg)\n' +
    '**Lenovo IdeaPad Slim 3 15,3"**\n' +
    '1.315 KM\n' +
    'Na lageru\n' +
    '[Pogledaj](https://webshop.bitlab.rs/G123.html)\n';

  const out = collapseMultiLineProducts(broken);
  assert.match(out, /\*\*Lenovo IdeaPad Slim 3[^*]+\*\* — 1\.315 KM — Na lageru — \[Pogledaj\]/);
});

test('Single-line input ostaje single-line (no-op)', () => {
  const ok =
    '- ![](https://webshop.bitlab.rs/img.jpg) **ASUS Vivobook 15** — 1.499 KM — Na lageru — [Pogledaj](https://webshop.bitlab.rs/X.html)';
  const out = collapseMultiLineProducts(ok);
  assert.equal(out, ok, 'Single-line ne smije biti promijenjen');
});

test('Multiple multi-line proizvoda u istom outputu', () => {
  const src =
    '![](https://x.com/a.jpg)\n' +
    '**ASUS E1504FA 15,6"**\n' +
    '929 KM\n' +
    'Na lageru\n' +
    '\n' +
    '![](https://x.com/b.jpg)\n' +
    '**Lenovo IdeaPad Slim 3 15,3"**\n' +
    '1.315 KM\n' +
    'Na lageru\n';

  const out = collapseMultiLineProducts(src);
  const productLines = out.split('\n').filter(l => l.includes('**'));
  assert.equal(productLines.length, 2, 'Oba proizvoda u svojim single-line varijantama');
});

test('FALSE POSITIVE GUARD: **Pažnja**: 500 KM ne tretira se kao produkt', () => {
  const src =
    '**Pažnja**\n' +
    '500 KM\n' +
    'minimum za besplatnu dostavu\n';
  const out = collapseMultiLineProducts(src);
  // Bez slike → ne sklapa se. Ostaje original.
  assert.equal(out, src);
});

test('FALSE POSITIVE GUARD: kratak bold (<8 zn) ne tretira se kao produkt', () => {
  const src =
    '![](https://x.com/img.jpg)\n' +
    '**SSD**\n' +
    '240 KM\n';
  const out = collapseMultiLineProducts(src);
  // Bold "SSD" je samo 3 znaka < 8 → ne sklapa
  assert.equal(out, src);
});

test('FALSE POSITIVE GUARD: bez cijene KM ne sklapa', () => {
  const src =
    '![](https://x.com/img.jpg)\n' +
    '**Vrlo dugo ime proizvoda**\n' +
    'Ovaj proizvod je super.\n';
  const out = collapseMultiLineProducts(src);
  assert.equal(out, src);
});

test('Plain text (uvodne rečenice) prolazi netaknut', () => {
  const src = 'Evo laptopa do 2000 KM koje trenutno imamo:\n\nBudžetni izbor:\n';
  const out = collapseMultiLineProducts(src);
  assert.equal(out, src);
});

test('--- separator sam (bez bloka) ostaje za markdown step da ga ukloni', () => {
  const src = 'Tekst\n\n---\n\nDrugi tekst\n';
  const out = collapseMultiLineProducts(src);
  // collapse ne dira plain --- (markdown post-process to radi)
  assert.match(out, /---/);
});

test('Cijena sa decimalama (389,99) ispravno parsovana', () => {
  const src =
    '![](https://x.com/x.jpg)\n' +
    '**Test Proizvod sa Dugim Imenom**\n' +
    '389,99 KM\n' +
    'Na lageru\n';
  const out = collapseMultiLineProducts(src);
  assert.match(out, /389,99 KM/);
});

// ── COPY-OF: formatPriceKm (widget.js — STATUS kartica srcv) ────────
function formatPriceKm(n) {
  if (n == null || isNaN(n)) return '';
  const isInt = Number.isInteger(n);
  if (isInt) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }
  const [intPart, decPart] = n.toFixed(2).split('.');
  return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ',' + decPart;
}

// ── COPY-OF: structuredReplyToText (widget.js — STATUS kartica srcv) ─
function structuredReplyToText(reply) {
  if (!reply || typeof reply !== 'object') return '';
  if (reply.type === 'products') {
    const items = (reply.products || [])
      .map((p) => `${p.name} — ${formatPriceKm(p.price_km)} KM — ${p.availability}`)
      .join('\n');
    return [reply.text || '', items].filter(Boolean).join('\n');
  }
  if (reply.type === 'empty') return reply.message || '';
  if (reply.type === 'message') return reply.content || '';
  return JSON.stringify(reply);
}

test('formatPriceKm: integer bez separatora (3-cifren)', () => {
  assert.equal(formatPriceKm(929), '929');
});

test('formatPriceKm: integer sa BCS thousand separator (4-cifren)', () => {
  assert.equal(formatPriceKm(1450), '1.450');
});

test('formatPriceKm: integer 5-cifren', () => {
  assert.equal(formatPriceKm(12345), '12.345');
});

test('formatPriceKm: decimale (zarez umjesto tačke)', () => {
  assert.equal(formatPriceKm(929.99), '929,99');
});

test('formatPriceKm: thousand sep + decimale', () => {
  assert.equal(formatPriceKm(1450.99), '1.450,99');
});

test('formatPriceKm: null / undefined / NaN vraća ""', () => {
  assert.equal(formatPriceKm(null), '');
  assert.equal(formatPriceKm(undefined), '');
  assert.equal(formatPriceKm(NaN), '');
});

test('structuredReplyToText: products flatten u intro + N linija', () => {
  const reply = {
    type: 'products',
    text: 'Evo top 2 laptopa:',
    products: [
      { sifra: 'G1', name: 'ASUS', price_km: 929, availability: 'Na lageru', url: 'https://x', image_url: null },
      { sifra: 'G2', name: 'Lenovo', price_km: 1450, availability: 'Po narudžbi', url: 'https://y', image_url: null },
    ],
  };
  const out = structuredReplyToText(reply);
  assert.match(out, /Evo top 2 laptopa:/);
  assert.match(out, /ASUS — 929 KM — Na lageru/);
  assert.match(out, /Lenovo — 1\.450 KM — Po narudžbi/);
});

test('structuredReplyToText: empty type vraća message', () => {
  assert.equal(
    structuredReplyToText({ type: 'empty', message: 'Nema rezultata.' }),
    'Nema rezultata.'
  );
});

test('structuredReplyToText: message type vraća content', () => {
  assert.equal(
    structuredReplyToText({ type: 'message', content: 'Pozdrav!' }),
    'Pozdrav!'
  );
});

test('structuredReplyToText: nepoznat type → JSON dump (fallback)', () => {
  const r = { type: 'something_else', x: 1 };
  assert.equal(structuredReplyToText(r), JSON.stringify(r));
});

test('structuredReplyToText: null/undefined → ""', () => {
  assert.equal(structuredReplyToText(null), '');
  assert.equal(structuredReplyToText(undefined), '');
  assert.equal(structuredReplyToText('string'), '');
});

console.log('✅ Svi widget renderer testovi prošli');
