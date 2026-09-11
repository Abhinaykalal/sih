from pydantic import BaseModel
from typing import List, Optional

class PestInput(BaseModel):
    crop: str                          # rice, wheat, cotton, maize, tomato, etc.
    growth_stage: str                  # Sowing, Seedling, Vegetative, Flowering, Fruiting
    temperature: float                 # °C
    humidity: float                    # %
    rainfall_last_week: float = 0.0   # mm
    symptoms_observed: str = ""        # User describes symptoms: "yellowing leaves", "holes in leaves"
    region: str = "Central India"      # Geographic region
    lang: str = "en"

# Pest/disease risk lookup table per crop + condition
PEST_LIBRARY = {
    "rice": {
        "high_humidity": {
            "threat": "Rice Blast (Magnaporthe oryzae)",
            "condition": "humidity > 85",
            "action": "Apply Tricyclazole 75WP @ 0.6g/L water. Remove infected tillers immediately."
        },
        "high_temp": {
            "threat": "Brown Plant Hopper (BPH) infestation",
            "condition": "temp > 32",
            "action": "Apply Imidacloprid 17.8 SL @ 0.3ml/L. Drain field partially to reduce hopper habitat."
        },
        "vegetative": {
            "threat": "Stem Borer (Scirpophaga incertulas)",
            "condition": "vegetative stage",
            "action": "Apply Cartap Hydrochloride 4G @ 17kg/ha in standing water."
        }
    },
    "wheat": {
        "high_humidity": {
            "threat": "Yellow Rust (Puccinia striiformis)",
            "condition": "humidity > 80",
            "action": "Apply Propiconazole 25EC @ 0.1% solution. Surveill neighboring fields for spread."
        },
        "flowering": {
            "threat": "Aphid Colony (Sitobion avenae)",
            "condition": "flowering stage",
            "action": "Apply Dimethoate 30EC @ 1ml/L. Introduce natural predators (ladybird beetles)."
        }
    },
    "cotton": {
        "vegetative": {
            "threat": "Bollworm (Helicoverpa armigera)",
            "condition": "vegetative/flowering",
            "action": "Apply Bt (Bacillus thuringiensis) spray @ 1kg/ha. Deploy pheromone traps."
        },
        "high_temp": {
            "threat": "Red Spider Mite infestation",
            "condition": "temp > 35 + low humidity",
            "action": "Apply Dicofol 18.5EC @ 2ml/L water. Maintain soil moisture to deter mites."
        }
    },
    "maize": {
        "seedling": {
            "threat": "Fall Armyworm (Spodoptera frugiperda)",
            "condition": "seedling stage",
            "action": "Apply Emamectin Benzoate 5SG @ 0.4g/L directly to leaf whorl."
        },
        "high_humidity": {
            "threat": "Downy Mildew (Peronosclerospora sorghi)",
            "condition": "humidity > 80",
            "action": "Treat seeds with Metalaxyl 35 SD before sowing. Apply Mancozeb 75WP @ 2.5g/L."
        }
    },
    "tomato": {
        "high_humidity": {
            "threat": "Early Blight (Alternaria solani)",
            "condition": "humidity > 75",
            "action": "Apply Mancozeb 75WP @ 2.5g/L. Remove affected lower leaves."
        },
        "flowering": {
            "threat": "Fruit Borer (Helicoverpa armigera)",
            "condition": "flowering/fruiting",
            "action": "Apply Spinosad 45SC @ 0.3ml/L. Set up light traps at night."
        }
    }
}

try:
    from .llm_service import get_llm_response
except ImportError:
    from llm_service import get_llm_response


def analyze_pest_risk(data: PestInput) -> dict:
    """
    Analyzes pest and disease risk. 
    Hybrid Engine: Uses static rules for immediate threats + LLM for symptom interpretation.
    """
    threats = []
    actions = []
    risk_score = 0

    crop = data.crop.lower()
    stage = data.growth_stage.lower()
    crop_data = PEST_LIBRARY.get(crop, {})

    # 1. Physical Rule Engine (Immediate deterministic threats)
    if data.humidity > 80 and "high_humidity" in crop_data:
        entry = crop_data["high_humidity"]
        threats.append(f"🦠 {entry['threat']}")
        actions.append(entry["action"])
        risk_score += 35

    if data.temperature > 32 and "high_temp" in crop_data:
        entry = crop_data["high_temp"]
        threats.append(f"🐛 {entry['threat']}")
        actions.append(entry["action"])
        risk_score += 25

    # 2. Logic Multipliers (Rain/Stage)
    if data.rainfall_last_week > 50:
        risk_score += 15
        actions.append("⚠️ Heavy moisture detected: Increase field scouting for fungal spores.")

    # 3. AI Intelligence Layer (Symptom Diagnosis)
    # If the farmer provided symptoms, use the LLM to provide professional diagnosis
    ai_diagnosis = ""
    if data.symptoms_observed.strip():
        sys_prompt = "You are a professional plant pathologist and agricultural scientist."
        prompt = (
            f"Diagnose this crop issue for a farmer in {data.region}:\n"
            f"Crop: {data.crop} ({data.growth_stage} stage)\n"
            f"Symptoms: {data.symptoms_observed}\n"
            f"Weather: Temp {data.temperature}°C, Hum {data.humidity}%\n\n"
            f"Answer in {data.lang}. Provide:\n"
            f"1) PROBABLE CAUSE (Pest/Disease/Nutrient)\n"
            f"2) IMMEDIATE TREATMENT (Chemical/Organic)\n"
            f"3) RED LIST WARNINGS (If contagious)"
        )
        ai_diagnosis = get_llm_response(prompt, sys_prompt)
        risk_score += 20 # Symptom presence naturally raises risk
    
    risk_level = "CRITICAL" if risk_score > 70 else ("HIGH" if risk_score >= 50 else ("MEDIUM" if risk_score >= 25 else "LOW"))
    
    # 4. Final LLM Summary (Bilingual)
    summary_prompt = (
        f"Summarize the following pest risk for a farmer in {data.lang} (max 2 sentences):\n"
        f"Risk Level: {risk_level}, Threats: {', '.join(threats)}, AI Diagnosis summary: {ai_diagnosis[:100]}"
    )
    final_summary = get_llm_response(summary_prompt)

    return {
        "crop": data.crop,
        "stage": data.growth_stage,
        "risk_level": risk_level,
        "risk_score": min(100, risk_score),
        "threats": threats,
        "actions": actions,
        "ai_diagnosis": ai_diagnosis,
        "summary": final_summary
    }
