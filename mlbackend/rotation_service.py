from pydantic import BaseModel
from typing import List

class RotationInput(BaseModel):
    current_crop: str       # rice, wheat, maize, cotton, soybean, etc.
    soil_type: str          # Sandy, Clay, Loamy, Black, Red
    irrigation_type: str    # Rainfed, Canal, Drip, Borewell, Sprinkler
    region: str = "Central India"
    previous_crop: str = ""  # Last season's crop (optional)
    lang: str = "en"

# Rotation recommendations: current crop → [S1, S2, S3] recommended next crops
ROTATION_DB = {
    "rice": {
        "default": ["Wheat", "Mustard", "Potato"],
        "legume_fix": "Lentil or Chickpea",
        "reasoning": [
            "Rice is heavy on Nitrogen; follow with Wheat which can utilize residual nutrients.",
            "Introducing Legume in Season 3 (Chickpea/Lentil) will naturally restore Nitrogen through atmospheric fixation.",
            "Avoid planting Rice consecutively — increases bacterial leaf blight risk and depletes Zinc."
        ]
    },
    "wheat": {
        "default": ["Rice", "Soybean", "Maize"],
        "legume_fix": "Mung Bean or Black Gram",
        "reasoning": [
            "Wheat → Rice is the classic Kharif-Rabi rotation in Indo-Gangetic plains.",
            "Introducing Soybean (Season 2) adds ~35kg N/ha back to the soil.",
            "Avoid continuous wheat — increases Karnal Bunt and Yellow Rust pressure."
        ]
    },
    "maize": {
        "default": ["Soybean", "Cowpea", "Sunflower"],
        "legume_fix": "Cowpea",
        "reasoning": [
            "Maize is a heavy feeder; Soybean rotation restores nitrogen and breaks pest cycles.",
            "Cowpea as cover crop (Season 2) adds green manure biomass and suppresses weeds.",
            "Sunflower (Season 3) has deep roots that break soil compaction left by Maize."
        ]
    },
    "cotton": {
        "default": ["Wheat", "Groundnut", "Green Gram"],
        "legume_fix": "Green Gram",
        "reasoning": [
            "Cotton exhausts soil heavily — Wheat rotation uses less water and restores structure.",
            "Groundnut (Season 2) fixes nitrogen and provides economic value.",
            "Green Gram as a fallow crop (Season 3) is a fast nitrogen fixer and can be incorporated as green manure."
        ]
    },
    "soybean": {
        "default": ["Maize", "Wheat", "Sorghum"],
        "legume_fix": "None required (Soybean is a legume)",
        "reasoning": [
            "Soybean fixes its own Nitrogen — rotate with Maize (Season 1) which benefits from the residual N.",
            "Wheat rotation (Season 2) takes advantage of Soybean's deep Phosphorus cycling.",
            "Sorghum (Season 3) is drought-tolerant and helps break Soybean pest cycles."
        ]
    },
    "sugarcane": {
        "default": ["Legumes (Cowpea/Mung)", "Wheat", "Vegetable crops"],
        "legume_fix": "Cowpea",
        "reasoning": [
            "Sugarcane depletes potassium significantly — plant Legumes first to restore soil biology.",
            "Wheat rotation is economically viable in cooler follow-on season.",
            "Vegetable crops utilize the well-broken soil left after sugarcane ratoon cutting."
        ]
    },
    "groundnut": {
        "default": ["Cotton", "Jowar", "Sesame"],
        "legume_fix": "None required (Groundnut is a legume)",
        "reasoning": [
            "Groundnut enriches soil with Nitrogen — Cotton rotation benefits from this N boost.",
            "Jowar (Sorghum) rotation breaks Tikka leaf spot disease cycle that affects groundnut.",
            "Sesame (Season 3) is drought-tolerant and very profitable in rainfed BLACK soil regions."
        ]
    }
}

try:
    from .llm_service import get_llm_response
except ImportError:
    from llm_service import get_llm_response


def recommend_rotation(data: RotationInput) -> dict:
    """
    Generates a 3-season smart crop rotation plan.
    Hybrid Engine: Uses expert lookup tables + AI dynamic reasoning.
    """
    crop = data.current_crop.lower()
    entry = ROTATION_DB.get(crop)

    if not entry:
        entry = {
            "default": ["Legume (Chickpea)", "Cereal (Maize)", "Oilseed (Mustard)"],
            "legume_fix": "Cowpea",
            "reasoning": ["Standard sustainable rotation logic applies."]
        }

    seasons = entry["default"]
    
    # AI reasoning layer (The 'Intelligence' part)
    sys_prompt = "You are a senior agronomist at AgriSaathi. Plan sustainable crop rotations for Indian farmers."
    prompt = (
        f"Design a high-yield, soil-rejuvenating 3-season rotation plan after {data.current_crop} "
        f"on {data.soil_type} soil near {data.region} in India.\n"
        f"Current Crop: {data.current_crop}\n"
        f"Soil: {data.soil_type}\n"
        f"Irrigation: {data.irrigation_type}\n\n"
        f"Provide a detailed reason for each chosen crop in the sequence in {data.lang}."
    )
    ai_reasoning = get_llm_response(prompt, sys_prompt)

    rotation_plan = [
        f"🌱 Season 1 (Current): {data.current_crop.capitalize()}",
        f"🌾 Season 2 (Rabi): {seasons[0]}",
        f"🌿 Season 3 (Zaid): {seasons[1]}",
        f"🫘 Season 4 (Kharif Next): {seasons[2] if len(seasons) > 2 else entry['legume_fix']}"
    ]

    summary = (
        f"Strategy: {data.current_crop.capitalize()} → {seasons[0]} → {seasons[1]}. "
        f"This cycle restores {entry['legume_fix']} and optimizes {data.soil_type} health."
    )

    return {
        "current_crop": data.current_crop,
        "soil_type": data.soil_type,
        "irrigation_type": data.irrigation_type,
        "rotation_plan": rotation_plan,
        "ai_reasoning": ai_reasoning,
        "nitrogen_fixer": entry["legume_fix"],
        "summary": summary
    }
