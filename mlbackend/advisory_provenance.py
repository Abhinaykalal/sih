"""
AgriSaathi AI — Advisory Data Provenance & Null-Safe Formatter Module
=====================================================================
Ensures granular data provenance tracking, null-safe weather rendering,
and transparent advisory display per agricultural extension standards.

Categories:
- LIVE_SENSOR
- LIVE_WEATHER
- HISTORICAL_DATABASE
- SOURCE_BACKED_KNOWLEDGE
- RULE_BASED
- MODEL_PREDICTION
- EXPERIMENTAL
- SIMULATED
- UNAVAILABLE
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class DataProvenance(str, Enum):
    LIVE_SENSOR = "LIVE_SENSOR"
    LIVE_WEATHER = "LIVE_WEATHER"
    HISTORICAL_DATABASE = "HISTORICAL_DATABASE"
    SOURCE_BACKED_KNOWLEDGE = "SOURCE_BACKED_KNOWLEDGE"
    RULE_BASED = "RULE_BASED"
    MODEL_PREDICTION = "MODEL_PREDICTION"
    EXPERIMENTAL = "EXPERIMENTAL"
    SIMULATED = "SIMULATED"
    UNAVAILABLE = "UNAVAILABLE"


class FieldTelemetryItem(BaseModel):
    value: Optional[Union[float, int, str]] = None
    unit: Optional[str] = None
    provenance: str = DataProvenance.UNAVAILABLE.value
    device_id: Optional[str] = None
    timestamp: Optional[str] = None
    freshness: str = "CURRENT"  # "CURRENT", "STALE", "OFFLINE"


class WeatherStatusItem(BaseModel):
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    rainfall_mm: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    status: str = "UNAVAILABLE"  # "AVAILABLE", "UNAVAILABLE", "STALE", "TEMPORARILY_UNAVAILABLE"
    provenance: str = DataProvenance.UNAVAILABLE.value
    message: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    last_updated: Optional[str] = None


class KnowledgeStatementItem(BaseModel):
    statement: str
    provenance: str = DataProvenance.SOURCE_BACKED_KNOWLEDGE.value
    source_title: str
    source_organization: Optional[str] = None
    source_url: Optional[str] = None
    publication_date: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    crop: Optional[str] = None
    growth_stage: Optional[str] = None
    region: Optional[str] = None
    citation_id: Optional[str] = None
    source_status: str = "VERIFIED"  # "VERIFIED" or "UNVERIFIED"
    limitations: List[str] = Field(default_factory=list)


class DecisionItem(BaseModel):
    result: str
    provenance: str = DataProvenance.RULE_BASED.value
    explanation: str
    inputs_used: List[str] = Field(default_factory=list)
    inputs_missing: List[str] = Field(default_factory=list)
    urgency: Optional[str] = None
    target_water_mm: Optional[float] = None
    # Traceability fields surfaced in rendered advisory (audit items 169-173)
    threshold_source: Optional[str] = None
    validation_status: str = "UNVALIDATED_AGAINST_FIELD_OUTCOMES"


class AdvisoryProvenanceResponse(BaseModel):
    advisory_title: str
    crop: str
    growth_stage: str
    field_status: Dict[str, FieldTelemetryItem]
    weather: WeatherStatusItem
    knowledge: List[KnowledgeStatementItem]
    decision: DecisionItem
    data_quality: Dict[str, str]
    overall_status: str  # "GROUNDED", "PARTIALLY_GROUNDED", "SIMULATED", "UNAVAILABLE"


def format_weather_display(weather_data: Optional[Dict[str, Any]], is_demo_mode: bool = False) -> WeatherStatusItem:
    """
    Null-safe formatter for weather data.
    Never renders 'Temp: None°C' or 'null°C' or inserts arbitrary fake numbers.
    """
    if weather_data is None:
        return WeatherStatusItem(
            temperature_c=None,
            status="UNAVAILABLE",
            provenance=DataProvenance.UNAVAILABLE.value,
            message="Weather data is not available.",
            description="Not available",
            reason="No verified weather reading received"
        )

    # Check for provider failure / error flag
    status = weather_data.get("status", "").upper()
    if status == "TEMPORARILY_UNAVAILABLE" or "error" in weather_data:
        return WeatherStatusItem(
            temperature_c=None,
            status="TEMPORARILY_UNAVAILABLE",
            provenance=DataProvenance.UNAVAILABLE.value,
            message=weather_data.get("error", "Weather provider temporarily unavailable"),
            description="Temporarily unavailable",
            reason=weather_data.get("reason", "Weather provider connection failed")
        )

    # Check for stale data
    is_stale = weather_data.get("is_stale", False)
    last_updated = weather_data.get("last_updated") or weather_data.get("timestamp")

    temp = weather_data.get("temp")
    # If temp is inside OWM 'main' subdict:
    if temp is None and isinstance(weather_data.get("main"), dict):
        temp = weather_data["main"].get("temp")

    # If temperature is completely missing
    if temp is None:
        return WeatherStatusItem(
            temperature_c=None,
            status="UNAVAILABLE",
            provenance=DataProvenance.UNAVAILABLE.value,
            message="Weather temperature data is missing.",
            description="Not available",
            reason="No temperature reading in weather payload",
            last_updated=last_updated
        )

    try:
        temp_float = float(temp)
    except (ValueError, TypeError):
        return WeatherStatusItem(
            temperature_c=None,
            status="UNAVAILABLE",
            provenance=DataProvenance.UNAVAILABLE.value,
            message="Invalid temperature reading received.",
            description="Not available",
            reason="Non-numeric temperature reading received"
        )

    humidity = weather_data.get("humidity")
    if humidity is None and isinstance(weather_data.get("main"), dict):
        humidity = weather_data["main"].get("humidity")

    rain = weather_data.get("rainfall_last_3h", weather_data.get("rain", 0.0))
    if isinstance(rain, dict):
        rain = rain.get("1h", rain.get("3h", 0.0))

    description = weather_data.get("description")
    if not description and isinstance(weather_data.get("weather"), list) and weather_data["weather"]:
        description = weather_data["weather"][0].get("description")
    if not description:
        description = "Clear / Partly cloudy"

    if is_stale:
        return WeatherStatusItem(
            temperature_c=round(temp_float, 1),
            humidity_pct=float(humidity) if humidity is not None else None,
            rainfall_mm=float(rain) if rain is not None else 0.0,
            status="STALE",
            provenance=DataProvenance.HISTORICAL_DATABASE.value if not is_demo_mode else DataProvenance.SIMULATED.value,
            message="Weather data is stale.",
            description=f"Stale data: {description}",
            reason=f"Last updated: {last_updated or 'Unknown'}",
            last_updated=last_updated
        )

    prov = DataProvenance.SIMULATED.value if is_demo_mode else DataProvenance.LIVE_WEATHER.value

    return WeatherStatusItem(
        temperature_c=round(temp_float, 1),
        humidity_pct=float(humidity) if humidity is not None else None,
        rainfall_mm=float(rain) if rain is not None else 0.0,
        wind_speed_ms=weather_data.get("wind_speed"),
        status="AVAILABLE",
        provenance=prov,
        message="Live verified weather",
        description=str(description).capitalize(),
        reason="Verified active reading",
        last_updated=last_updated or datetime.now(timezone.utc).isoformat()
    )


def determine_overall_status(
    field_status: Dict[str, FieldTelemetryItem],
    weather: WeatherStatusItem,
    knowledge: List[KnowledgeStatementItem],
    is_demo_mode: bool = False
) -> str:
    """Computes transparent overall grounding status."""
    if is_demo_mode:
        return "SIMULATED"

    provenances = set()
    for item in field_status.values():
        provenances.add(item.provenance)
    provenances.add(weather.provenance)
    for k in knowledge:
        provenances.add(k.provenance)

    has_live = DataProvenance.LIVE_SENSOR.value in provenances or DataProvenance.LIVE_WEATHER.value in provenances
    has_source = DataProvenance.SOURCE_BACKED_KNOWLEDGE.value in provenances
    has_unavail = DataProvenance.UNAVAILABLE.value in provenances
    has_sim = DataProvenance.SIMULATED.value in provenances

    if (has_live or has_source) and (has_unavail or has_sim):
        return "PARTIALLY_GROUNDED"
    elif has_live and has_source and not has_unavail and not has_sim:
        return "GROUNDED"
    elif has_sim and not has_live:
        return "SIMULATED"
    elif has_unavail and not has_live:
        return "UNAVAILABLE"
    return "PARTIALLY_GROUNDED"


def render_advisory_text(
    crop: str,
    growth_stage: str,
    field_status: Dict[str, FieldTelemetryItem],
    weather: WeatherStatusItem,
    knowledge: List[KnowledgeStatementItem],
    decision: DecisionItem,
    is_demo_mode: bool = False,
    device_id: Optional[str] = "ESP32_NODE_01",
    telemetry_timestamp: Optional[str] = None
) -> str:
    """
    Renders standardized advisory output following exact agricultural provenance rules:
    
    AgriSaathi Advisory for <Crop>
    <Stage> stage
    
    Field telemetry
    - Soil moisture: <val>% [<Provenance>]
    ...
    Weather
    ...
    Agronomic knowledge
    ...
    Decision
    ...
    Data quality
    ...
    """
    lines = []

    if is_demo_mode:
        lines.append("⚠️ DEMO MODE — SIMULATED DATA\n")

    lines.append(f"AgriSaathi Advisory for {crop}")
    lines.append(f"{growth_stage} stage\n")

    # 1. Field Telemetry
    lines.append("Field telemetry")
    moisture_item = field_status.get("soil_moisture_pct")
    if moisture_item and moisture_item.value is not None:
        prov_label = "Simulated" if moisture_item.provenance == DataProvenance.SIMULATED.value else "Live sensor"
        lines.append(f"- Soil moisture: {moisture_item.value}{moisture_item.unit or '%'} [{prov_label}]")
    else:
        lines.append("- Soil moisture: Not available [Unavailable]")

    air_temp_item = field_status.get("air_temperature_c")
    if air_temp_item and air_temp_item.value is not None:
        prov_label = "Simulated" if air_temp_item.provenance == DataProvenance.SIMULATED.value else "Live sensor"
        unit = air_temp_item.unit or '\u00b0C'
        lines.append(f"- Air temperature: {air_temp_item.value}{unit} [{prov_label}]")
    else:
        lines.append("- Air temperature: Not available [Unavailable]")

    dev_label = f"{device_id} (Simulated)" if is_demo_mode else (device_id or "ESP32_NODE_01")
    lines.append(f"- Device: {dev_label}")
    ts = telemetry_timestamp or (moisture_item.timestamp if moisture_item else None) or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"- Last updated: {ts}\n")

    # 2. Weather
    lines.append("Weather")
    if weather.status == "AVAILABLE" and weather.temperature_c is not None:
        prov_label = "Simulated" if weather.provenance == DataProvenance.SIMULATED.value else "Live weather"
        lines.append(f"- Status: {weather.description} [{prov_label}]")
        lines.append(f"- Temperature: {weather.temperature_c}°C")
        if weather.humidity_pct is not None:
            lines.append(f"- Humidity: {weather.humidity_pct}%")
        if weather.rainfall_mm is not None and weather.rainfall_mm > 0:
            lines.append(f"- Rain: {weather.rainfall_mm} mm")
    elif weather.status == "STALE":
        lines.append("- Status: Stale data")
        temp_str = f"{weather.temperature_c}°C" if weather.temperature_c is not None else "Not available"
        lines.append(f"- Temperature: {temp_str}")
        lines.append(f"- Last updated: {weather.last_updated or 'Unknown'}")
    elif weather.status == "TEMPORARILY_UNAVAILABLE":
        lines.append("- Status: Temporarily unavailable")
        lines.append("- Temperature: Not available")
        lines.append(f"- Reason: {weather.reason or 'Weather provider connection failed'}")
    else:
        lines.append("- Status: Not available")
        lines.append("- Temperature: Not available")
        lines.append(f"- Reason: {weather.reason or 'No verified weather reading received'}")
    lines.append("")

    # 3. Agronomic Knowledge
    lines.append("Agronomic knowledge")
    if knowledge:
        for k in knowledge:
            stage_str = f" ({k.growth_stage} stage)" if k.growth_stage else ""
            lines.append(f"- {k.crop or crop}{stage_str} guidance: {k.statement}")
            lines.append(f"- Source: {k.source_title}")
            if k.source_url:
                lines.append(f"- Verified URL: {k.source_url}")
            prov_text = "Source-backed knowledge" if k.source_status == "VERIFIED" else "Source verification unavailable"
            lines.append(f"- Provenance: {prov_text}")
    else:
        lines.append("- Guidance: Source verification unavailable")
        lines.append("- Provenance: Source verification unavailable")
    lines.append("")

    # 4. Decision
    lines.append("Decision")
    lines.append(f"- Recommendation: {decision.result}")
    lines.append(f"- Provenance: {decision.provenance}")
    lines.append(f"- Explanation: {decision.explanation}")
    if hasattr(decision, "threshold_source") and decision.threshold_source:
        lines.append(f"- Threshold source: {decision.threshold_source}")
    lines.append("")

    # 5. Data Quality Summary
    lines.append("Data quality")
    # Telemetry badge
    if moisture_item and moisture_item.provenance == DataProvenance.LIVE_SENSOR.value:
        t_badge = "Live"
    elif moisture_item and moisture_item.provenance == DataProvenance.SIMULATED.value:
        t_badge = "Simulated"
    else:
        t_badge = "Unavailable"
    lines.append(f"- Field telemetry: {t_badge}")

    # Weather badge
    if weather.provenance == DataProvenance.LIVE_WEATHER.value:
        w_badge = "Live"
    elif weather.provenance == DataProvenance.SIMULATED.value:
        w_badge = "Simulated"
    elif weather.status == "STALE":
        w_badge = "Stale"
    else:
        w_badge = "Unavailable"
    lines.append(f"- Weather: {w_badge}")

    # Knowledge badge
    k_badge = "Source-backed" if any(k.source_status == "VERIFIED" for k in knowledge) else "Unverified"
    lines.append(f"- Knowledge: {k_badge}")

    # Overall advisory badge
    overall = determine_overall_status(field_status, weather, knowledge, is_demo_mode=is_demo_mode)
    lines.append(f"- Overall advisory: {overall.replace('_', ' ').capitalize()}")

    # 6. Domain Limitations (Audit Items 169-173)
    lines.append("")
    lines.append("Advisory limitations")
    lines.append(
        "- Decision engine: Deterministic rule-based thresholds from ICAR/FAO published guidelines."
    )
    lines.append(
        "- Validation: These thresholds have NOT been empirically validated against this farm's field outcomes."
    )
    lines.append(
        "- Domain authority: Not a substitute for agronomist-reviewed recommendations."
    )
    lines.append(
        "- Action: Always confirm with a qualified agricultural extension officer before commercial decisions."
    )

    return "\n".join(lines)
