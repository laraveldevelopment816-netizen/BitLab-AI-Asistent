# Gmail OAuth setup za n8n — autoreply workflow

Cilj: povezati Gmail nalog (od BitLab-a) sa n8n workflow-om `email-autoreply` da live testiramo AI auto-reply na pristigle email-ove.

Trajanje: ~10-15 min. Sve se radi u browser-u na dvije strane: **Google Cloud Console** + **n8n UI**.

---

## Šta već imamo

- ✅ n8n staging live: **https://staging.aiasistent.bitlab.rs/n8n/**
- ✅ n8n prod live: **https://aiasistent.bitlab.rs/n8n/**
- ✅ Workflow JSON pripremljen: `n8n/email-autoreply.json`
- ✅ HTTP request URL u workflow-u parametrizovan kroz `AI_ASSISTANT_URL` env var (ne treba editovati nakon import-a)

OAuth Redirect URL koji n8n traži:

| Environment | Redirect URI |
|---|---|
| Staging | `https://staging.aiasistent.bitlab.rs/n8n/rest/oauth2-credential/callback` |
| Production | `https://aiasistent.bitlab.rs/n8n/rest/oauth2-credential/callback` |

---

## Korak 1 — Google Cloud Console: project + Gmail API

1. Otvori https://console.cloud.google.com (login sa Gmail nalogom koji će workflow koristiti — npr. `bitlab.support@gmail.com` ili koji god BitLab koristi za sales/support).
2. Top-left: **Select a project → New Project**.
   - Name: `BitLab n8n`
   - Organization: ostavi default (ako pita)
   - Klikni **Create**, sačekaj ~10s da se project kreira, pa ga selektuj.
3. Lijeva navigacija: **APIs & Services → Library**.
4. Pretraži **"Gmail API"** → klik na rezultat → **Enable**. Sačekaj 2-3 sekunde dok ne kaže "API enabled".

---

## Korak 2 — OAuth consent screen

1. Lijeva navigacija: **APIs & Services → OAuth consent screen**.
2. **User Type:** **External** (jer koristimo public Gmail nalog) → **Create**.
3. **App information:**
   - App name: `BitLab AI Asistent — n8n`
   - User support email: tvoj Gmail
   - App logo: skip (opciono)
4. **App domain (opciono):** prazno za sad.
5. **Authorized domains:** dodaj `bitlab.rs` (klikni **+ Add domain**).
6. **Developer contact information:** tvoj Gmail.
7. **Save and Continue**.

### Scopes

8. Klik **Add or Remove Scopes**.
9. U pretragu kucaj `gmail` i čekiraj:
   - `https://www.googleapis.com/auth/gmail.modify` (čitanje + označavanje pročitanih)
   - `https://www.googleapis.com/auth/gmail.send` (slanje odgovora)
10. **Update → Save and Continue**.

### Test users

11. **Test users → + Add Users → email** koji ćemo koristiti za testiranje (možeš dodati i svoj `bjovkovic@gmail.com` da brže testiraš).
   - Tokom **Testing** statusa (default), samo ovi korisnici mogu OAuth-ovati. Za prod produkciju kasnije ide submit za **Verification** (proces traje 4-6 nedelja, ne hitamo).
12. **Save and Continue → Back to Dashboard**.

> Ostavljamo Publishing status na **Testing** za sad — to je OK za interno korišćenje.

---

## Korak 3 — Create OAuth 2.0 Client ID

1. Lijeva navigacija: **APIs & Services → Credentials**.
2. **+ Create Credentials → OAuth client ID**.
3. **Application type:** **Web application**.
4. **Name:** `n8n staging` (kasnije ćemo isti flow proći za prod, posebno OAuth client).
5. **Authorized redirect URIs → + Add URI:**

   ```
   https://staging.aiasistent.bitlab.rs/n8n/rest/oauth2-credential/callback
   ```

   > ⚠️ Bukvalno ovaj URL — trailing `callback` bez `/`, sa `/n8n/` u path-u. Ako pogriješiš makar jedan karakter, OAuth flow vraća error.

6. **Create**.
7. Pojavi se modal sa **Client ID** i **Client secret** — kopiraj oba (možeš ih kasnije čitati iz Credentials liste).

---

## Korak 4 — n8n UI: paste credentials

1. Otvori https://staging.aiasistent.bitlab.rs/n8n/ (već si tu — modalni prozor "Setup credential" na slici).
2. **Connection** tab (već si tu):
   - **Client ID:** paste iz Google Cloud Console
   - **Client Secret:** paste
   - **Allowed HTTP Request Domains:** ostavi `All`
3. Klik **Sign in with Google** dugme dole.
4. Otvori se Google OAuth popup:
   - Login sa Gmail nalogom **koji je dodat kao test user** (Korak 2.11)
   - Google će pokazati: **"BitLab AI Asistent — n8n wants access to your Google Account"**
   - Klikni **Continue** (može biti warning jer app nije verified — to je očekivano za testing)
   - Odobri scope-ove (`gmail.modify`, `gmail.send`)
5. Vrati se na n8n tab — modal kaže **"Account connected"** ili sl.
6. **Save** (gore desno) → **Close**.

---

## Korak 5 — Configure Gmail Trigger node

1. U workflow-u (već si na njega kliknuo gore), otvori **Gmail Trigger** node.
2. **Credential to connect with:** dropdown → izaberi **`Gmail account`** (taj koji si upravo kreirao).
3. **Poll Times:** ostavi **Every Minute** (default iz workflow-a).
4. **Filters → Include Spam/Trash:** off (default).
5. **Test step** dugme dole — pokreće trigger jednom da provjeri da li čita inbox. Ako prvi test prođe (ne mora biti email u inbox-u, samo da n8n može da pristupi Gmail-u), node je OK.

---

## Korak 6 — Configure Gmail Send node ("Pošalji AI Reply")

1. Otvori **Gmail: Pošalji AI Reply** node.
2. **Credential to connect with:** isti `Gmail account`.
3. Ostala polja (`To`, `Subject`, `Message`, `emailType: html`) već dolaze iz import-a — ne diraj.

---

## Korak 7 — Activate workflow + smoke test

1. **Save** workflow (gore desno).
2. Toggle **Active** (gore desno) → workflow je sad live, polluje Gmail svake minute.
3. **Smoke test:**
   - Pošalji email na povezani Gmail nalog **iz drugog email-a** (npr. tvoje `bjovkovic@gmail.com` šalje na `bitlab.support@gmail.com`).
   - Subject mora sadržati neki od ključnih pojmova: `upit`, `ponuda`, `cijen`, `dostava`, `garancija`, `kako`, `imate li`, `trebam`, `kupiti`, `narudžba`. (IF node u workflow-u filtrira po ovome.)
   - Body — tijelo upita (npr. "Imate li u ponudi Apple iPhone 16, koliko kosta?")
4. Sačekaj ~60s (poll interval) → AI reply stiže nazad u inbox.

---

## Troubleshooting

**OAuth error "redirect_uri_mismatch":**
- Provjeri da Authorized redirect URI u Google Cloud Console **bukvalno** odgovara onome što n8n pokazuje (uključujući `/n8n/` u path-u).
- Ako si dodao staging URI a sad si na prod URL-u, treba poseban OAuth client za prod.

**OAuth radi ali Gmail Trigger ne čita email:**
- Provjeri da Gmail nalog koji si OAuth-ovao **isto** prima email-ove (ne neki drugi nalog u browser session-u).
- `Test step` na Gmail Trigger-u — vidi error message u UI.

**Workflow se aktivira ali nema reply:**
- Otvori workflow → **Executions** tab dole — vidiš svaki run-up sa status-om.
- Ako IF node skida sve → subject ne sadrži ključnu riječ.
- Ako HTTP node puca → vjerovatno `AI_ASSISTANT_URL` nije postavljen ili FastAPI app ne radi. Provjeri:

  ```bash
  ssh ai@staging.aiasistent.bitlab.rs 'curl -sf http://127.0.0.1:8001/healthz'
  # Mora vratiti JSON sa products_index_present:true
  ```

**Logovi n8n servisa (na server-u):**

```bash
ssh ai@staging.aiasistent.bitlab.rs 'sudo journalctl -u n8n-staging -f'
```

---

## Prod isto, kasnije

Kad staging odradi par successful run-ova, ponavljaš Korake 3-7 za prod:

1. U Google Cloud Console (isti project): **+ Create Credentials → OAuth client ID** → name `n8n prod` → redirect URI:

   ```
   https://aiasistent.bitlab.rs/n8n/rest/oauth2-credential/callback
   ```

2. U **prod** n8n UI (https://aiasistent.bitlab.rs/n8n/): kreiraj owner account, importuj isti `n8n/email-autoreply.json`, paste prod Client ID/Secret, sign in, activate.

> Možeš koristiti **isti Gmail nalog** (samo OAuth client je drugi) — workflow će samo poslati reply iz povezanog naloga.

---

## Kad dođe DNS (Rale objavi A rekorde)

Subpath URL-ovi će i dalje raditi (ostavljamo backward-compat). Ali ako želiš preći na čistu subdomenu:

1. U Google Cloud Console: **OAuth client → Authorized redirect URIs → + Add URI** sa novim URL-om:
   - `https://n8n-staging.bitlab.rs/rest/oauth2-credential/callback`
   - `https://n8n.bitlab.rs/rest/oauth2-credential/callback`
2. Sačuvaj. Stari subpath URI ostavi paralelno dok ne migriraš sve workflow-e.
3. Migracioni koraci na server strani su u [`n8n-odluka.md`](./n8n-odluka.md) sekcija "Migracija subpath → subdomena".

---

## Reference

- n8n Gmail Trigger node docs: https://docs.n8n.io/integrations/builtin/credentials/google/oauth-generic/
- Google Cloud OAuth setup: https://developers.google.com/identity/protocols/oauth2/web-server
- Workflow JSON: [`n8n/email-autoreply.json`](../../n8n/email-autoreply.json)
- Server setup detalji: [`n8n-setup.md`](./n8n-setup.md)
- Plan + odluke: [`n8n-odluka.md`](./n8n-odluka.md)
