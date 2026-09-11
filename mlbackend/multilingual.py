"""
AgriSaathi Multilingual Support
=================================
Provides language detection, translation stubs, and localization
for Hindi, Punjabi, Telugu, Marathi, Tamil, Kannada, Bengali, Odia.

Architecture:
- Language detection via langdetect (no API keys needed)
- Response templates in multiple languages for structured parts
- Full AI response is generated in English internally, then
  "spoken intro" and "unit labels" are localized.
- All user messages are translated to English before passing to the AI.

NO EXTERNAL TRANSLATION API REQUIRED for basic operation.
Optional: integrate with Google Translate API if premium quality needed.
"""
from typing import Optional, Tuple


# ISO 639-1 language codes supported
SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "pa": "Punjabi",
    "te": "Telugu",
    "mr": "Marathi",
    "ta": "Tamil",
    "kn": "Kannada",
    "bn": "Bengali",
    "or": "Odia",
    "en": "English"
}

# Greeting templates per language
GREETINGS = {
    "hi": "नमस्ते! AgriSaathi AI यहाँ है।",
    "pa": "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! AgriSaathi AI ਹਾਜ਼ਰ ਹੈ।",
    "te": "నమస్కారం! AgriSaathi AI ఇక్కడ ఉంది.",
    "mr": "नमस्कार! AgriSaathi AI इथे आहे.",
    "ta": "வணக்கம்! AgriSaathi AI இங்கே உள்ளது.",
    "kn": "ನಮಸ್ಕಾರ! AgriSaathi AI ಇಲ್ಲಿದೆ.",
    "bn": "নমস্কার! AgriSaathi AI এখানে আছে।",
    "or": "ନମସ୍କାର! AgriSaathi AI ଏଠାରେ ଅଛି।",
    "en": "Hello! AgriSaathi AI is here."
}

# Sensor unit labels per language
SENSOR_LABELS = {
    "hi": {
        "soil_moisture": "मिट्टी नमी",
        "temperature": "तापमान",
        "humidity": "आर्द्रता",
        "ph": "पीएच",
        "nitrogen": "नाइट्रोजन",
        "phosphorus": "फास्फोरस",
        "potassium": "पोटेशियम"
    },
    "pa": {
        "soil_moisture": "ਮਿੱਟੀ ਦੀ ਨਮੀ",
        "temperature": "ਤਾਪਮਾਨ",
        "humidity": "ਨਮੀ",
        "ph": "ਪੀਐਚ",
        "nitrogen": "ਨਾਈਟ੍ਰੋਜਨ",
        "phosphorus": "ਫਾਸਫੋਰਸ",
        "potassium": "ਪੋਟਾਸ਼ੀਅਮ"
    },
    "te": {
        "soil_moisture": "నేల తేమ",
        "temperature": "ఉష్ణోగ్రత",
        "humidity": "తేమ",
        "ph": "పీహెచ్",
        "nitrogen": "నైట్రోజన్",
        "phosphorus": "ఫాస్ఫరస్",
        "potassium": "పొటాషియం"
    },
    "mr": {
        "soil_moisture": "माती ओलावा",
        "temperature": "तापमान",
        "humidity": "आर्द्रता",
        "ph": "पीएच",
        "nitrogen": "नायट्रोजन",
        "phosphorus": "फॉस्फरस",
        "potassium": "पोटॅशियम"
    },
    "en": {
        "soil_moisture": "Soil Moisture",
        "temperature": "Temperature",
        "humidity": "Humidity",
        "ph": "pH",
        "nitrogen": "Nitrogen",
        "phosphorus": "Phosphorus",
        "potassium": "Potassium"
    }
}

# Alert message templates
ALERT_TEMPLATES = {
    "low_moisture": {
        "hi": "⚠️ मिट्टी में नमी कम है ({val}%). सिंचाई आवश्यक है।",
        "pa": "⚠️ ਮਿੱਟੀ ਵਿੱਚ ਨਮੀ ਘੱਟ ਹੈ ({val}%). ਸਿੰਚਾਈ ਜ਼ਰੂਰੀ ਹੈ।",
        "te": "⚠️ నేలలో తేమ తక్కువగా ఉంది ({val}%). నీటి పారుదల అవసరం.",
        "mr": "⚠️ मातीत ओलावा कमी आहे ({val}%). सिंचन आवश्यक आहे.",
        "en": "⚠️ Soil moisture is low ({val}%). Irrigation needed."
    },
    "high_temperature": {
        "hi": "🌡️ तापमान बहुत अधिक है ({val}°C). फसल को नुकसान हो सकता है।",
        "en": "🌡️ Temperature is too high ({val}°C). Crop stress risk."
    },
    "low_nitrogen": {
        "hi": "🌿 नाइट्रोजन स्तर कम है। यूरिया उर्वरक लगाएं।",
        "en": "🌿 Nitrogen levels are low. Apply urea fertilizer."
    },
    "sensor_offline": {
        "hi": "📡 सेंसर ऑफलाइन है। कृपया कनेक्शन जांचें।",
        "pa": "📡 ਸੈਂਸਰ ਔਫਲਾਈਨ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਕੁਨੈਕਸ਼ਨ ਜਾਂਚੋ।",
        "te": "📡 సెన్సర్ ఆఫ్‌లైన్‌లో ఉంది. దయచేసి కనెక్షన్‌ని తనిఖీ చేయండి.",
        "en": "📡 Sensor is offline. Please check connection."
    }
}


def detect_language(text: str) -> str:
    """
    Detect the language of user input text.
    Returns ISO 639-1 code, defaults to 'en' if detection fails.
    """
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 42  # reproducibility
        lang = detect(text)
        # Normalize common variants
        if lang.startswith("zh"):
            lang = "zh"
        return lang if lang in SUPPORTED_LANGUAGES else "en"
    except Exception:
        return "en"


def get_greeting(lang_code: str) -> str:
    """Return localized greeting."""
    return GREETINGS.get(lang_code, GREETINGS["en"])


def get_alert_message(alert_type: str, lang_code: str, val: Optional[str] = None) -> str:
    """Return a localized alert message, filling in dynamic values."""
    templates = ALERT_TEMPLATES.get(alert_type, {})
    template = templates.get(lang_code, templates.get("en", f"Alert: {alert_type}"))
    if val is not None:
        template = template.replace("{val}", str(val))
    return template


def get_sensor_labels(lang_code: str) -> dict:
    """Return localized sensor label dictionary."""
    return SENSOR_LABELS.get(lang_code, SENSOR_LABELS["en"])


def translate_to_english(text: str, source_lang: str) -> Tuple[str, bool]:
    """
    Translate non-English text to English for AI processing.
    
    Returns:
        (translated_text, was_translated: bool)
    
    Strategy:
    1. Try Google Translate (free tier via requests) – no API key needed for small volume
    2. Fall back to returning original text (AI can often understand Hindi/regional scripts)
    """
    if source_lang == "en":
        return text, False
    
    # Attempt free Google Translate endpoint (unofficial, 5000 char limit)
    try:
        import urllib.request
        import urllib.parse
        query = urllib.parse.urlencode({
            "q": text,
            "langpair": f"{source_lang}|en",
            "de": "agrisaathi@sih2026.in"
        })
        url = f"https://api.mymemory.translated.net/get?{query}"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = resp.read()
        import json
        result = json.loads(data)
        translated = result.get("responseData", {}).get("translatedText", "")
        if translated and translated.lower() != text.lower():
            return translated, True
    except Exception:
        pass

    # Fallback: return original (GPT-4 / Gemini can handle multilingual input)
    return text, False


def build_multilingual_response(
    english_response: str,
    lang_code: str,
    greeting: bool = True
) -> str:
    """
    Wrap an English AI response with a localized greeting when user is non-English.
    Full translation of responses is a future enhancement (requires translation API).
    """
    if lang_code == "en":
        return english_response
    
    lang_name = SUPPORTED_LANGUAGES.get(lang_code, "Unknown")
    header = get_greeting(lang_code)
    
    # Add language advisory
    disclaimer = f"\n\n_(Response in English. Full {lang_name} translation coming soon.)_"
    return f"{header}\n\n{english_response}{disclaimer}"
