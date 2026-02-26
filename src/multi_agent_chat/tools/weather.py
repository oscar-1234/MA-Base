import random
import hashlib
from ..config import USER_ID

from datapizza.tools import tool

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

def _stable_random_0_1(*parts: str) -> float:
    """
    Deterministic pseudo-random in [0,1) derived from input strings.
    """
    joined = "|".join(p.strip() for p in parts if p is not None)
    digest = hashlib.sha256(joined.encode("utf-8")).digest()
    # Usa i primi 8 byte come intero (64-bit) e normalizza
    n = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return (n % 10**12) / 10**12  # [0,1)

# === FALLBACK costanti ===
WEATHER_UNAVAILABLE = "Weather data temporarily unavailable — please try again shortly."

# === INNER FUNCTION con retry ===
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),  # 1s → 2s → 4s
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
    reraise=False  # non rilancia, gestiamo nel chiamante
)
def _fetch_weather(location: str, when: str) -> str:
    """
    Real call to the weather service.
    Tenacity retry on transient errors (timeout, connection).
    """
    # ── qui andrà la chiamata API reale ──
    # es: response = requests.get(f"https://api.weather.com/{location}")
    # Per ora mock:
    try:
        r = _stable_random_0_1(USER_ID, location, when)

        if r < 0.3:
            return f"Weather in {location} on {when}: 10°C, partly cloudy"
        elif r < 0.6:
            return f"Weather in {location} on {when}: 1°C, rainy"
        else:
            return f"Weather in {location} on {when}: 25°C, sunny"

    except RetryError:
        return WEATHER_UNAVAILABLE
    except Exception as e:
        return f"Weather service error: {str(e)}"


# === FLAG DI TEST (rimuovi in produzione) ===
SIMULATE_FAILURE_COUNT = 0        # contatore interno
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s → 2s → 4s
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
    reraise=False  # non rilancia, gestiamo nel chiamante
)
def _fetch_weather_failure(location: str, when: str) -> str:    
    # ── SIMULAZIONE FAILURE ──
    global SIMULATE_FAILURE_COUNT

    if  SIMULATE_FAILURE_COUNT < 2:
        SIMULATE_FAILURE_COUNT += 1
        print(f"[TEST] 💥 Simulated TimeoutError (attempt {SIMULATE_FAILURE_COUNT}/3)")
        raise TimeoutError("Simulated connection timeout")
    
    SIMULATE_FAILURE_COUNT = 0
    return f"Weather in {location} on {when}: 10°C, partly cloudy"

# === TOOL WRAPPER con fallback ===
@tool
def get_weather(location: str, when: str) -> str:
    """
    Retrieve a short weather summary for a given location and time.

    Use this tool to get an estimated temperature and conditions for:
    - location: a city/area name (e.g., "Milan", "Rome")
    - when: a date/time in natural language or ISO-like format (e.g., "today", "tomorrow morning", "2026-03-01")

    Behavior:
    - Returns a single-line human-readable summary in this format:
      "Weather in {location} on {when}: {temp}°C, {condition}"
    - The tool is resilient: it may retry on transient failures (timeouts/connection issues) and fall back to a
      stable "temporarily unavailable" message if it cannot retrieve data.

    Input rules:
    - location must be non-empty; if missing, the tool returns an explicit error message asking for a location.
    - when can be any non-empty string; if omitted/empty, the tool may still respond but should be provided.

    Notes for agents:
    - Weather is transient information and should not be stored as long-term user memory.

    Example:
    get_weather(location="Milan", when="tomorrow")
    -> "Weather in Milan on tomorrow: 10°C, partly cloudy"
    """

    if not location or not location.strip():
        return "Cannot retrieve weather: location not specified."
    
    try:
        result = _fetch_weather(location, when)
#       per SIMULAZIONE FAILURE
#        result = _fetch_weather_failure(location, when)
        print(f"[TOOL] ✅ get_weather({location}, {when})")
        return result
    
    except RetryError as e:
        # Tutti e 3 i tentativi falliti
        print(f"[TOOL] ❌ get_weather failed after 3 attempts: {e}")
        return WEATHER_UNAVAILABLE
    
    except Exception as e:
        # Errore non-transiente (bad input, auth...) → fail fast, no retry
        print(f"[TOOL] ❌ get_weather unexpected error: {type(e).__name__}: {e}")
        return f"Weather service error: {str(e)}"


@tool
def get_parse_weather(weather_string: str) -> str:
    """
    Extract the temperature value in °C as an integer from a weather summary string.

    Use this tool to reliably parse the temperature from get_weather() output.
    It finds the first number before "°C" in the input string and returns it as a string.

    Input:
    - weather_string: the raw output from get_weather (e.g., "Weather in Milan on tomorrow: 10°C, partly cloudy")

    Output:
    - A string containing the extracted integer temperature (e.g., "10", "-5").
    - "N/A" if no valid temperature is found (no match for pattern r'(-?\d+)°C').

    Behavior:
    - Handles positive/negative integers only (e.g., "25°C" → "25", "-2°C" → "-2").
    - Case-insensitive and ignores surrounding text.
    - Robust to malformed strings; never crashes.

    Examples:
    get_parse_weather("Weather in Rome tomorrow: 1°C, rainy") → "1"
    get_parse_weather("Weather in Milan now: 10°C, partly cloudy") → "10"
    get_parse_weather("No weather data available") → "N/A"
    get_parse_weather("Sunny 25 degrees") → "N/A"  (must have "°C")

    Notes for agents:
    - Call this immediately after get_weather to get a clean integer temperature.
    - Compare the result as int: if int(result) < 10 → choose "plane", else "train".
    - Do not parse manually; use this tool to avoid errors.
    """

    import re
    match = re.search(r'(-?\d+)°C', weather_string)
    return str(int(match.group(1))) if match else "N/A"
