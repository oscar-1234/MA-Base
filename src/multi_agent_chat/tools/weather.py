from datapizza.tools import tool

@tool
def get_weather(location: str, when: str) -> str:
    """Retrives weather information"""
    return f"Weather in {location} on {when}: 10°C, partly cloudy"
