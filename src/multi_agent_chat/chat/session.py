import json
import asyncio

from datapizza.memory import Memory
from datapizza.type import ROLE, TextBlock

#from multi_agent_chat.config import STM_MAX_TURNS
#from multi_agent_chat.prompts.system_prompts import BASE_ORCHESTRATOR_PROMPT
#from multi_agent_chat.memory.stm import prune_memory
#from multi_agent_chat.memory.ltm import get_ltm_context_async, save_final_response_to_ltm_async
#from multi_agent_chat.agents.setup import create_agents

from ..config import STM_MAX_TURNS
from ..memory.stm import prune_memory
from ..memory.ltm import get_ltm_context_async, save_final_response_to_ltm_async
from ..agents.setup import create_agents
from ..prompts.system_prompts import BASE_ORCHESTRATOR_PROMPT



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
    orchestrator_agent.system_prompt = (
        f"{BASE_ORCHESTRATOR_PROMPT}\n\n{ltm_context}" if ltm_context
        else BASE_ORCHESTRATOR_PROMPT
    )

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
        if step.index % 3 == 0:
            prune_memory(memory, max_turns=STM_MAX_TURNS)

    # 4. Salva ultimo turno in LTM
    print("\n💾 SAVING TO LTM...")
    asyncio.run(save_final_response_to_ltm_async(user_query, memory))

    # 5. Debug stato memoria
    data = json.loads(memory.json_dumps())
    print(f"\n📊 MEMORY STATE — Turni attivi: {len(data)}")
