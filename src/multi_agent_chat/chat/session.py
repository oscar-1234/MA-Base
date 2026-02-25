import json
import asyncio

from datapizza.memory import Memory
from datapizza.type import ROLE, TextBlock

from ..config import STM_MAX_TURNS
from ..memory.stm import prune_memory
from ..memory.ltm import get_ltm_context_async, save_final_response_to_ltm_async
from ..agents.setup import create_agents
from ..prompts.system_prompts import ORCHESTRATOR_PLANNER_PROMPT


### MONKEY PATCH
from openai import RateLimitError, APIConnectionError, AuthenticationError
import time
from datapizza.agents import Agent

original_stream_invoke = Agent.stream_invoke

def resilient_stream_invoke(self, query):
    try:
        yield from original_stream_invoke(self, query)
    except AuthenticationError as e:
        print(f"[API] ❌ Auth failed (fatal): {e}")
        raise RuntimeError("OpenAI authentication failed. Check API key.") from None
    except RateLimitError as e:
        print(f"[API] ⏳ Rate limit → 60s wait")
        time.sleep(60)
        yield from resilient_stream_invoke(self, query)
    except APIConnectionError as e:
        print(f"[API] 🌐 Connection retrying...")
        for i in range(3):
            time.sleep(2 ** i)
            try:
                yield from original_stream_invoke(self, query)
                return
            except APIConnectionError:
                continue
        
        # Fallback semplice
        class FallbackStep:
            def __init__(self, content):
                self.content = [TextBlock(content=content)]
                self.index = 1
                self.tools_used = []
        
        print("[API] ⚠️ All retries failed → fallback")
        yield FallbackStep("Connection issues. Please try again.")

Agent.stream_invoke = resilient_stream_invoke


# Istanze condivise di sessione
memory = Memory()
orchestrator_agent, weather_agent = create_agents(memory)


def chat_turn(user_query: str) -> None:
    """Un turno completo: prune → retrieve LTM → invoke → save."""
    print(f"\n🗣️ USER: {user_query}")

    # 1. Pruning pre-query
    prune_memory(memory, max_turns=STM_MAX_TURNS)

    # 2. LTM inject nel system prompt
    ltm_context = asyncio.run(get_ltm_context_async(user_query))
    if ltm_context:
        full_prompt = ORCHESTRATOR_PLANNER_PROMPT.format(ltm_context=ltm_context)
    else:
        full_prompt = ORCHESTRATOR_PLANNER_PROMPT

    memory.add_turn(TextBlock(content=user_query), role=ROLE.USER)

    # 3. Invoke con streaming
    for step in orchestrator_agent.stream_invoke(user_query):
        agent_name = (
            f"{orchestrator_agent.name} -> {step.tools_used[0].name}"
            if step.tools_used else orchestrator_agent.name
        )
        memory.add_turn(
            TextBlock(content=f"STEP: {step.index} | AGENT: {agent_name}"),
            role=ROLE.ASSISTANT,
        )
        for block in step.content:
            if hasattr(block, "arguments"):
                memory.add_to_last_turn(TextBlock(content=f"TOOL CALL: {block.name} ARGS: {block.arguments}"))
            elif hasattr(block, "result"):
                memory.add_to_last_turn(TextBlock(content=f"TOOL RESULT: {block.result}"))
            elif hasattr(block, "content"):
                memory.add_to_last_turn(TextBlock(content=f"TEXT CONTENT: {block.content}"))

        # Pruning intra-run ogni 3 step
        if step.index % 2 == 0:
            prune_memory(memory, max_turns=STM_MAX_TURNS)

    # 4. Salva ultimo turno in LTM
    print("\n💾 SAVING TO LTM...")
    asyncio.run(save_final_response_to_ltm_async(user_query, memory))

    # 5. Debug stato memoria
    data = json.loads(memory.json_dumps())
    print(f"\n📊 MEMORY STATE — Turni attivi: {len(data)}")
