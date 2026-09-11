from pydantic import BaseModel

class SoilHealthInput(BaseModel):
    ph: float
    nitrogen_ppm: float
    phosphorus_ppm: float
    potassium_ppm: float
    organic_carbon_pct: float
    sand_pct: float = 40.0
    clay_pct: float = 30.0
    silt_pct: float = 30.0
    lang: str = "en"

def analyze_soil_health(data: SoilHealthInput):
    """
    Expert system for soil analysis.
    Takes into account nutrients AND physical texture (sand/clay/silt).
    """
    insights = []
    actions = []
    
    # 1. Texture Analysis (The foundation)
    if data.clay_pct > 40:
        texture = "Heavy Clay"
        insights.append(f"Soil Texture: {texture}. Excellent nutrient retention but high waterlogging risk.")
        actions.append("Ensure deep tillage to improve internal drainage.")
    elif data.sand_pct > 50:
        texture = "Sandy"
        insights.append(f"Soil Texture: {texture}. Fast drainage, but nutrients leach away quickly.")
        actions.append("Apply fertilizers in frequent, smaller doses (split application).")
    else:
        texture = "Loamy / Balanced"
        insights.append(f"Soil Texture: {texture}. Ideal structure for most agricultural crops.")

    # 2. pH Analysis
    if data.ph < 5.5:
        insights.append(f"pH level ({data.ph}) is Highly Acidic.")
        actions.append("Apply agricultural lime (calcium carbonate) to neutralize acidity.")
    elif data.ph > 8.5:
        insights.append(f"pH level ({data.ph}) is Highly Alkaline.")
        actions.append("Apply elemental sulfur or gypsum to reduce alkalinity.")
    
    # 3. Nutrient Intelligence
    if data.nitrogen_ppm < 40:
        insights.append("Low Nitrogen levels detected — critical for foliage synthesis.")
        actions.append("Consider a nitrogen-fixing cover crop (e.g. Alfalfa) for the next fallow.")
    
    if data.organic_carbon_pct < 0.6:
        insights.append("Organic Carbon (SOC) is below healthy threshold.")
        actions.append("Incorporate crop residues (mulching) instead of burning.")

    severity = "STABLE" if not actions else ("CRITICAL" if len(actions) > 2 else "WARNING")

    return {
        "texture": texture,
        "status": severity,
        "insights": insights,
        "rejuvenation_steps": actions
    }
