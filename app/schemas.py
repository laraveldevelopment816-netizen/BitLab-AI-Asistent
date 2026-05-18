"""
JSON shema za strukturisani AI output (chat widget) — STATUS kartica srcv.

Tri tipa odgovora (discriminated union po `type` polju):
- `products` — pretraga vrati 1+ proizvoda
- `empty` — pretraga vratila 0 rezultata (eksplicitno polje, ne ad-hoc null)
- `message` — sve van pretrage (pozdrav, FAQ, eskalacija, pojašnjenje)

Pydantic modeli su single source of truth — validiraju AI output prije nego
ga propagiraju u widget. JSON Schema export preko `.model_json_schema()` ili
`assistant_response_adapter.json_schema()`.

Polja proizvoda preslikana 1:1 sa onim što `rag.search()` već vraća
(`app/rag.py:423-430`): `sifra`, `name`, `price_km`, `availability`, `url`,
`image_url`. Bez derivata (`in_stock`, `kolicina`) — nije dio postojećeg
toka, ne dodaje se.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class Product(BaseModel):
    """Jedan proizvod u listi rezultata pretrage."""

    sifra: str = Field(min_length=1, description="Šifra proizvoda iz kataloga.")
    name: str = Field(min_length=1, description="Naziv proizvoda.")
    price_km: float = Field(ge=0, description="Cijena u KM (broj, ne string).")
    availability: str = Field(
        min_length=1,
        description="Tekstualni status: 'Na lageru' / 'Dobavljivo po narudžbi' / itd.",
    )
    url: str = Field(min_length=1, description="URL ka detaljnoj stranici proizvoda na webshopu.")
    image_url: str | None = Field(
        description="URL slike proizvoda, ili null kad slika nedostaje (legacy/missing iz audit-a).",
    )


class ProductsResponse(BaseModel):
    """Pretraga je vratila 1+ proizvoda."""

    type: Literal["products"]
    text: str = Field(description="Tekstualni okvir oko liste (intro + opcionalan follow-up).")
    products: list[Product] = Field(
        min_length=1,
        description="Lista proizvoda. Min 1 — za 0 rezultata koristi EmptyResponse.",
    )


class EmptyResponse(BaseModel):
    """Pretraga vratila 0 rezultata — eksplicitno odvojeno od products sa praznom listom."""

    type: Literal["empty"]
    message: str = Field(min_length=1, description="Korisniku-čitljiva poruka da nema rezultata.")


class MessageResponse(BaseModel):
    """Sve van pretrage — pozdrav, FAQ, eskalacija, pojašnjenje."""

    type: Literal["message"]
    content: str = Field(min_length=1, description="Tekst poruke (markdown dozvoljen).")


# Discriminated union — TypeAdapter eksponira validate_python / validate_json /
# json_schema za potrošače. Diskriminator `type` daje fail-fast sa jasnom
# greškom kad AI vrati nepoznat tip umjesto silent fallback-a.
AssistantResponse = Annotated[
    Union[ProductsResponse, EmptyResponse, MessageResponse],
    Field(discriminator="type"),
]

assistant_response_adapter: TypeAdapter[AssistantResponse] = TypeAdapter(AssistantResponse)
