#🤖 Multi-Agent Memory Management: A Case Study on datapizza-ai Framework 
## A Case Study on datapizza-ai Framework

## 🎯 Panoramica

Questo progetto dimostra soluzioni per:
- **State Management**: STM sliding window + LTM con Mem0
- **Planning**: Procedural Memory + `planning_interval=3`
- **Multi-Agent**: 4 agenti coordinati con `max_steps` anti-loop
- **Long-term Memory**: Retrieval top-K efficiente (~200 token)
- **Error Recovery**: 3 layer (prompt + Tenacity + monkey patch)


## Strumenti e Metodologie Implementate

Sono stati identificati **6 pattern/metodologie** principali:

### 1. STM con Sliding Window (Short-Term Memory)

Implementata in `memory/stm.py`. La funzione `prune_memory()` lavora per **turni completi** (user + tutti gli assistant che seguono), non per singoli messaggi. Quando si supera `STM_MAX_TURNS = 4`, i turni in scadenza vengono prima salvati in LTM e poi rimossi. Il pruning avviene sia **pre-query** che **intra-run** (ogni 2 step di `stream_invoke`).

### 2. LTM con Mem0 (Long-Term Memory)

Implementata in `memory/ltm.py`. Mem0 persiste fatti atomici cross-sessione tramite un vector store (Qdrant embedded). Il retrieval è **on-demand top-K=3** per query, non dump completo. Un `CUSTOM_FACT_EXTRACTION_PROMPT` filtra esplicitamente dati transienti (meteo, tool call, step metadata) estraendo solo fatti personali duraturi (nome, città, preferenze).

### 3. Procedural Memory + Dynamic Toolset Injection

Implementata in `prompts/procedural_memory.py`. Il dizionario `PROC_MEMORY` definisce 3 workflow (`weather`, `transfer_booking`, `generic`), ciascuno con istruzioni step-by-step precise e un set di agenti disponibili **iniettato dinamicamente** nel system prompt dell'orchestratore. Questo riduce il rischio di allucinazioni e loop delegando solo gli strumenti pertinenti.

### 4. Task Classifier (Intent Routing)

Implementato in `chat/classifier.py`. Un LLM leggero (`temperature=0.1`) classifica ogni query in `weather` / `transfer_booking` / `generic` prima di invocare il multi-agente. La versione `classify_user_intent_2` (commentata) include anche STM e LTM nel contesto di classificazione per gestire query ambigue come "Weather?" (risolto con profilo utente da LTM).

### 5. Multi-Agent Orchestration con datapizza-ai

In `agents/setup.py` vengono creati 4 agenti (`orchestrator`, `weather`, `parse_weather`, `transfer`) con memoria condivisa e `orchestrator.can_call([...])`. L'orchestratore usa `planning_interval=3` (ogni 3 step rivaluta il piano) e `max_steps=10` per evitare loop infiniti. L'agente `parse_weather` ha intenzionalmente `max_steps=1` essendo deterministico.

### 6. Error Recovery Multi-Layer con Tenacity

Tre layer distinti di protezione:

- **Layer 1 — Prompt-level**: `system_prompts.py` istruisce ogni agente con `<error_handling>`: retry con input semplificato, stop dopo 3 tentativi, risposta parziale > silenzio
- **Layer 2 — Python-level (Tenacity)**: nei tool `weather.py` e `transfer.py`, wrapper `@retry` con exponential backoff (1s→2s→4s, max 3 tentativi) per errori transienti (`TimeoutError`, `ConnectionError`, `OSError`); fail-fast immediato per errori permanenti (auth, bad input)
- **Layer 3 — Monkey Patch su `Agent.stream_invoke`**: in `session.py`, sovrascrittura runtime del metodo per gestire `RateLimitError` (wait 60s + retry), `APIConnectionError` (3 tentativi esponenziali + fallback `FallbackStep`), `AuthenticationError` (fail fast)

***

## Copertura dei 5 Temi

| Tema | Soluzione Implementata | Copertura stimata |
| :-- | :-- | :-- |
| **1. State Management** | STM sliding window turn-based (prune pre-query + intra-run ogni 2 step); LTM persistenza cross-sessione; memoria condivisa tra agenti | **~65%** — manca tracking esplicito di stato workflow complesso (es. "task al 60%")   |
| **2. Planning** | `planning_interval=3` nativo datapizza-ai; Procedural Memory inietta istruzioni step-by-step precise per task; Dynamic Toolset Injection riduce spazio decisionale | **~70%** — la robustezza dipende ancora dal modello sottostante per workflow > 6 step |
| **3. Multi-Agent Orchestration** | 4 agenti specializzati con ruoli distinti; `max_steps` per anti-loop; `<error_handling>` nel prompt blocca chiamate ripetute allo stesso agente (max 3); Intent Classifier riduce ambiguità di routing | **~75%** — non c'è un supervisore esterno o meccanismo di deadlock detection formale   |
| **4. Long-Term Memory** | Mem0 con fact extraction custom; retrieval top-K on-demand (~200 token per retrieve); nessun dump completo della conversazione; filtro esplicito di dati transienti | **~90%** — soluzione più matura del progetto; manca compressione semantica per sessioni molto lunghe   |
| **5. Error Recovery** | 3 layer indipendenti (prompt + Tenacity + monkey patch); tabella errori transienti vs permanenti; `save_to_ltm` con fallback silenzioso (blocca pruning se LTM down per non perdere STM); simulation flags per test | **~80%** — manca circuit breaker formale e logging/alerting persistente   |



## 🏗️ Struttura del Progetto
```
MA_BASE/
├── README.md # Questa documentazione
├── main.py # Entry point chat loop
├── requirements.txt # Dipendenze (datapizza-ai 0.0.9+)
├── .env.example # Template API keys
├── setup.bat # Setup venv + pip install
└── src/
    └── multi_agent_chat/
        ├── config.py # Env vars + costanti
        ├── agents/ # Factory agenti + client Ollama/OpenAI
        │ ├── client.py
        │ └── setup.py
        ├── chat/ # Classifier intent + session
        │ ├── classifier.py
        │ └── session.py
        ├── memory/ # STM pruning + LTM Mem0
        │ ├── ltm.py
        │ └── stm.py
        ├── prompts/ # System prompts + procedural memory
        │ ├── procedural_memory.py
        │ └── system_prompts.py
        └── tools/ # Weather + Transfer tools
            ├── weather.py
            └── transfer.py
```