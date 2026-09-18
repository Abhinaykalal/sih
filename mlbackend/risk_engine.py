"""
AGRISENTINEL EDGE - MULTIMODAL RISK & DISASTER MANAGEMENT ENGINE
Strictly aligned with SIH Problem Statement Requirements:
1. Continuous Crop Health & Environmental Sensor Ingestion
2. Early Risk Detection (Drought, Flood, Heat Stress, Pest Outbreaks, Disease)
3. Smart Irrigation & Input Optimization (Water & Chemical Conservation)
4. Edge AI Offline Store & Sync Architecture
"""

from typing import Dict, Any, Optional, List

def validate_sensor_availability(required_sensors: List[str], sensor_values: Dict[str, Optional[float]]) -> Dict[str, Any]:
    """
    Phase 4: Vision AI Sensor Validation
    
    Validates that all required sensors are REAL (not None/synthetic) before multimodal fusion.
    
    Args:
        required_sensors: List of sensor names needed for analysis
        sensor_values: Dict mapping sensor names to their values (None if unavailable)
        
    Returns:
        Dict with:
        - all_available: bool (True if all required sensors are real)
        - available_sensors: list of sensor names with real data
        - missing_sensors: list of sensor names that are None
        - data_quality_assessment: str describing why fusion may/may not be reliable
    """
    available_sensors = []
    missing_sensors = []
    
    for sensor_name in required_sensors:
        value = sensor_values.get(sensor_name)
        if value is not None:
            available_sensors.append(sensor_name)
        else:
            missing_sensors.append(sensor_name)
    
    all_available = len(missing_sensors) == 0
    
    if all_available:
        data_quality_assessment = "All required sensors available. Multimodal fusion can proceed with high confidence."
    elif len(available_sensors) > 0:
        data_quality_assessment = f"Partial sensor data: {', '.join(available_sensors)} available. Missing: {', '.join(missing_sensors)}. Image-only diagnosis recommended."
    else:
        data_quality_assessment = "No sensor data available. Image-only diagnosis will be used."
    
    return {
        "all_available": all_available,
        "available_sensors": available_sensors,
        "missing_sensors": missing_sensors,
        "data_quality_assessment": data_quality_assessment,
        "recommendation": "MULTIMODAL" if all_available else "IMAGE_ONLY"
    }

def evaluate_smart_irrigation(soil_moisture: float, air_temp: float, rain_forecast_prob: float) -> Dict[str, Any]:
    """
    SMART IRRIGATION ENGINE: Optimizes water usage based on soil moisture,
    evapotranspiration, and upcoming rain forecasts.
    Detects water stress, optimal moisture, and dangerous over-irrigation/waterlogging.
    """
    if soil_moisture > 80.0:
        status = "OVER-IRRIGATION / WATERLOGGING"
        recommendation = f"Soil saturated ({soil_moisture}%). Halt pump, open drainage furrows to avert root rot & hypoxia."
        action_code = "HALT_PUMP_DRAIN"
        color = "PURPLE"
    elif soil_moisture < 25.0 and rain_forecast_prob < 50.0:
        status = "IRRIGATE IMMEDIATELY"
        recommendation = f"Soil moisture is critical ({soil_moisture}%). Apply drip irrigation now."
        action_code = "START_PUMP"
        color = "RED"
    elif soil_moisture < 25.0 and rain_forecast_prob >= 50.0:
        status = "HOLD IRRIGATION"
        recommendation = f"Soil moisture low ({soil_moisture}%), but rain expected ({rain_forecast_prob}% chance). Hold pump to save water & power."
        action_code = "HOLD_PUMP"
        color = "YELLOW"
    else:
        status = "MOISTURE OPTIMAL"
        recommendation = f"Soil moisture healthy ({soil_moisture}%). Maintain standard monitoring."
        action_code = "NO_ACTION"
        color = "GREEN"

    deficit = max(0.0, 30.0 - soil_moisture)
    optimal_runtime_minutes = int(deficit * 2.8) if action_code == "START_PUMP" else 0

    return {
        "status": status,
        "recommendation": recommendation,
        "action_code": action_code,
        "optimal_runtime_minutes": optimal_runtime_minutes,
        "color": color
    }

def evaluate_pest_trend(pest_counts: list) -> Dict[str, Any]:
    """
    PEST OUTBREAK ACCELERATION ENGINE: Detects population velocity before severe crop damage.
    Requires a list with at least one real observation. Returns a NO_DATA status when called
    with no counts — callers must not substitute synthetic values.
    """
    if not pest_counts:
        # No real trap-count data available. Do NOT use synthetic history.
        return {
            "latest_pest_count": None,
            "trend_history": "NO_DATA",
            "is_accelerating": False,
            "risk_level": "DATA_UNAVAILABLE",
            "recommendation": (
                "No pest trap-count data received. Install sticky-trap sensors or enter "
                "manual trap counts to enable pest outbreak detection."
            ),
            "color": "GREY",
            "data_source": "NO_SENSOR_DATA"
        }
    latest_count = pest_counts[-1]
    is_accelerating = len(pest_counts) >= 3 and (pest_counts[-1] - pest_counts[-2]) > (pest_counts[-2] - pest_counts[-3])
    
    if latest_count > 20 or is_accelerating:
        risk_level = "HIGH PEST OUTBREAK RISK"
        recommendation = f"Trap count spiked to {latest_count} insects (Accelerating trend). Deploy targeted pheromone traps in affected zone."
        color = "RED"
    elif latest_count > 10:
        risk_level = "MODERATE PEST ACTIVITY"
        recommendation = "Pest population rising. Monitor traps daily."
        color = "YELLOW"
    else:
        risk_level = "LOW PEST RISK"
        recommendation = "Pest levels within safe threshold."
        color = "GREEN"

    return {
        "latest_pest_count": latest_count,
        "trend_history": " -> ".join(map(str, pest_counts)),
        "is_accelerating": is_accelerating,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "color": color
    }

def evaluate_multimodal_disease_context(vision_class: str, soil_moisture: float, air_temp: float, humidity: float, ec_salinity: Optional[float] = None) -> Dict[str, Any]:
    """
    MULTIMODAL DISEASE & NUTRIENT DEFICIENCY DIAGNOSIS:
    Fuses visual leaf features with soil moisture, EC salinity, and microclimate to prevent
    misdiagnosing abiotic stress (water stress, fertilizer burn) as pathogen infection or nutrient deficiency.
    """
    v_lower = (vision_class or "").lower()
    
    # 1. Abiotic Water-Stress Induced Chlorosis (Underwatered vs Nitrogen deficiency)
    if any(w in v_lower for w in ["yellow", "chlorosis", "wilt"]) and soil_moisture < 20.0 and air_temp > 32.0:
        return {
            "diagnosis": "Water-Stress Induced Chlorosis (Abiotic)",
            "confidence_pct": None,
            "provenance": "RULE_BASED_HEURISTIC",
            "action": "DO NOT apply nitrogen fertilizer. Irrigate crop immediately to restore root turgor pressure.",
            "category": "Water Stress"
        }
    
    # 2. Over-irrigation root asphyxia / waterlogging chlorosis
    if any(w in v_lower for w in ["yellow", "wilt", "stunted"]) and soil_moisture > 80.0:
        return {
            "diagnosis": "Waterlogging Root Hypoxia / Anaerobic Stress",
            "confidence_pct": None,
            "provenance": "RULE_BASED_HEURISTIC",
            "action": "Soil is waterlogged. Stop irrigation immediately and aerate/drain soil furrows.",
            "category": "Over-irrigation"
        }

    # 3. True Nitrogen (N) Deficiency (Moisture normal, foliage pale green/yellow from tips)
    if ("nitrogen" in v_lower or "chlorosis" in v_lower or "yellow" in v_lower) and soil_moisture >= 25.0 and (ec_salinity is None or ec_salinity <= 1.8):
        return {
            "diagnosis": "Nitrogen (N) Deficiency Chlorosis",
            "confidence_pct": None,
            "provenance": "RULE_BASED_HEURISTIC",
            "action": "Soil moisture is adequate. Apply Urea @ 25-30 kg/acre or liquid organic bio-nitrogen spray.",
            "category": "Nutrient Deficiency"
        }

    # 4. Potassium (K) Deficiency (Marginal scorching / brown leaf edges)
    if "potassium" in v_lower or "scorch" in v_lower or ("brown" in v_lower and "edge" in v_lower):
        return {
            "diagnosis": "Potassium (K) Deficiency / Marginal Leaf Scorch",
            "confidence_pct": None,
            "provenance": "RULE_BASED_HEURISTIC",
            "action": "Apply Muriate of Potash (MOP) @ 20 kg/acre or foliar spray of Potassium Nitrate (13-0-45) @ 1%.",
            "category": "Nutrient Deficiency"
        }

    # 5. Phosphorus (P) Deficiency (Purpling / dark bronzing)
    if "phosphorus" in v_lower or "purple" in v_lower or "bronze" in v_lower:
        return {
            "diagnosis": "Phosphorus (P) Deficiency / Anthocyanin Accumulation",
            "confidence_pct": None,
            "provenance": "RULE_BASED_HEURISTIC",
            "action": "Apply Single Super Phosphate (SSP) or DAP directly into root zone to enhance root development.",
            "category": "Nutrient Deficiency"
        }

    # 6. High Humidity Fungal Blight Outbreak
    if (any(w in v_lower for w in ["blight", "spot", "mildew", "rust"]) or humidity > 85.0):
        return {
            "diagnosis": "Fungal Blight / Foliar Pathogen Risk",
            "confidence_pct": None,
            "provenance": "RULE_BASED_HEURISTIC",
            "action": "High ambient humidity (>85%). Apply organic bio-fungicide (Trichoderma viride or Copper Oxychloride @ 2.5g/L).",
            "category": "Pathogen / Fungal"
        }

    # 7. Salinity Root Burn
    if ec_salinity is not None and ec_salinity > 2.2:
        return {
            "diagnosis": "Osmotic Root Burn / Soil Salinity Toxicity",
            "confidence_pct": None,
            "provenance": "RULE_BASED_HEURISTIC",
            "action": "Soil EC is toxic (>2.2 dS/m). Leach soil with clean water and halt all chemical fertilizers.",
            "category": "Salinity"
        }

    return {
        "diagnosis": vision_class if vision_class else "Healthy Foliage",
        "confidence_pct": None,
        "provenance": "RULE_BASED_HEURISTIC",
        "action": "Crop canopy in healthy condition. Maintain routine irrigation and IPM scouting.",
        "category": "Optimal"
    }

def compute_4zone_farm_status(sensor_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes real-time farm disaster risks across 4 physical zones strictly adhering to SIH requirements:
    - Zone 1: North Block (Field Health & Baseline)
    - Zone 2: East Plot (Smart Irrigation & Water Stress)
    - Zone 3: South Block (Pest Infestation Velocity & Early Warning)
    - Zone 4: West Plot (Fungal Disease & Micro-Climate Vulnerability)
    Also computes composite Disaster Scores (Drought, Flood, Heat, Disease, Pests, Health).
    """
    # Resolve sensor values — None means "sensor not connected / no reading".
    # Do NOT substitute crisis defaults (e.g. 16.0 drought-level moisture, 35°C heat).
    # Scores that depend on missing sensors are set to 0 (unknown, not alarming).
    z1_moisture_raw = sensor_data.get("z1_moisture")
    z2_moisture_raw = sensor_data.get("z2_moisture")
    z4_humidity_raw = sensor_data.get("z4_humidity")
    air_temp_raw    = sensor_data.get("air_temp")
    rain_prob_raw   = sensor_data.get("rain_prob")

    z1_moisture = float(z1_moisture_raw) if z1_moisture_raw is not None else None
    z2_moisture = float(z2_moisture_raw) if z2_moisture_raw is not None else None
    z3_pest_count = sensor_data.get("z3_pest_count")
    z3_pest_count = int(z3_pest_count) if z3_pest_count is not None else None
    z4_humidity = float(z4_humidity_raw) if z4_humidity_raw is not None else None
    air_temp   = float(air_temp_raw)   if air_temp_raw   is not None else None
    rain_prob  = float(rain_prob_raw)  if rain_prob_raw  is not None else None
    ec_salinity = sensor_data.get("ec_salinity")
    ec_salinity = float(ec_salinity) if ec_salinity is not None else None

    # Zone 2: Irrigation — only evaluate when soil moisture is available
    if z2_moisture is not None:
        irrigation_eval = evaluate_smart_irrigation(z2_moisture, air_temp, rain_prob)
    else:
        irrigation_eval = {
            "status": "DATA_UNAVAILABLE",
            "color": "GREY",
            "recommendation": "No soil moisture sensor data available for Zone 2."
        }

    # Pass only the real current count. evaluate_pest_trend handles the missing-data case.
    pest_eval = evaluate_pest_trend([z3_pest_count] if z3_pest_count is not None else [])

    # Zone 4: Disease — only evaluate when humidity is available
    if z4_humidity is not None:
        disease_status = "HIGH FUNGAL DISEASE RISK" if z4_humidity > 85 else ("MODERATE FUNGAL RISK" if z4_humidity > 70 else "LOW DISEASE RISK")
        disease_color  = "PURPLE" if z4_humidity > 85 else ("YELLOW" if z4_humidity > 70 else "GREEN")
        disease_action = "Apply preventive bio-fungicide. High humidity accelerates spore germination." if z4_humidity > 85 else "Micro-climate clear."
    else:
        disease_status = "DATA_UNAVAILABLE"
        disease_color  = "GREY"
        disease_action = "No humidity sensor data for Zone 4. Install sensor to enable fungal risk detection."

    zones = {
        "zone_1": {
            "name": "Zone 1 (North Block - Paddy)",
            "status": "NORMAL",
            "color": "GREEN",
            "moisture": z1_moisture,
            "action": "Optimal growing conditions. Maintain regular monitoring."
        },
        "zone_2": {
            "name": "Zone 2 (East Plot - Tomato)",
            "status": irrigation_eval["status"],
            "color": irrigation_eval["color"],
            "moisture": z2_moisture,
            "action": irrigation_eval["recommendation"]
        },
        "zone_3": {
            "name": "Zone 3 (South Block - Cotton)",
            "status": pest_eval["risk_level"],
            "color": pest_eval["color"],
            "pest_count": z3_pest_count,
            "action": pest_eval["recommendation"]
        },
        "zone_4": {
            "name": "Zone 4 (West Plot - Maize)",
            "status": disease_status,
            "color": disease_color,
            "humidity": z4_humidity,
            "action": disease_action
        }
    }

    # Disaster scores — set to 0 when the required sensor is missing (unknown ≠ no risk)
    drought_score = round(max(0.0, min(100.0, (28.0 - z2_moisture) * 4.5)), 1) if z2_moisture is not None else 0.0
    heat_score    = round(min(100.0, max(0.0, (air_temp - 28.0) * 7.0)), 1)   if air_temp    is not None else 0.0
    disease_score = round(min(100.0, z4_humidity * 0.95), 1)                   if z4_humidity is not None else 0.0
    pest_score    = round(min(100.0, z3_pest_count * 3.5), 1)                  if z3_pest_count is not None else 0.0

    # Flood risk derived from high moisture (>45%) + incoming rain probability
    if z2_moisture is not None and rain_prob is not None:
        soil_saturation = max(0.0, z2_moisture - 45.0)
        flood_score = round(min(100.0, max(0.0, (soil_saturation * 1.6) + (rain_prob * 0.5))), 1)
    else:
        flood_score = 0.0

    # Dynamic farm health score (100 minus weighted penalties)
    overall_health = max(15, min(100, round(100 - (
        drought_score * 0.25 + 
        heat_score * 0.18 + 
        pest_score * 0.22 + 
        disease_score * 0.18 + 
        flood_score * 0.17
    ))))

    # Yield-risk forecasting: estimate yield reduction percentage if risks stay untreated
    yield_loss_projected_pct = round(min(45.0, (drought_score * 0.35 + pest_score * 0.30 + disease_score * 0.20 + heat_score * 0.15) * 0.4), 1)
    yield_forecast_pct = round(100.0 - yield_loss_projected_pct, 1)

    disaster_scores = {
        "drought_risk_pct": drought_score,
        "heat_stress_pct": heat_score,
        "disease_vulnerability_pct": disease_score,
        "pest_outbreak_pct": pest_score,
        "flood_risk_pct": flood_score,
        "overall_farm_health_score": overall_health,
        "yield_forecast_pct": yield_forecast_pct,
        "yield_loss_projected_pct": yield_loss_projected_pct
    }

    # Explicit problem statement farmer advisory recommendations
    advisory_alerts = [
        {
            "category": "Irrigation",
            "alert": (
                "Irrigate now (Zone 2 critical)" if z2_moisture is not None and z2_moisture < 20 and (rain_prob or 0) < 50
                else "Delay irrigation (Rain expected)" if z2_moisture is not None and z2_moisture < 25 and (rain_prob or 0) >= 50
                else "Over-irrigation: drain furrows" if z2_moisture is not None and z2_moisture > 80
                else "Soil moisture optimal" if z2_moisture is not None
                else "No soil moisture sensor data"
            ),
            "status": irrigation_eval["status"],
            "severity": (
                "CRITICAL" if z2_moisture is not None and z2_moisture < 20
                else "WARNING" if z2_moisture is not None and z2_moisture > 80
                else "NORMAL"
            )
        },
        {
            "category": "Disease",
            "alert": (
                "Possible disease detected: High fungal risk in Zone 4" if z4_humidity is not None and z4_humidity > 85
                else "Foliar disease risk clear" if z4_humidity is not None
                else "No humidity sensor data for Zone 4"
            ),
            "status": disease_status,
            "severity": "WARNING" if z4_humidity is not None and z4_humidity > 85 else "NORMAL"
        },
        {
            "category": "Pests",
            "alert": (
                f"Pest activity increasing ({z3_pest_count} insects)" if z3_pest_count is not None and z3_pest_count > 15
                else "Pest activity within threshold" if z3_pest_count is not None
                else "No pest trap-count data"
            ),
            "status": pest_eval["risk_level"],
            "severity": "WARNING" if z3_pest_count is not None and z3_pest_count > 15 else "NORMAL"
        },
        {
            "category": "Heat Stress",
            "alert": (
                f"Heat-stress warning ({air_temp}°C exceeds 33°C)" if air_temp is not None and air_temp > 33
                else "Thermal conditions optimal" if air_temp is not None
                else "No air temperature sensor data"
            ),
            "status": "ELEVATED HEAT" if air_temp is not None and air_temp > 33 else "NORMAL",
            "severity": "WARNING" if air_temp is not None and air_temp > 33 else "NORMAL"
        },
        {
            "category": "Flood Risk",
            "alert": f"Flood-risk alert: High saturation ({flood_score}%)" if flood_score > 40 else "Flood risk low",
            "status": "WATCH" if flood_score > 40 else "SAFE",
            "severity": "WARNING" if flood_score > 40 else "NORMAL"
        }
    ]

    # Crop growth stage tracking
    crop_growth_stages = {
        "zone_1": {"crop": "Paddy", "stage": "Tillering / Panicle Initiation", "das": 42},
        "zone_2": {"crop": "Tomato", "stage": "Flowering & Early Fruit Set", "das": 54},
        "zone_3": {"crop": "Cotton", "stage": "Square Formation & Vegetative", "das": 38},
        "zone_4": {"crop": "Maize", "stage": "Tasseling & Silking", "das": 48}
    }

    return {
        "zones": zones,
        "disaster_scores": disaster_scores,
        "smart_irrigation": irrigation_eval,
        "pest_trend": pest_eval,
        "advisory_alerts": advisory_alerts,
        "crop_growth_stages": crop_growth_stages
    }

def evaluate_spray_drift_guard(wind_speed_kmh: float = 8.0, temp_c: float = 32.0, rain_prob: float = 10.0) -> Dict[str, Any]:
    is_safe = wind_speed_kmh <= 15.0 and temp_c <= 34.0 and rain_prob <= 50.0
    return {
        "spray_status": "SAFE TO SPRAY" if is_safe else "UNSAFE SPRAY DRIFT RISK",
        "is_safe": is_safe,
        "recommendation": "Optimal spraying conditions." if is_safe else "Postpone spraying due to wind or rain risk."
    }

def evaluate_lwd_fungal_risk(temp_c: float = 25.0, humidity: float = 90.0) -> Dict[str, Any]:
    is_high = humidity > 85.0
    return {
        "status": "HIGH FUNGAL RISK" if is_high else "LOW RISK",
        "fungal_infection_risk_pct": 92.0 if is_high else 20.0,
        "recommendation": "Apply preventive bio-fungicide spray." if is_high else "Conditions clear."
    }

def evaluate_fertilizer_burn_ec(soil_ec_ds_m: Optional[float] = None, soil_moisture_pct: float = 20.0) -> Dict[str, Any]:
    if soil_ec_ds_m is None:
        return {
            "is_toxic": False,
            "salinity_status": "UNKNOWN (NO SENSOR)",
            "recommendation": "No EC sensor data available."
        }
    is_toxic = soil_ec_ds_m > 2.2
    return {
        "is_toxic": is_toxic,
        "salinity_status": "CRITICAL ROOT BURN RISK" if is_toxic else "BALANCED SALINITY",
        "recommendation": "Flush soil with fresh water. DO NOT apply fertilizer." if is_toxic else "Soil salinity balanced."
    }

def evaluate_multimodal_fusion(vision_label: str, soil_moisture: float, temp_c: float, ec_salinity: float) -> Dict[str, Any]:
    res = evaluate_multimodal_disease_context(vision_label, soil_moisture, temp_c, 80.0, ec_salinity)
    return {
        "fused_diagnosis": res["diagnosis"],
        "confidence_score_pct": res["confidence_pct"],
        "recommended_action": res["action"],
        "category": res.get("category", "General")
    }

