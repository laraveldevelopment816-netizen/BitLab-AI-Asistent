# Notes — bitlab-ai-asistent

Inbox za napomene, zapažanja i zanimljivosti kroz projekat. **Sirovo** — ne mora biti destilovano.
Kad napomena sazri u pravu lekciju sa poentom, prelazi u [`lessons-learned.md`](lessons-learned.md).

---

- 2026-06-07 — **Kontradikcija sample vs full koju treba držati na umu:** [`ralph/AGENTS.md`](../../ralph/AGENTS.md):64 i [`EVAL_OPTIMIZACIJA.md`](../archives/EVAL_OPTIMIZACIJA.md) Q1#2 preporučuju `--mode sample` (46 poziva) kao default za iteraciju, ALI lekcija [L1](lessons-learned.md) (iter17) pokazuje da je sample dao lažni zeleni 93–100% dok je pun set bio 79%. Pravilo: sample za brzu fail-pattern detekciju OK, ali **gate uvijek na punom** (ili sample koji eksplicitno uključuje teške leaf slučajeve).

<!-- Dodavaj odozdo, jedna napomena = jedan bullet, sa datumom. Primjer:
- 2026-06-07 — random `--mode sample` eval laže: 93–100% na sample-u dok je pun set 79%. Gate uvijek na punom (ili stratifikovanom koji uključuje teške slučajeve).
-->
