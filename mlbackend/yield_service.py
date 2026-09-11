from pydantic import BaseModel

class YieldInput(BaseModel):
    crop: str                     # rice, wheat, maize, cotton, sugarcane, etc.
    field_size: float             # acres
    soil_type: str                # Sandy, Clay, Loamy, Black, Red
    irrigation_type: str          # Rainfed, Canal, Drip, Sprinkler, Borewell
    fertilizer_used: str          # DAP, Urea, NPK, Organic, Mixed
    expected_rainfall: float      # mm this season
    temperature_avg: float        # average seasonal temp °C
    seed_variety: str = "local"   # HYV (High Yield Variety), local, hybrid
    lang: str = "en"

# Base yield data in quintals/acre for HYV under ideal conditions
BASE_YIELD = {
    "rice": {"HYV": 20.0, "hybrid": 22.0, "local": 12.0},
    "wheat": {"HYV": 18.0, "hybrid": 20.0, "local": 12.0},
    "maize": {"HYV": 22.0, "hybrid": 28.0, "local": 14.0},
    "cotton": {"HYV": 10.0, "hybrid": 14.0, "local": 6.0},
    "sugarcane": {"HYV": 350.0, "hybrid": 400.0, "local": 250.0},
    "soybean": {"HYV": 12.0, "hybrid": 15.0, "local": 8.0},
    "groundnut": {"HYV": 10.0, "hybrid": 12.0, "local": 6.0},
    "tomato": {"HYV": 80.0, "hybrid": 120.0, "local": 50.0},
}

def predict_yield(data: YieldInput) -> dict:
    """
    Predicts expected crop yield using agronomic factor scoring.
    """
    crop = data.crop.lower()
    variety = data.seed_variety.lower()

    base = BASE_YIELD.get(crop, {}).get(variety, BASE_YIELD.get(crop, {}).get("local", 10.0))

    efficiency_factor = 1.0
    advice = []

    # Irrigation adjustment
    irrig = data.irrigation_type.lower()
    if irrig == "drip":
        efficiency_factor *= 1.20
        advice.append("✅ Drip irrigation boosts efficiency by 20% through precise nutrient delivery.")
    elif irrig == "sprinkler":
        efficiency_factor *= 1.10
        advice.append("✅ Sprinkler irrigation adds ~10% yield efficiency vs rainfed.")
    elif irrig in ["canal", "borewell"]:
        efficiency_factor *= 1.05
    elif irrig == "rainfed":
        if data.expected_rainfall < 400:
            efficiency_factor *= 0.70
            advice.append("⚠️ Low rainfall (<400mm) expected for rainfed field — yield will be 30% below potential.")
        else:
            efficiency_factor *= 0.90
            advice.append("ℹ️ Rainfed cultivation: moderate yield achievable with adequate monsoon.")

    # Soil type adjustment
    soil = data.soil_type.lower()
    if soil == "loamy":
        efficiency_factor *= 1.10
        advice.append("✅ Loamy soil is optimal — excellent water retention and drainage balance.")
    elif soil == "clay":
        efficiency_factor *= 0.92
        advice.append("ℹ️ Clay soil is suitable but ensure drainage to prevent waterlogging.")
    elif soil == "sandy":
        efficiency_factor *= 0.82
        advice.append("⚠️ Sandy soil has low nutrient retention. Increase organic matter application.")
    elif soil in ["black", "black cotton"]:
        efficiency_factor *= 1.05
        advice.append("✅ Black cotton soil is excellent for cotton and soybean crops.")

    # Fertilizer adjustment
    fert = data.fertilizer_used.lower()
    if "npk" in fert or "mixed" in fert:
        efficiency_factor *= 1.08
        advice.append("✅ Balanced NPK application is expected to boost output by ~8%.")
    elif fert == "organic":
        efficiency_factor *= 1.03
        advice.append("ℹ️ Organic fertilizer supports long-term soil health but initial yield gain is ~3%.")
    elif fert == "urea":
        efficiency_factor *= 1.04

    # Temperature adjustment
    temp = data.temperature_avg
    if temp < 15 or temp > 42:
        efficiency_factor *= 0.70
        advice.append("❌ Extreme temperature detected. Significant yield reduction expected.")
    elif temp < 20:
        efficiency_factor *= 0.88
        advice.append("⚠️ Cool temperatures may slow growth — consider cold-tolerant varieties.")
    elif 25 <= temp <= 35:
        efficiency_factor *= 1.05
        advice.append("✅ Optimal temperature range for high yields.")

    predicted_yield_per_acre = round(base * efficiency_factor, 1)
    total_yield = round(predicted_yield_per_acre * data.field_size, 1)

    unit = "quintals" if crop not in ["sugarcane"] else "quintals"
    msp_approx = {
        "rice": 2183, "wheat": 2275, "maize": 1962, "cotton": 6620,
        "soybean": 4600, "groundnut": 6377, "sugarcane": 315, "tomato": 800
    }
    revenue_est = round(total_yield * msp_approx.get(crop, 2000))

    summary = (
        f"Expected yield for {data.field_size} acres of {data.crop.capitalize()} ({data.seed_variety} variety): "
        f"~{total_yield} {unit} (≈ ₹{revenue_est:,} at MSP rates)."
    )

    return {
        "crop": data.crop,
        "field_size_acres": data.field_size,
        "variety": data.seed_variety,
        "predicted_yield_per_acre": predicted_yield_per_acre,
        "total_yield": total_yield,
        "unit": unit,
        "estimated_revenue_inr": revenue_est,
        "efficiency_factor": round(efficiency_factor, 2),
        "advice": advice,
        "summary": summary
    }
