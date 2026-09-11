import os
import requests
from dotenv import load_dotenv

load_dotenv()

def run_api_tests():
    print("--- TESTING OPENWEATHER API ---")
    owm_key = os.getenv("OPENWEATHER_API_KEY")
    if owm_key:
        try:
            r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat=19.076&lon=72.877&appid={owm_key}", timeout=5)
            if r.status_code == 200:
                print(f"[OK] OpenWeatherMap: Temp in Mumbai is {r.json()['main']['temp']}K")
            else:
                print(f"[FAIL] OpenWeatherMap: {r.status_code} {r.text}")
        except Exception as e:
            print(f"[FAIL] OpenWeatherMap network: {e}")
    else:
        print("[FAIL] OPENWEATHER_API_KEY not found in .env")

    print("\n--- TESTING TELEGRAM BOT API ---")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if tg_token:
        try:
            r = requests.get(f"https://api.telegram.org/bot{tg_token}/getMe", timeout=5)
            if r.status_code == 200:
                print(f"[OK] Telegram: Bot Name is {r.json()['result']['first_name']}")
            else:
                print(f"[FAIL] Telegram: {r.status_code} {r.text}")
        except Exception as e:
            print(f"[FAIL] Telegram network: {e}")
    else:
        print("[FAIL] TELEGRAM_BOT_TOKEN not found in .env")

    print("\n--- TESTING GROQ LLM API ---")
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            chat = client.chat.completions.create(
                messages=[{"role": "user", "content": "Say 'hello world' if you can hear me."}],
                model="llama-3.3-70b-versatile",
                max_tokens=10
            )
            print(f"[OK] Groq: {chat.choices[0].message.content}")
        except Exception as e:
            print(f"[FAIL] Groq: {e}")
    else:
        print("[FAIL] GROQ_API_KEY not found")

if __name__ == "__main__":
    run_api_tests()
