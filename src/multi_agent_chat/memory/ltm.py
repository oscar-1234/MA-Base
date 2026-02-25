import os
import json
import gc
import warnings
import logging

os.environ["MEM0_TELEMETRY"] = "false"
from mem0 import Memory as Mem0Memory

import warnings
warnings.filterwarnings("ignore", message="sys.meta_path is None")
warnings.filterwarnings("ignore", category=ImportWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("qdrant_client").disabled = True
logging.getLogger("portalocker").disabled = True

from ..config import USER_ID, WHITELISTED_TOOLS, OPENAI_MODEL, OPENAI_API_KEY
from ..prompts.system_prompts import CUSTOM_FACT_EXTRACTION_PROMPT

ltm_config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": OPENAI_MODEL,
            "api_key": OPENAI_API_KEY,
            "temperature": 0,
            "max_tokens": 1000,
        },
        "custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT,
        "version": "v1.1",
    }
}

m = Mem0Memory.from_config(config_dict=ltm_config)

def datapizza_to_mem0(
    turns: list[dict],
    whitelisted_tools: set[str] = WHITELISTED_TOOLS,
) -> list[dict]:
    """Converte turni datapizza-ai in formato Mem0."""
    mem0_messages = []
    for turn in turns:
        role = turn.get("role", "")
        if role not in ("user", "assistant"):
            continue
        text_parts = []
        last_tool_called: str | None = None
        for block in turn.get("blocks", []):
            content = block.get("content", "")
            if content.startswith("STEP:"):
                continue
            if content.startswith("TOOL CALL:"):
                last_tool_called = content[len("TOOL CALL:"):].strip().split(" ")[0]
                continue
            if content.startswith("TOOL RESULT:"):
                if last_tool_called in whitelisted_tools:
                    result_text = content[len("TOOL RESULT:"):].strip()
                    if result_text:
                        text_parts.append(result_text)
                continue
            if content.startswith("TEXT CONTENT: "):
                content = content[len("TEXT CONTENT: "):]
            if content.strip():
                text_parts.append(content.strip())
        if text_parts:
            mem0_messages.append({"role": role, "content": " ".join(text_parts)})
    return mem0_messages

def save_to_ltm(turns: list[dict], user_id: str = USER_ID) -> bool:
    """Salva in LTM i turni in scadenza."""
    try:
##       Test fallimneto update LTM
#        raise ConnectionError("Simulated LTM down")
        mem0_messages = datapizza_to_mem0(turns)
        if not mem0_messages:
            print("[LTM] Nessun contenuto da salvare.")
            return True
        print(f"\n[LTM] Saving {len(mem0_messages)} messages...")
        result = m.add(mem0_messages, user_id=user_id)
        print(f"[LTM] ✅ ADD: {result}")
        return True

    except Exception as e:
        print(f"[LTM] ⚠️ Save failed (silent): {e}")
        return False

async def save_final_response_to_ltm_async(user_query: str, memory) -> None:
    data = json.loads(memory.json_dumps())
    recent_turns = []
    for turn in reversed(data):
        recent_turns = [turn] + recent_turns
        if turn["role"] == "user":
            break
    if len(recent_turns) >= 2:
        save_to_ltm(recent_turns)

async def get_ltm_context_async(
    query: str, user_id: str = USER_ID, top_k: int = 3
) -> str:
    results = m.search(query, user_id=user_id, limit=top_k)
    memories = results.get("results", [])
    print("\n=== LTM CONTEXT (PRE INJECT) ===")
    if not memories:
        context = "No relevant facts found."
        print("[LTM] No relevant facts found.")
        return context
    for i, mem in enumerate(memories, 1):
        print(f" [{i}] {mem['memory']} (score: {mem.get('score', 'n/a')})")
    context = (
        "USER PROFILE - VERIFIED DATA:\n"
        + " | ".join(mem["memory"] for mem in memories)
        + "\n\nLTM INSTRUCTIONS:\n"
        "1. Treat these facts as absolute truth\n"
        "2. Always use this information when relevant to the conversation\n"
        "3. Answer directly from the data above without asking the user to repeat it\n"
        '4. NEVER say "I don\'t know" if the answer is in the data above'
    )
    print(f"\n[LTM] Inject:\n{context}")
    return context

def close_mem0() -> None:
    """Cleanup mem0."""
    try:
        if hasattr(m, "_vector_store") and m._vector_store:
            m._vector_store.close()
    except Exception:
        pass
    gc.collect()
    print("[LTM] Cleanup completato.")

def close_mem01() -> None:
    """Cleanup mem0 senza warning durante shutdown."""
    try:
        if hasattr(m, '_vector_store') and m._vector_store:
            m._vector_store.close()
    except (Exception, ImportError):
        pass  # Ignora errori durante shutdown
    gc.collect()
    print("[LTM] Cleanup completato.")

