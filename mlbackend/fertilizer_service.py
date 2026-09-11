from typing import List, Optional
from pydantic import BaseModel

class FertilizerInput(BaseModel):
    crop_type: str
    crop_variety: str = "local"
    growth_stage: str # Sowing, Seedling, Vegetative, Flowering, Fruiting
    field_size: float # in acres
    soil_type: str # Red, Black, Sandy, Clay, Loamy
    prev_crop: str
    prev_fertilizers: str
    organic_manure: str # Farmyard, Compost, Vermicompost, None
    irrigation_type: str # Rainfed, Canal, Borewell, Drip, Sprinkler
    irrigation_frequency: str # Daily, Weekly, Only rainfall
    visual_indicators: str = ""
    lang: str = "en"

def calculate_fertilizer_needs(data: FertilizerInput):
    """
    Expert system to calculate exact fertilizer requirements.
    This logic mimics an agronomist's decision-making process.
    """
    recommendations = []
    reasoning = []
    
    # 1. Base NPK requirements based on crop and stage
    # (Simplified lookup table for demo purposes, can be expanded to 100+ crops)
    base_npk = {
        "rice": {"N": 100, "P": 50, "K": 50},
        "wheat": {"N": 120, "P": 60, "K": 40},
        "cotton": {"N": 150, "P": 75, "K": 75},
        "maize": {"N": 120, "P": 60, "K": 40}
    }
    
    crop = data.crop_type.lower()
    needs = base_npk.get(crop, {"N": 80, "P": 40, "K": 40})
    
    # 2. Adjust based on Growth Stage
    stage = data.growth_stage.lower()
    if stage == "sowing":
        rec_n = needs["N"] * 0.2
        rec_p = needs["P"] * 1.0 # High P for root development
        rec_k = needs["K"] * 0.5
        reasoning.append("High Phosphorus (P) recommended during sowing for strong root development.")
    elif stage == "vegetative":
        rec_n = needs["N"] * 0.5 # High N for leaf growth
        rec_p = needs["P"] * 0.0
        rec_k = needs["K"] * 0.2
        reasoning.append("High Nitrogen (N) is priority now for vigorous foliage and stem growth.")
    elif stage == "flowering":
        rec_n = needs["N"] * 0.2
        rec_p = needs["P"] * 0.2
        rec_k = needs["K"] * 1.0 # High K for fruit/flower quality
        reasoning.append("Potassium (K) boost recommended to improve fruit set and quality.")
    else: # Fruiting or default
        rec_n = needs["N"] * 0.1
        rec_p = needs["P"] * 0.0
        rec_k = needs["K"] * 0.5
        reasoning.append("Maintain moderate Potassium levels to support grain filling/fruiting.")

    # 3. Soil Adjustments
    soil = data.soil_type.lower()
    if soil == "sandy":
        reasoning.append("Sandy soil has high leaching; split Nitrogen into 4 applications instead of 2.")
        rec_n *= 1.1 # 10% more due to leaching
    elif soil == "clay":
        reasoning.append("Clay soil retains nutrients well; ensure proper drainage to avoid root rot.")
        rec_n *= 0.9 # 10% less
        
    # 4. Organic History Adjustment
    if "manure" in data.organic_manure.lower() or "compost" in data.organic_manure.lower():
        rec_n -= 10 # Deduct 10kg/acre equivalent from manure
        reasoning.append("Organic manure history allows for a 10% reduction in synthetic Nitrogen.")

    # 5. Irrigation Adjustment
    if data.irrigation_type.lower() == "drip":
        reasoning.append("Drip irrigation detected: Use water-soluble fertilizers (Fertigation) for 30% higher efficiency.")
    elif data.irrigation_type.lower() == "rainfed":
        reasoning.append("Rainfed field: Time fertilizer application strictly with light rains; avoid during heavy downpours.")

    # Final Recommendation Construction
    recommendations.append(f"Recommended Nitrogen (N): {round(rec_n, 1)} kg/acre")
    recommendations.append(f"Recommended Phosphorus (P): {round(rec_p, 1)} kg/acre")
    recommendations.append(f"Recommended Potassium (K): {round(rec_k, 1)} kg/acre")
    
    return {
        "crop": data.crop_type,
        "stage": data.growth_stage,
        "recommendations": recommendations,
        "scientific_reasoning": reasoning,
    }
