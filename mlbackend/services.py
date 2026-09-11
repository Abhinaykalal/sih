import requests
from deep_translator import GoogleTranslator
try:
    from .config import settings
except ImportError:
    from config import settings


# ============================================================
# LANGUAGE DETECTION FROM GEOLOCATION
# Indian state → regional language mapping
# ============================================================

STATE_LANG_MAP = {
    # North India
    "Uttar Pradesh": ("hi", "Hindi"),
    "Bihar": ("hi", "Hindi"),
    "Uttarakhand": ("hi", "Hindi"),
    "Himachal Pradesh": ("hi", "Hindi"),
    "Haryana": ("hi", "Hindi"),
    "Rajasthan": ("hi", "Hindi"),
    "Madhya Pradesh": ("hi", "Hindi"),
    "Chhattisgarh": ("hi", "Hindi"),
    "Delhi": ("hi", "Hindi"),
    "Jharkhand": ("hi", "Hindi"),

    # Maharashtra / Goa
    "Maharashtra": ("mr", "Marathi"),
    "Goa": ("mr", "Marathi"),

    # Punjab / Chandigarh
    "Punjab": ("pa", "Punjabi"),
    "Chandigarh": ("pa", "Punjabi"),

    # South India
    "Karnataka": ("kn", "Kannada"),
    "Tamil Nadu": ("ta", "Tamil"),
    "Kerala": ("ml", "Malayalam"),
    "Andhra Pradesh": ("te", "Telugu"),
    "Telangana": ("te", "Telugu"),

    # East India
    "West Bengal": ("bn", "Bengali"),
    "Assam": ("as", "Assamese"),
    "Odisha": ("or", "Odia"),

    # West India
    "Gujarat": ("gu", "Gujarati"),

    # Default
}


def detect_language_from_coords(lat: float, lon: float):
    """
    Performs a reverse geocode using OpenStreetMap Nominatim API
    (no API key required) to find the Indian state, then maps it to
    the dominant regional language.
    Returns (lang_code, lang_name, state_name)
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "AgriSaathi-AI/2.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        data = resp.json()

        address = data.get("address", {})
        state = address.get("state", "")

        if state in STATE_LANG_MAP:
            lang_code, lang_name = STATE_LANG_MAP[state]
            return lang_code, lang_name, state

        # Try partial match
        for key in STATE_LANG_MAP:
            if key.lower() in state.lower():
                lang_code, lang_name = STATE_LANG_MAP[key]
                return lang_code, lang_name, state

    except Exception as e:
        print(f"Geolocation language detection error: {e}")

    return "hi", "Hindi", "Unknown"  # Safe Indian default


# ============================================================
# TRANSLATION SERVICE
# ============================================================

def translate_text(text: str, target_lang: str = "hi") -> str:
    """
    Translates text to target language using deep-translator / Google Translate.
    - Chunks long text into ≤4500 char pieces to stay under the API limit
    - Retries once on transient failure
    - Falls back gracefully to original text on any error
    """
    if not text or target_lang == "en":
        return text

    MAX_CHUNK = 4500

    def _translate_chunk(chunk: str) -> str:
        for attempt in range(2):
            try:
                result = GoogleTranslator(source="auto", target=target_lang).translate(chunk)
                if result:
                    return result
            except Exception as e:
                print(f"Translation attempt {attempt+1} failed ({target_lang}): {e}")
        return chunk  # fallback to original chunk

    # If short enough, translate directly
    if len(text) <= MAX_CHUNK:
        return _translate_chunk(text)

    # Split into chunks at paragraph/sentence boundaries where possible
    import re
    sentences = re.split(r'(?<=[.!\?\n])\s+', text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= MAX_CHUNK:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)

    translated_parts = [_translate_chunk(c) for c in chunks]
    return " ".join(translated_parts)



# ============================================================
# WEATHER API
# ============================================================

def get_weather(lat: float, lon: float, allow_simulation: bool = False) -> dict:
    """
    Fetches real-time weather from OpenWeather API.
    Handles missing keys, timeouts, and network failures with explicit null-safe statuses.
    Never inserts arbitrary fake temperature readings unless explicitly in simulation mode.
    """
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        if allow_simulation:
            return {
                "status": "SIMULATED",
                "temp": 28.5,
                "humidity": 68,
                "rainfall_last_3h": 0.0,
                "wind_speed": 4.2,
                "description": "Partly cloudy (Simulation Mode)",
                "provenance": "SIMULATED"
            }
        return {
            "status": "UNAVAILABLE",
            "temp": None,
            "humidity": None,
            "rainfall_last_3h": None,
            "wind_speed": None,
            "description": "Not available",
            "reason": "No verified weather reading received (API key not configured)",
            "provenance": "UNAVAILABLE"
        }

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}

    try:
        response = requests.get(url, params=params, timeout=8)
        response.raise_for_status()
        data = response.json()
        
        # OWM sometimes returns 'rain' only if it's currently raining
        rain_data = data.get("rain", {})
        rainfall = rain_data.get("3h", rain_data.get("1h", 0.0))
        
        return {
            "status": "AVAILABLE",
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "visibility": data.get("visibility", 10000),
            "rainfall_last_3h": rainfall,
            "wind_speed": data.get("wind", {}).get("speed", 0.0),
            "description": data["weather"][0]["description"].capitalize(),
            "location_name": data.get("name", "Unknown Region"),
            "provenance": "LIVE_WEATHER"
        }
    except Exception as e:
        return {
            "status": "TEMPORARILY_UNAVAILABLE",
            "temp": None,
            "humidity": None,
            "rainfall_last_3h": None,
            "wind_speed": None,
            "description": "Temporarily unavailable",
            "reason": f"Weather provider temporarily unavailable ({type(e).__name__})",
            "provenance": "UNAVAILABLE"
        }

def get_forecast(lat: float, lon: float) -> dict:
    """
    Fetches 5-day / 3-hour forecast. 
    Crucial for proactive frost or flood alerts.
    """
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        return {"error": "API Key missing for forecast system"}

    url = f"https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        summarized = []
        for entry in data.get("list", [])[:16]: 
            summarized.append({
                "time": entry.get("dt_txt"),
                "temp": entry["main"]["temp"],
                "condition": entry["weather"][0]["main"],
                "rain_prob": round(entry.get("pop", 0) * 100, 1) # probability 0-100
            })
        return {"city": data.get("city", {}).get("name"), "forecast": summarized}
    except Exception as e:
        return {"error": f"Forecast failed: {str(e)}"}


# ============================================================
# SOIL DATA API (ISRIC SoilGrids v2)
# ============================================================

def get_soil_data(lat: float, lon: float) -> dict:
    """
    Fetches multi-layer soil property data from the ISRIC SoilGrids global database.
    Now includes nutrients AND texture (sand/clay/silt) for deeper analysis.
    """
    properties = ["nitrogen", "phh2o", "soc", "clay", "sand", "silt"]
    props_query = "&property=".join(properties)
    url = (
        f"https://rest.isric.org/soilgrids/v2.0/properties/query"
        f"?lat={lat}&lon={lon}&property={props_query}&depth=0-5cm&value=mean"
    )
    
    # Defaults in case of API failure or missing data points
    result = {
        "N": 40.0, "ph": 6.5, "soc": 0.8,
        "clay": 30, "sand": 40, "silt": 30 
    }
    
    try:
        response = requests.get(url, timeout=12)
        response.raise_for_status()
        data = response.json()
        
        layers = data.get("properties", {}).get("layers", [])
        for layer in layers:
            name = layer.get("name", "")
            val = layer.get("depths", [{}])[0].get("values", {}).get("mean", None)
            if val is not None:
                if name == "nitrogen":
                    result["N"] = round(val / 100, 1)  # cg/kg → g/kg
                elif name == "phh2o":
                    result["ph"] = round(val / 10, 1)  # x10 → pH
                elif name == "soc":
                    result["soc"] = round(val / 10, 2) # dg/kg → %
                elif name in ["clay", "sand", "silt"]:
                    result[name] = round(val / 10, 1) # g/kg → %
        return result
    except Exception as e:
        print(f"Soil grids error: {e}")
        return result
