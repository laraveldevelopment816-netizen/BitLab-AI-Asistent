# Design Patterns Primjena: Od CM Scraperа do BitLab AI Asistenta

---

## Zašto svaki pattern — u jednoj rečenici

**Pipeline pattern:** Kad dodaš novi korak u obradu (npr. transliteracija prije ekstrakcije), bez pipeline-a moraš tražiti gdje da ga ubaciti u monolitnoj funkciji i bojati se šta ćeš pokvariti; sa pipeline-om dodaš jednu klasu i jedan red u `build_pipeline()` — gotovo.

**Factory pattern:** Bez factory-ja svaki pozivač koji hoće pipeline mora znati koje Stage-ove da instancira i kojim redom — sa `build_pipeline()` postoji jedno mjesto u cijelom sistemu gdje se mijenja sklapanje, i ništa drugo ne treba da zna za to.

**Chain of Responsibility (RunModelsStage):** Umjesto da unaprijed odlučiš koji model ćeš koristiti i platiš uvijek najskuplji, lanac proba jeftinijeg prvog — ako je dovoljno dobar, staje i ne plaća skupljeg; skupi model se zove samo kad treba.

**AgentLoop (za BitLab Asistenta):** Sad isti tool-loop postoji na dva mjesta (`_run_anthropic` i `_run_pwr`) — 130 linija duplikata koje moraš ažurirati na dva mjesta kad god promijeniš logiku; `AgentLoop` ga svodi na jedno.

**Context Object (PipelineContext):** Umjesto da svaki Stage prima 10 parametara i mora znati šta prethodni Stage radio, jedan objekat putuje kroz cijeli lanac i svako čita samo šta mu treba i piše samo šta je njegovo — dodavanje novog podatka = jedno novo polje.

---

## 1. Lekcija iz CM Scraperа: Put od Haosa do Elegancije

### 1.1 Problem: HaikuBrowserClient i "God Object" anti-pattern

`haiku/browser.py` ima 438 linija i jedan method `wait_for_response()` sa 160 linija koji radi sve:

```python
# haiku/browser.py — PROBLEM: trofazni state machine u jednoj metodi
def wait_for_response(self) -> str:
    page = self._ensure_page()
    pre_count = self._pre_send_count
    msg_selector = 'div[class*="markdown"]'
    stop_selector = 'button[aria-label*="Stop"], button:has-text("Stop")'

    start_time = time.time()
    elapsed = lambda: time.time() - start_time
    max_secs = self.timeout / 1000
    _MIN_WAIT = 90  # magic number: zakopan u tijelu metode

    # Phase 1: ceka da se pojavi AI response div
    target = pre_count + 2
    while elapsed() < max_secs:
        page.wait_for_timeout(3000)   # polling svake 3s
        # ... usage limit check, count check, break ...

    ai_appeared_at = elapsed()

    # Phase 2: prati stop button (appear -> disappear = streaming gotov)
    streaming_seen = False
    while elapsed() < max_secs:
        page.wait_for_timeout(1000)
        # ... stop_visible logika, streaming_seen toggle ...

    # Phase 3: text stability + minimum wait enforcement
    last_text = ""
    stable_count = 0
    while elapsed() < max_secs:
        page.wait_for_timeout(3000)
        # ... stable_count, _MIN_WAIT provjera ...
        if stable_count >= 3 and time_since_ai >= _MIN_WAIT:
            return current_text
```

**Konkretan popis problema:**
- Tri `while` petlje sa tri razlicita izlazna uslova u jednoj metodi
- `_MIN_WAIT = 90` je magic number zakopan u tijelu — ne moze se konfigurirati izvana
- Fundamentalni anti-pattern: cijeli `haiku/` modul scrape-uje `claude.ai` browser UI umjesto da koristi `anthropic` SDK
- `haiku/db_writer.py` vraca `act_type='haiku_parsed'` koji nije u `ActType` enumu — zaobilazi type sistem
- Copy-paste duplikacija: `_split_into_acts` i `_is_act_start` postoje u i `GazettePdfParser` i `PropisiPdfParser`

### 1.2 Koji Patereni su Riješili Problem

**Pipeline** je zamijenio monolitni `cmd_run` (195 linija jedne funkcije) sa 7 Stage klasa od ~30 linija svaka.

**Factory** (`build_pipeline()`) je jedino mjesto gdje se Stage instanciraju — `Pipeline` zna samo za `Stage` protokol.

**Chain of Responsibility** je unutar `RunModelsStage` — modeli se probaju redom dok jedan ne prode prag.

### 1.3 Vizualna Dijagram Razlika

```
STARO (cm-scraper-v0)
=====================

app.py (107 redova)
      |
      +-- FastAPI + CORS + ScraperScheduler + router mount + pub/sub config
                                                    |
                              +---------------------+---------------------+
                              |                     |                     |
                      documents.py          haiku/browser.py        core/pdf_parser.py
                              |             (438 linija)                  |
                    (inline StorePipeline    |                    _split_into_acts()
                     + AnalyzerWebhook)      |                         [DUPLIKAT]
                                    wait_for_response()           core/propisi_parser.py
                                    (160 linija)                        |
                                    [Phase 1]                   _split_into_acts()
                                    [Phase 2]                        [DUPLIKAT]
                                    [Phase 3]
                                    [magic _MIN_WAIT=90]
                                    [DOM polling]


NOVO (cm-scraper)
=================

factory.py::build_pipeline()
      |
      v
Pipeline([
    PrepareTextStage(),    ~30 LOC  -- PDF -> tekst, samo to
    BuildPromptStage(),    ~30 LOC  -- tekst -> prompt, samo to
    RunModelsStage(),      ~40 LOC  -- chain: model1 -> model2 -> break@threshold
    ArbiterStage(),        ~20 LOC  -- eskalacija ako threshold nije dostignuta
    FinalizeStage(),       ~20 LOC  -- bira pobjednika po score-u
    SaveStage(),           ~25 LOC  -- disk write, samo to
    ReportStage(),         ~20 LOC  -- izvjestaj, samo to
])
      |
      v
PipelineContext (jedini objekt koji putuje kroz sve faze)

      RunModelsStage unutrasnji Chain of Responsibility:
      model1.run(ctx) -> score >= threshold? -> BREAK (gotovo)
                      -> score <  threshold? -> NEXT
      model2.run(ctx) -> score >= threshold? -> BREAK
                      -> svi pali          -> StageError(fatal=False)
                      -> ArbiterStage dobija sansu
```

---

## 2. Pattern Priručnik: Pipeline, Factory, Chain of Responsibility

### 2.1 Pipeline Pattern

**Kada ga koristis — signali u kodu:**
- Imas jednu monolitnu funkciju koja prolazi kroz jasne korake (extract → transform → load, ili: pripremi → pozovi → validiraj → sacuvaj)
- Koraci imaju prirodan redoslijed, izlaz jednog je ulaz sljedeceg
- Hoces da dodas novi korak bez dodirivanja postojecih
- Hoces `stop_after="BuildPromptStage"` za debug bez mijenjanja logike

**Implementacioni predlozak:**

```python
# protocols.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class Stage(Protocol):
    name: str
    def run(self, ctx: "PipelineContext") -> "PipelineContext": ...


class StageError(Exception):
    def __init__(self, msg: str, *, fatal: bool = True):
        super().__init__(msg)
        self.fatal = fatal


# pipeline.py
import time

class Pipeline:
    def __init__(self, stages: list[Stage]) -> None:
        self.stages = stages

    def run(
        self,
        ctx: "PipelineContext",
        *,
        stop_after: str | None = None,
    ) -> "PipelineContext":
        for stage in self.stages:
            start = time.perf_counter()
            fatal = False
            try:
                ctx = stage.run(ctx)
            except StageError as exc:
                if exc.fatal:
                    ctx.errors.append(f"{stage.name}: {exc}")
                    fatal = True
                else:
                    ctx.warnings.append(f"{stage.name}: {exc}")
            except Exception as exc:
                ctx.errors.append(f"{stage.name}: {exc}")
                fatal = True
            else:
                ctx.completed_stages.append(stage.name)
            finally:
                ctx.timings[stage.name] = time.perf_counter() - start

            if fatal:
                break
            if stop_after is not None and stage.name == stop_after:
                break
        return ctx


# Konkretna stage klasa — template
class PrepareTextStage:
    name = "prepare_text"

    def run(self, ctx: "PipelineContext") -> "PipelineContext":
        # Jedna odgovornost: PDF -> tekst
        # Ako nesto krene krivo:
        #   raise StageError("PDF nije citan", fatal=True)   # prekida pipeline
        #   raise StageError("Prazan tekst", fatal=False)    # upozorenje, nastavlja
        ctx.prepared_text = extract_text(ctx.pdf_path)
        return ctx
```

**Primjer iz CM Scrapera (stvarni kod):**

```python
# cm-scraper/pipeline/factory.py
def build_pipeline() -> Pipeline:
    return Pipeline([
        PrepareTextStage(),
        BuildPromptStage(),
        RunModelsStage(),
        ArbiterStage(),
        FinalizeStage(),
        SaveStage(),
        ReportStage(),
    ])

def run_pdf(pdf_path: str | Path, models: list[str] | None = None) -> PipelineContext:
    models = build_models(models)
    ctx = PipelineContext(
        pdf_path=Path(pdf_path),
        config=PipelineConfig(models=models, writer="versioned", enable_report=True),
    )
    return build_pipeline().run(ctx)
```

Dodavanje novog koraka (npr. `ValidateOutputStage`) je bukvalno jedan red u `build_pipeline()` — nista drugo se ne mijenja.

---

### 2.2 Factory Pattern

**Kada ga koristis — signali u kodu:**
- Imas `if backend == "anthropic": ... elif backend == "pwr": ...` rasut po kodu na vise mjesta
- Kreiranje objekta je kompleksno (vise zavisnosti, konfiguracija, inicijalizacija)
- Hoces da zamijenis implementaciju bez dodirivanja klijentskog koda
- `isinstance()` provjere se mnozavaju

**Implementacioni predlozak:**

```python
# abstractions.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AgentResult:
    reply: str
    tool_calls: list[dict]
    iterations: int


class AbstractLLMBackend(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict]) -> AgentResult: ...


# backends/anthropic_backend.py
class AnthropicBackend(AbstractLLMBackend):
    def __init__(self, api_key: str, model: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> AgentResult:
        # Anthropic-specific implementacija
        ...


# backends/pwr_backend.py
class PWRBackend(AbstractLLMBackend):
    def __init__(self, base_url: str, api_key: str, model: str):
        import openai
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> AgentResult:
        # PWR/OpenAI-compatible implementacija
        ...


# factory.py
def create_llm_backend(settings: "Settings") -> AbstractLLMBackend:
    if settings.use_pwr:
        return PWRBackend(
            base_url=settings.pwr_base_url,
            api_key=settings.pwr_api_key,
            model=settings.model,
        )
    return AnthropicBackend(
        api_key=settings.anthropic_api_key,
        model=settings.model,
    )
```

**Primjer iz CM Scrapera (factory kao slobodna funkcija):**

```python
# cm-scraper/pipeline/factory.py
# Factory ne mora biti klasa — slobodna funkcija je dovoljna

def build_pipeline() -> Pipeline:
    """Jedino mjesto gdje se Stage klase instantiraju."""
    return Pipeline([
        PrepareTextStage(),
        BuildPromptStage(),
        RunModelsStage(),   # interno koristi _resolve_provider() za per-model factory
        ArbiterStage(),
        FinalizeStage(),
        SaveStage(),
        ReportStage(),
    ])

# Pipeline.run() ne zna da postoji PrepareTextStage.
# Zna samo za Stage protokol: name: str + run(ctx) -> ctx.
# To je Factory u akciji: instantiranje je odvojeno od koristenja.
```

---

### 2.3 Chain of Responsibility Pattern

**Kada ga koristis — signali u kodu:**
- Imas `if tool_name == "a": ... elif tool_name == "b": ... elif tool_name == "c": ...`
- Hoces da svaki handler sam odluci da li je nadlezan
- Redoslijed handlera je bitan (od specificnog ka generickom)
- Hoces da dodas novi handler bez dodirivanja postojecih

**Implementacioni predlozak:**

```python
# chain.py
from abc import ABC, abstractmethod
from typing import Optional

class ToolHandler(ABC):
    def __init__(self):
        self._next: Optional["ToolHandler"] = None

    def set_next(self, handler: "ToolHandler") -> "ToolHandler":
        self._next = handler
        return handler  # omogucava chaining: a.set_next(b).set_next(c)

    @abstractmethod
    def handle(self, tool_name: str, args: dict) -> str | None:
        """Vrati string rezultat ili None ako nisi nadlezan."""
        ...

    def _delegate(self, tool_name: str, args: dict) -> str | None:
        if self._next:
            return self._next.handle(tool_name, args)
        return None  # kraj lanca, niko nije obradio


class CatalogToolHandler(ToolHandler):
    HANDLED = {"category_overview", "search_products"}

    def handle(self, tool_name: str, args: dict) -> str | None:
        if tool_name not in self.HANDLED:
            return self._delegate(tool_name, args)
        return dispatch_catalog(tool_name, args)  # obradi


class RespondToUserHandler(ToolHandler):
    def handle(self, tool_name: str, args: dict) -> str | None:
        if tool_name != "respond_to_user":
            return self._delegate(tool_name, args)
        return args.get("message", "")


class FallbackHandler(ToolHandler):
    def handle(self, tool_name: str, args: dict) -> str | None:
        # Uvijek obradi — genericka greska
        return f"Nepoznati tool: {tool_name}"


# Sklapanje lanca
def build_tool_chain() -> ToolHandler:
    catalog = CatalogToolHandler()
    respond = RespondToUserHandler()
    fallback = FallbackHandler()
    catalog.set_next(respond).set_next(fallback)
    return catalog

# Koristenje
chain = build_tool_chain()
result = chain.handle("category_overview", {"category_id": "abc"})
```

**Primjer iz CM Scrapera (Chain unutar RunModelsStage):**

```python
# cm-scraper/pipeline/stages/run_models.py
# Unutrasnji CoR: probaj modele redom dok jedan ne prode prag

class RunModelsStage:
    name = "run_models"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        for model_id in ctx.config.models:      # lista = redoslijed lanca
            provider, model = _resolve_provider(model_id)
            output, greska = call_model(ctx.prompt, provider, model)
            mr = ModelResult(provider=provider, model=model,
                             output=output, greska=greska or None)
            ctx.model_results.append(mr)

            if output is None:
                continue   # ovaj handler nije uspio -> sledeci

            rezultat = validiraj_json(output)
            mr.validna = rezultat.uspjesno
            if not rezultat.uspjesno:
                mr.greska = "; ".join(rezultat.greske)
                continue   # nije validan -> sledeci

            sr = real_score(output, ctx.prepared_text or "")
            mr.score_result = sr
            if mr.score >= settings.fallback_threshold:
                ctx.threshold_met = True
                break      # DOVOLJAN -> lanac staje ovdje

        # Ako svi pali: StageError(fatal=False) -> ArbiterStage dobija sansu
        if not ctx.threshold_met:
            raise StageError("Svi modeli ispod praga", fatal=False)
        return ctx
```

---

## 3. Primjena na BitLab AI Asistenta

### 3.1 Problem: Dupla Tool-Loop Implementacija (Kritican)

**Lokacija:** `app/agent.py`, `_run_anthropic()` (r.113-176) i `_run_pwr()` (r.179-267)

**Koji pattern:** Factory za backend + ekstrakcija zajednicke AgentLoop logike

**Gdje tacno:** Cijele dvije funkcije se zamjenjuju jednim `AgentLoop` objektom i dva mala adaptera.

**Konkretan refaktoring:**

```python
# app/backends/base.py  (novi fajl)
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict

@dataclass
class LLMResponse:
    tool_uses: list[ToolUseBlock]
    text: str | None  # None ako je model vratio samo tool_use, bez teksta


class AbstractLLMBackend(ABC):
    """SDK-agnostic interface. Implementacija ne zna za agent logiku."""

    @abstractmethod
    def call(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...

    @abstractmethod
    def build_tool_result_message(
        self, tool_use_id: str, content: str
    ) -> dict: ...
    # Anthropic vraca: {"role": "user", "content": [{"type": "tool_result", ...}]}
    # PWR/OpenAI vraca: {"role": "tool", "tool_call_id": ..., "content": ...}


# app/backends/anthropic_backend.py  (novi fajl)
import anthropic
from .base import AbstractLLMBackend, LLMResponse, ToolUseBlock

class AnthropicBackend(AbstractLLMBackend):
    def __init__(self, api_key: str, model: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def call(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT_V1,
            messages=messages,
            tools=tools,
        )
        tool_uses = [
            ToolUseBlock(id=b.id, name=b.name, input=b.input)
            for b in resp.content
            if b.type == "tool_use"
        ]
        text = next(
            (b.text for b in resp.content if b.type == "text"), None
        )
        return LLMResponse(tool_uses=tool_uses, text=text)

    def build_tool_result_message(self, tool_use_id: str, content: str) -> dict:
        return {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": content}],
        }


# app/backends/pwr_backend.py  (novi fajl)
import openai
from .base import AbstractLLMBackend, LLMResponse, ToolUseBlock

class PWRBackend(AbstractLLMBackend):
    def __init__(self, base_url: str, api_key: str, model: str):
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def call(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
        )
        msg = resp.choices[0].message
        tool_uses = [
            ToolUseBlock(id=tc.id, name=tc.function.name,
                         input=json.loads(tc.function.arguments))
            for tc in (msg.tool_calls or [])
        ]
        return LLMResponse(tool_uses=tool_uses, text=msg.content)

    def build_tool_result_message(self, tool_use_id: str, content: str) -> dict:
        return {"role": "tool", "tool_call_id": tool_use_id, "content": content}


# app/backends/factory.py  (novi fajl)
from app.config import Settings
from .base import AbstractLLMBackend
from .anthropic_backend import AnthropicBackend
from .pwr_backend import PWRBackend

def create_backend(settings: Settings) -> AbstractLLMBackend:
    if settings.use_pwr:
        return PWRBackend(
            base_url=str(settings.pwr_base_url),
            api_key=settings.pwr_api_key,
            model=settings.model,
        )
    return AnthropicBackend(
        api_key=settings.anthropic_api_key,
        model=settings.model,
    )


# app/agent_loop.py  (novi fajl — zamjenjuje while petlju u _run_anthropic/_run_pwr)
from app.backends.base import AbstractLLMBackend
from app.tools import dispatch, TOOL_DEFINITIONS
import json

# Centralne konstante — vise nema rasutih string literala
TOOL_RESPOND_TO_USER = "respond_to_user"
TOOL_CATALOG = {"category_overview", "search_products"}

class AgentLoop:
    """SDK-agnostic while petlja. Jednom napisana, radi sa svakim backendom."""

    def __init__(self, backend: AbstractLLMBackend, max_iterations: int = 5):
        self._backend = backend
        self._max_iterations = max_iterations

    def run(self, messages: list[dict]) -> dict:
        tool_calls_log: list[dict] = []
        iterations = 0

        for _ in range(self._max_iterations):
            iterations += 1
            response = self._backend.call(messages, TOOL_DEFINITIONS)

            if not response.tool_uses:
                # Model odgovorio tekstom direktno
                return {
                    "reply": response.text or "",
                    "tool_calls": tool_calls_log,
                    "iterations": iterations,
                }

            # Obradi sve tool use blokove
            for tool_use in response.tool_uses:
                tool_calls_log.append({"name": tool_use.name, "input": tool_use.input})

                if tool_use.name == TOOL_RESPOND_TO_USER:
                    return {
                        "reply": tool_use.input.get("message", ""),
                        "tool_calls": tool_calls_log,
                        "iterations": iterations,
                    }

                # Kataloski tool — dispatch i dodaj rezultat u poruke
                result_content = dispatch(tool_use.name, tool_use.input)
                tool_result_msg = self._backend.build_tool_result_message(
                    tool_use.id, result_content
                )
                messages = [*messages, tool_result_msg]

        return {"reply": "", "tool_calls": tool_calls_log, "iterations": iterations}


# app/agent.py  (refaktorisano — stare _run_anthropic/_run_pwr se brisu)
from app.backends.factory import create_backend
from app.agent_loop import AgentLoop
from app.config import settings

def run_agent(messages: list[dict]) -> dict:
    backend = create_backend(settings)    # Factory odlucuje koji backend
    loop = AgentLoop(backend)             # Petlja ne zna koji je backend
    return loop.run(messages)
```

Ovaj refaktoring eliminise ~130 LOC duplikata. Dodavanje treceg backend-a (npr. Gemini) je jedna nova klasa koja implementira `AbstractLLMBackend` — `AgentLoop` i `run_agent` se ne diraju.

---

### 3.2 Problem: Module-Level Side Effects u `tools.py`

**Lokacija:** `app/tools.py`, r.34-81 — globalni state `_CATEGORIES`, `_CHILDREN_BY_PARENT`, itd. se grade pri importu

**Koji pattern:** Lazy initialization sa Factory funkcijom + dependency injection

**Gdje tacno:** Blok na r.34-81 koji cita fajl i gradi rjecnike pri importu modula

**Konkretan refaktoring:**

```python
# app/tools.py  (refaktorisano)
from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass

# Centralne konstante za tool nazive — vise nema rasutih literala
TOOL_CATEGORY_OVERVIEW = "category_overview"
TOOL_SEARCH_PRODUCTS = "search_products"
TOOL_RESPOND_TO_USER = "respond_to_user"


@dataclass
class CategoryStore:
    """Sve kategorije — jedan objekt, lako mock-ovati u testovima."""
    categories: dict
    children_by_parent: dict
    parent_ids: set
    parent_id_enum: list[str]
    leaf_id_enum: list[str]

    @classmethod
    def from_file(cls, path: Path) -> "CategoryStore":
        data = json.loads(path.read_text(encoding="utf-8"))
        categories = {c["id"]: c for c in data}
        children_by_parent: dict[str, list] = {}
        parent_ids: set[str] = set()
        for cat in data:
            pid = cat.get("parent_id")
            if pid:
                children_by_parent.setdefault(pid, []).append(cat)
                parent_ids.add(pid)
        leaf_ids = [c["id"] for c in data if c["id"] not in parent_ids]
        return cls(
            categories=categories,
            children_by_parent=children_by_parent,
            parent_ids=parent_ids,
            parent_id_enum=list(parent_ids),
            leaf_id_enum=leaf_ids,
        )


@lru_cache(maxsize=1)
def _get_store() -> CategoryStore:
    """Lazy init — cita fajl tek kad se prvi put pozove, ne pri importu."""
    path = Path(__file__).parent.parent / "data" / "categories_new.json"
    return CategoryStore.from_file(path)


def _handle_category_overview(args: dict) -> str:
    store = _get_store()
    # ... logika koristeci store ...


def _handle_search_products(args: dict) -> str:
    store = _get_store()
    # ... logika koristeci store ...


# Registar tool handlera — nema vise if/elif na string
_TOOL_REGISTRY: dict[str, callable] = {
    TOOL_CATEGORY_OVERVIEW: _handle_category_overview,
    TOOL_SEARCH_PRODUCTS:   _handle_search_products,
}

def dispatch(tool_name: str, args: dict) -> str:
    handler = _TOOL_REGISTRY.get(tool_name)
    if handler is None:
        return json.dumps({"error": f"Nepoznati tool: {tool_name}"})
    return handler(args)


# U testovima:
# from unittest.mock import patch
# with patch("app.tools._get_store", return_value=mock_store):
#     result = dispatch("category_overview", {...})
# Nema monkeypatching globalnog state-a.
```

Kljucna promjena: nema vise koda na module level koji ima side-effects. `_get_store()` je `lru_cache` — prva poziva cita fajl, sve ostale vraca cached objekt. U testovima se mock-uje ta jedna funkcija.

---

### 3.3 Problem: `run_suite()` God Function u Eval Frameworku

**Lokacija:** `evals/framework/runner.py`, `run_suite()` r.144-303 (160 LOC)

**Koji pattern:** Pipeline Pattern — svaka odgovornost postaje Stage

**Gdje tacno:** Cijela `run_suite()` funkcija

**Konkretan refaktoring:**

```python
# evals/framework/pipeline.py  (novi fajl)
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class SuiteContext:
    """Jedini nosac stanja kroz eval pipeline."""
    suite_path: Path
    mode: str
    limit: int | None
    # Puni se kroz pipeline:
    entries: list[dict] = field(default_factory=list)
    sampled: list[dict] = field(default_factory=list)
    verdicts: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    completed_stages: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    # Checkpoint stanje:
    checkpoint_path: Path | None = None
    resumed_ids: set[str] = field(default_factory=set)


# evals/framework/stages/load_stage.py
class LoadEntriesStage:
    name = "load_entries"

    def run(self, ctx: SuiteContext) -> SuiteContext:
        from evals.framework.loader import load_suite
        ctx.entries = load_suite(ctx.suite_path)
        return ctx


# evals/framework/stages/resume_stage.py
class ResumeStage:
    name = "resume"

    def run(self, ctx: SuiteContext) -> SuiteContext:
        if ctx.checkpoint_path and ctx.checkpoint_path.exists():
            import json
            data = json.loads(ctx.checkpoint_path.read_text())
            if data.get("mode") != ctx.mode:
                raise StageError(
                    f"Mode mismatch: checkpoint={data['mode']}, current={ctx.mode}",
                    fatal=True,
                )
            ctx.resumed_ids = set(data.get("completed_ids", []))
            ctx.warnings.append(f"Resume: preskacemo {len(ctx.resumed_ids)} entry-ja")
        return ctx


# evals/framework/stages/sample_stage.py
class SampleStage:
    name = "sample"

    def run(self, ctx: SuiteContext) -> SuiteContext:
        from evals.framework.sampler import stratified_sample
        candidates = [e for e in ctx.entries if e["id"] not in ctx.resumed_ids]
        ctx.sampled = stratified_sample(candidates, ctx.limit)
        return ctx


# evals/framework/stages/run_entries_stage.py
class RunEntriesStage:
    """Jedina stage koja ima unutrasnju petlju po entry-jima."""
    name = "run_entries"

    def run(self, ctx: SuiteContext) -> SuiteContext:
        from evals.framework.budget import BudgetTracker
        from evals.framework.cache import VerdictCache
        from evals.framework.client import EvalClient
        from evals.framework.judge import judge_entry
        from evals.framework.reporter import append_verdict

        budget = BudgetTracker()
        cache = VerdictCache()
        client = EvalClient()

        for entry in ctx.sampled:
            # BudgetGate -> CacheGate -> LLMCall -> CachePut -> Record
            if budget.should_pause():
                ctx.warnings.append(f"Budget pauza na entry {entry['id']}")
                _write_pause_marker(ctx, entry["id"])
                break

            cached = cache.get(entry)
            if cached:
                ctx.verdicts.append(cached)
                continue

            try:
                response = client.call(entry)
            except RateLimitDetected:
                ctx.warnings.append(f"Rate limit na {entry['id']}")
                _write_pause_marker(ctx, entry["id"])
                break

            verdict = judge_entry(entry, response)
            cache.put(entry, verdict)
            budget.record(response)
            ctx.verdicts.append(verdict)
            append_verdict(verdict, ctx.suite_path)

        return ctx


# evals/framework/stages/report_stage.py
class ReportStage:
    name = "report"

    def run(self, ctx: SuiteContext) -> SuiteContext:
        from evals.framework.reporter import print_summary, write_html
        print_summary(ctx.verdicts)
        write_html(ctx.verdicts, ctx.suite_path)
        return ctx


# evals/framework/suite_factory.py
from evals.framework.pipeline import Pipeline, SuiteContext
from evals.framework.stages.load_stage import LoadEntriesStage
from evals.framework.stages.resume_stage import ResumeStage
from evals.framework.stages.sample_stage import SampleStage
from evals.framework.stages.run_entries_stage import RunEntriesStage
from evals.framework.stages.report_stage import ReportStage

def build_eval_pipeline() -> Pipeline:
    return Pipeline([
        LoadEntriesStage(),
        ResumeStage(),
        SampleStage(),
        RunEntriesStage(),
        ReportStage(),
    ])

def run_suite(suite_path: Path, mode: str, limit: int | None = None) -> SuiteContext:
    ctx = SuiteContext(suite_path=suite_path, mode=mode, limit=limit)
    return build_eval_pipeline().run(ctx)
```

`run_suite()` pada sa 160 LOC na 4 linije. Svaka Stage je izolovana i testabilna bez pokretanja cijelog eval suite-a.

---

### 3.4 Problem: Magic String Routing u `dispatch()` i `agent.py`

**Lokacija:** `app/tools.py` `dispatch()` funkcija + `app/agent.py` string literali rasuti po kodu

**Koji pattern:** Registar (varijanta Factory) + centralne konstante

**Gdje tacno:** Vec rijeseno u sekciji 3.2 kroz `_TOOL_REGISTRY` i `TOOL_*` konstante — iste konstante se importuju i u `agent_loop.py` da nema duplikata.

```python
# app/tools.py — vec prikazano u 3.2
TOOL_CATEGORY_OVERVIEW = "category_overview"
TOOL_SEARCH_PRODUCTS = "search_products"
TOOL_RESPOND_TO_USER = "respond_to_user"

# app/agent_loop.py — importuje, ne redefini se
from app.tools import TOOL_RESPOND_TO_USER, dispatch, TOOL_DEFINITIONS
```

---

### 3.5 Problem: SYSTEM_PROMPT_V1 Embedded u `agent.py`

**Lokacija:** `app/agent.py`, 72-linijski string direktno u Python kodu

**Koji pattern:** Nije klasican design pattern — ovo je konfiguracija vs kod separacija

**Gdje tacno:** Linija gdje pocinje `SYSTEM_PROMPT_V1 = """..."""`

**Konkretan refaktoring:**

```python
# app/prompts/v1.txt  (novi fajl — prompt kao tekst, hot-reload moguc)
Ti si AI asistent za BitLab web shop...
[sadrzaj prompta]

# app/prompts/__init__.py  (novi fajl)
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Ucitava prompt iz fajla. lru_cache = ucita se jednom po procesu."""
    path = Path(__file__).parent / f"{name}.txt"
    return path.read_text(encoding="utf-8")

# U agent.py — umjesto hardcoded stringa:
from app.prompts import load_prompt

# U AbstractLLMBackend.call():
system = load_prompt("v1")  # ili load_prompt(settings.prompt_version)
```

Sad je moguce A/B testiranje prompta bez redeploya: postavi `PROMPT_VERSION=v2` env var i ucitaj `v2.txt`.

---

## 4. Prioritetni Plan

### Redoslijed od najvaznjijeg ka manje vaznom

---

**Prioritet 1 (Kritican — eliminise ~130 LOC duplikata):**
Ekstrakcija `AgentLoop` + `AbstractLLMBackend` + Factory

- Fajlovi koji se kreiraju: `app/backends/base.py`, `app/backends/anthropic_backend.py`, `app/backends/pwr_backend.py`, `app/backends/factory.py`, `app/agent_loop.py`
- Fajlovi koji se mijenjaju: `app/agent.py` (brisanje `_run_anthropic` i `_run_pwr`, nova `run_agent` od ~5 linija)
- Verifikacija: svi postojeci testovi koji mock-uju `_run_anthropic` / `_run_pwr` se prepisuju da mock-uju `AbstractLLMBackend.call()`; ponasanje iz perspektive `POST /api/chat` ostaje identicno
- Trajanje: 1 radni dan
- Blokira: sve ostalo ovisi o ovome jer je `agent.py` srce sistema

---

**Prioritet 2 (Visok — testabilnost tools modula):**
Lazy init `CategoryStore` + `_TOOL_REGISTRY` registar + `TOOL_*` konstante

- Fajlovi koji se mijenjaju: `app/tools.py` (refaktoring inline, ne novi fajlovi)
- Verifikacija: testovi koji trenutno moraju mock-ovati globalni state sada mock-uju samo `_get_store()`; `dispatch()` pozivi s nepostojucim tool imenom vracaju JSON gresku umjesto da padnu
- Trajanje: pola radnog dana
- Zavisi od: Prioriteta 1 (jer `agent_loop.py` mora importovati `TOOL_*` konstante iz `tools.py`)

---

**Prioritet 3 (Visok — eval framework maintainability):**
Refaktoring `run_suite()` u Pipeline od 5 Stage klasa

- Fajlovi koji se kreiraju: `evals/framework/pipeline.py`, `evals/framework/stages/` (5 fajlova), `evals/framework/suite_factory.py`
- Fajlovi koji se mijenjaju: `evals/framework/runner.py` (stara `run_suite()` se zamjenjuje pozivom `suite_factory.run_suite()`)
- Verifikacija: `python -m evals.framework.runner --suite acceptance --mode full` daje iste rezultate kao i prije; `--stop-after sample` mogucnost za debug
- Trajanje: 1 radni dan
- Napomena: ovo je odvojeno od Prioriteta 1 i 2 — moze se raditi paralelno ako postoje dva developera, inace nakon P2

---

**Prioritet 4 (Srednji — operativna fleksibilnost):**
Ekstrakcija `SYSTEM_PROMPT_V1` u `app/prompts/v1.txt`

- Fajlovi koji se kreiraju: `app/prompts/__init__.py`, `app/prompts/v1.txt`
- Fajlovi koji se mijenjaju: `app/agent.py` ili `app/backends/anthropic_backend.py` / `pwr_backend.py` — uklanja se hardcoded string, dodaje `load_prompt("v1")`
- Verifikacija: `POST /api/chat` sa testnim pitanjem vraca isti odgovor; `v2.txt` sa izmjenom jedne linije se ucitava bez redeploya (samo restart procesa)
- Trajanje: 2 sata
- Zavisi od: Prioriteta 1 (jer backend klase nose system prompt poziv)

---

**Prioritet 5 (Nizak — tehnicko dugovanje, ne blokira nista):**
Centralizacija `_estimate_reset_epoch` duplikata

- Lokacija: `evals/framework/runner.py::_estimate_reset_epoch()` i `ralph/estimate_reset.py::estimate_reset()` implementiraju istu sliding-window logiku na dva razlicita nacina
- Akcija: Jedna funkcija u `evals/framework/budget.py`, obje lokacije je importuju
- Verifikacija: `ralph/wait_pause.py` i `runner.py` vracaju isti epoch za iste ulazne podatke
- Trajanje: 2 sata
- Napomena: Nema funkcionalnog uticaja dok su oba puta konzistentna — mozda je razlika namjerna (jedna je "legacy"); provjeriti s autorom prije refaktoringa

---

**Ukupna procjena:** 3-4 radna dana za sve 5 prioriteta. Prioritet 1 i 2 zajedno eliminisu najveci dio tehnickog duga i trebaju biti u istom PR-u (jer dijele `TOOL_*` konstante). Prioritet 3 je odvojen PR. Prioriteti 4 i 5 su sitni i mogu ici kao jedan zajednicki `chore` PR.
