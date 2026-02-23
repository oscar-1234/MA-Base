from datapizza.agents import Agent
from datapizza.memory import Memory

from ..agents.client import client
from ..prompts.system_prompts import BASE_ORCHESTRATOR_PROMPT, WEATHER_SYSTEM_PROMPT
from ..tools.weather import get_weather


def create_agents(memory: Memory) -> tuple[Agent, Agent]:
    """Factory: crea e collega gli agenti con la memory condivisa."""
    orchestrator = Agent(
        name="orchestrator_agent",
        client=client,
        system_prompt=BASE_ORCHESTRATOR_PROMPT,
        memory=memory,
        max_steps=10,
    )
    weather = Agent(
        name="weather_agent",
        client=client,
        system_prompt=WEATHER_SYSTEM_PROMPT,
        tools=[get_weather],
        memory=memory,
        max_steps=10,
    )
    orchestrator.can_call(weather)
    return orchestrator, weather
