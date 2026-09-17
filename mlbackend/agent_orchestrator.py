"""
AgriSaathi Telemetry Decision Router
=====================================
IMPORTANT: This module is NOT an LLM and does NOT generate text.
It is a deterministic rules-based aggregator that:
  - Reads live/simulated ESP32 telemetry via MQTT
  - Retrieves RAG knowledge chunks from rag_engine.py
  - Evaluates irrigation decisions via the irrigation_provider
  - Formats the output as structured, provenance-tagged JSON

All natural language generation is handled exclusively by
llm_provider.py (llm_provider.hybrid_provider), which routes
Ollama local â†’ Groq cloud â†’ RAG-only.

This module does NOT call any LLM, it only assembles structured
inputs and routes them to domain tools.
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from model_providers import (
        
        irrigation_provider,
        nutrient_provider,
        EvidenceItem,
        ModelConfidence
    )
    from rag_engine import rag_engine
    from mqtt_service import mqtt_manager
    from services import get_weather, get_forecast
    from conversation_memory import ConversationMemory
    from multilingual import detect_language as ml_detect_language, translate_to_english, build_multilingual_response
    from esp32_simulator import esp32_simulator
    from advisory_provenance import (
        DataProvenance,
        FieldTelemetryItem,
        WeatherStatusItem,
        KnowledgeStatementItem,
        DecisionItem,
        format_weather_display,
        render_advisory_text,
        determine_overall_status
    )
except ImportError:
    try:
        from mlbackend.model_providers import (
             irrigation_provider, nutrient_provider,
            EvidenceItem, ModelConfidence
        )
        from mlbackend.rag_engine import rag_engine
        from mlbackend.mqtt_service import mqtt_manager
        from mlbackend.services import get_weather, get_forecast
        from mlbackend.conversation_memory import ConversationMemory
        from mlbackend.multilingual import detect_language as ml_detect_language, translate_to_english, build_multilingual_response
        from mlbackend.esp32_simulator import esp32_simulator
        from mlbackend.advisory_provenance import (
            DataProvenance,
            FieldTelemetryItem,
            WeatherStatusItem,
            KnowledgeStatementItem,
            DecisionItem,
            format_weather_display,
            render_advisory_text,
            determine_overall_status
        )
    except ImportError:
        irrigation_provider = None
        nutrient_provider = None
        rag_engine = None
        mqtt_manager = None
        ConversationMemory = None
        esp32_simulator = None
        def get_weather(lat, lon, allow_simulation=False): return {}
        def get_forecast(lat, lon): return {}
        def ml_detect_language(t): return "en"
        def translate_to_english(t, l): return t, False
        def build_multilingual_response(english_response, lang_code, greeting=True): return english_response

        class EvidenceItem(BaseModel):
            type: str
            name: str
            value: Any = None
            unit: Optional[str] = None
            confidence: Optional[float] = None
            timestamp: Optional[str] = None

        class ModelConfidence(BaseModel):
            overall: float
            level: str = "high"

        # Minimal stubs so agent_orchestrator doesn't crash at runtime
        from enum import Enum
        class DataProvenance(str, Enum):
            LIVE_SENSOR = "LIVE_SENSOR"
            LIVE_WEATHER = "LIVE_WEATHER"
            SIMULATED = "SIMULATED"
            SOURCE_BACKED_KNOWLEDGE = "SOURCE_BACKED_KNOWLEDGE"
            RULE_BASED = "RULE_BASED"
            UNAVAILABLE = "UNAVAILABLE"

        class FieldTelemetryItem(BaseModel):
            value: Any = None
            unit: Optional[str] = None
            provenance: str = "UNAVAILABLE"
            device_id: Optional[str] = None
            timestamp: Optional[str] = None
            freshness: str = "OFFLINE"

        class WeatherStatusItem(BaseModel):
            status: str = "UNAVAILABLE"
            temperature_c: Optional[float] = None
            humidity_pct: Optional[float] = None
            rainfall_mm: Optional[float] = None
            description: Optional[str] = None
            provenance: str = "UNAVAILABLE"

        class KnowledgeStatementItem(BaseModel):
            statement: str
            provenance: str = "UNAVAILABLE"
            source_title: Optional[str] = None
            source_organization: Optional[str] = None
            source_url: Optional[str] = None
            publication_date: Optional[str] = None
            crop: Optional[str] = None
            growth_stage: Optional[str] = None
            region: Optional[str] = None
            citation_id: Optional[str] = None
            source_status: str = "UNVERIFIED"
            limitations: list = []

        class DecisionItem(BaseModel):
            result: str = "UNAVAILABLE"
            provenance: str = "UNAVAILABLE"
            explanation: str = ""
            inputs_used: list = []
            inputs_missing: list = []
            urgency: str = "LOW"
            target_water_mm: Optional[float] = None

        def format_weather_display(weather_data, is_demo_mode=False): return WeatherStatusItem()
        def render_advisory_text(*args, **kwargs): return ""
        def determine_overall_status(*args, **kwargs): return "UNAVAILABLE"


class AgentChatRequest(BaseModel):
    message: str
    crop: Optional[str] = "Rice"
    stage: Optional[str] = "Vegetative"
    field_id: Optional[str] = "field-rice-01"
    lat: Optional[float] = 30.7333
    lon: Optional[float] = 76.7794
    image_base64: Optional[str] = None
    language: Optional[str] = None        # None = auto-detect
    user_id: Optional[str] = "anonymous"  # for conversation memory
    session_id: Optional[str] = "default"
    demo_mode: bool = False
    mock_telemetry: Optional[Dict[str, Any]] = None
    mock_weather: Optional[Dict[str, Any]] = None


class StructuredAgentResponse(BaseModel):
    answer: str
    language: str = "en"
    detected_language: str = "en"
    intent: str
    confidence: ModelConfidence
    evidence: List[EvidenceItem]
    actions: List[str]
    sources: List[Dict[str, str]]
    model_versions: Dict[str, str]
    telemetry_source: str = "NONE"        # "LIVE_SENSOR", "SIMULATED", "UNAVAILABLE"

    # Provenance-Aware Schema Attributes
    advisory_title: Optional[str] = None
    crop: Optional[str] = None
    growth_stage: Optional[str] = None
    field_status: Optional[Dict[str, Any]] = None
    weather: Optional[Dict[str, Any]] = None
    knowledge: Optional[List[Dict[str, Any]]] = None
    decision: Optional[Dict[str, Any]] = None
    data_quality: Optional[Dict[str, str]] = None
    overall_status: Optional[str] = None


class AgentOrchestrator:
    """Dynamic Multi-Model Agent Orchestrator with Granular Provenance & Response Validation."""

    def process_query(self, req: AgentChatRequest) -> StructuredAgentResponse:
        # --------------------------------------------------------
        # Step 0: Language Detection & Translation
        # --------------------------------------------------------
        detected_lang = req.language or ml_detect_language(req.message)
        english_message, was_translated = translate_to_english(req.message, detected_lang)
        query_text = english_message.lower()
        intent = self._detect_intent(query_text, req.image_base64)
        is_demo_mode = getattr(req, "demo_mode", False)

        # --------------------------------------------------------
        # Step 1: Conversation Memory - load history
        # --------------------------------------------------------
        mem = None
        conversation_history = []
        if ConversationMemory and req.user_id:
            mem = ConversationMemory(
                user_id=req.user_id,
                session_id=req.session_id or "default"
            )
            conversation_history = mem.get_window(max_turns=10)

        # --------------------------------------------------------
        # Step 2: Fetch Live or Simulated ESP32 Telemetry
        # --------------------------------------------------------
        telemetry = None
        telemetry_source = DataProvenance.UNAVAILABLE.value
        device_id = "ESP32_NODE_01"

        if getattr(req, "mock_telemetry", None) is not None:
            telemetry = req.mock_telemetry
            telemetry_source = req.mock_telemetry.get("provenance", DataProvenance.SIMULATED.value if is_demo_mode else DataProvenance.LIVE_SENSOR.value)
            device_id = telemetry.get("device_id", device_id)
        else:
            # Try live MQTT data first
            if mqtt_manager and not is_demo_mode:
                live = mqtt_manager.get_latest_telemetry("ESP32-001")
                if live and live.get("timestamp"):
                    telemetry = live
                    telemetry_source = DataProvenance.LIVE_SENSOR.value
                    device_id = live.get("device_id", "ESP32_NODE_01")

            # Fall back to realistic simulator only if in demo mode or simulator requested
            if not telemetry and is_demo_mode and esp32_simulator:
                sim = esp32_simulator.generate_telemetry()
                telemetry = {
                    "soilMoisture": sim["readings"]["soil_moisture_pct"],
                    "soilTemperature": sim["readings"]["soil_temperature_c"],
                    "airTemperature": sim["readings"]["air_temperature_c"],
                    "humidity": sim["readings"]["air_humidity_pct"],
                    "pH": sim["readings"].get("soil_ph"),
                    "EC": sim["readings"].get("soil_ec_ds_m"),
                    "NPK": sim["readings"].get("NPK_ppm", {"N": 45, "P": 22, "K": 38}),
                    "rain": sim["readings"]["rain_detected"],
                    "timestamp": sim["timestamp"],
                    "device_health": sim["sensor_health"],
                    "device_id": "ESP32_NODE_01"
                }
                telemetry_source = DataProvenance.SIMULATED.value

        # Extract sensor values (offline if no data)
        is_sensor_offline = (telemetry is None)
        moisture = telemetry.get("soilMoisture") if telemetry else None
        soil_temp = telemetry.get("soilTemperature") if telemetry else None
        air_temp = telemetry.get("airTemperature") if telemetry else None
        humidity = telemetry.get("humidity") if telemetry else None
        ph = telemetry.get("pH") if telemetry else None
        npk = telemetry.get("NPK") if telemetry else None
        telemetry_ts = telemetry.get("timestamp") if telemetry else None

        # Build Field Status dictionary
        field_status: Dict[str, FieldTelemetryItem] = {
            "soil_moisture_pct": FieldTelemetryItem(
                value=moisture,
                unit="%",
                provenance=telemetry_source if moisture is not None else DataProvenance.UNAVAILABLE.value,
                device_id=device_id,
                timestamp=telemetry_ts,
                freshness="CURRENT" if moisture is not None else "OFFLINE"
            ),
            "air_temperature_c": FieldTelemetryItem(
                value=air_temp,
                unit="Â°C",
                provenance=telemetry_source if air_temp is not None else DataProvenance.UNAVAILABLE.value,
                device_id=device_id,
                timestamp=telemetry_ts,
                freshness="CURRENT" if air_temp is not None else "OFFLINE"
            )
        }

        # --------------------------------------------------------
        # Step 3: Build Evidence List
        # --------------------------------------------------------
        evidence_list: List[EvidenceItem] = []
        if not is_sensor_offline and telemetry:
            if moisture is not None:
                evidence_list.append(EvidenceItem(
                    type="sensor",
                    name="soil_moisture",
                    value=moisture,
                    unit="%",
                    timestamp=telemetry_ts
                ))
            if air_temp is not None:
                evidence_list.append(EvidenceItem(type="sensor", name="air_temperature", value=air_temp, unit="Â°C"))
            if humidity is not None:
                evidence_list.append(EvidenceItem(type="sensor", name="humidity", value=humidity, unit="%"))
            if ph is not None:
                evidence_list.append(EvidenceItem(type="sensor", name="soil_ph", value=ph, unit="pH"))
            if npk:
                evidence_list.append(EvidenceItem(type="sensor", name="NPK_N", value=npk.get("N"), unit="ppm"))
                evidence_list.append(EvidenceItem(type="sensor", name="NPK_P", value=npk.get("P"), unit="ppm"))
                evidence_list.append(EvidenceItem(type="sensor", name="NPK_K", value=npk.get("K"), unit="ppm"))

        # --------------------------------------------------------
        # Step 4: Weather API (Null-Safe)
        # --------------------------------------------------------
        if getattr(req, "mock_weather", None) is not None:
            weather_data = req.mock_weather
        else:
            try:
                weather_data = get_weather(req.lat or 30.73, req.lon or 76.78, allow_simulation=is_demo_mode)
            except Exception:
                weather_data = {
                    "status": "TEMPORARILY_UNAVAILABLE",
                    "temp": None,
                    "reason": "Weather provider connection failed"
                }

        weather_item = format_weather_display(weather_data, is_demo_mode=is_demo_mode)

        if weather_item.rainfall_mm is not None:
            evidence_list.append(EvidenceItem(type="weather", name="rain_forecast", value=weather_item.rainfall_mm, unit="mm"))

        # --------------------------------------------------------
        # Step 5: Knowledge & Tool Execution
        # --------------------------------------------------------
        actions: List[str] = []
        sources: List[Dict[str, str]] = []
        knowledge_items: List[KnowledgeStatementItem] = []
        model_versions = {
            "agent_orchestrator": "2.2.0",
            "vision_model": "2.5.0",
            "irrigation_model": "2.1.0",
            "rag_engine": "1.1.0",
            "memory": "1.0.0",
            "multilingual": "1.0.0"
        }

        # Retrieve RAG Knowledge
        rag_docs = rag_engine.search(query_text, crop=req.crop) if rag_engine else []
        for doc in rag_docs:
            sources.append({"title": doc.title, "source": doc.source, "url": doc.url})
            is_verified = (doc.verification_status == "VERIFIED_GOVERNMENT_EXTENSION" and bool(doc.url))
            knowledge_items.append(KnowledgeStatementItem(
                statement=doc.content,
                provenance=DataProvenance.SOURCE_BACKED_KNOWLEDGE.value if is_verified else DataProvenance.UNAVAILABLE.value,
                source_title=doc.title,
                source_organization=doc.source_organization,
                source_url=doc.url if is_verified else None,
                publication_date=doc.publication_date,
                crop=doc.crop,
                growth_stage=getattr(doc, "growth_stage", req.stage),
                region=doc.region,
                citation_id=getattr(doc, "citation_id", doc.id),
                source_status="VERIFIED" if is_verified else "UNVERIFIED",
                limitations=getattr(doc, "limitations", [])
            ))

        # Evaluate Irrigation / Decision Engine
        if irrigation_provider:
            is_sim_telemetry = (telemetry_source == DataProvenance.SIMULATED.value)
            irrig_res = irrigation_provider.assess_irrigation_needs(
                soil_moisture=moisture,
                air_temp=air_temp,
                humidity=humidity,
                rain_forecast_mm=weather_item.rainfall_mm,
                crop=req.crop or "Rice",
                growth_stage=req.stage or "Vegetative",
                is_simulated=is_sim_telemetry
            )
            decision_item = DecisionItem(
                result=irrig_res.recommendation_text,
                provenance=irrig_res.provenance,
                explanation=irrig_res.explanation,
                inputs_used=irrig_res.inputs_used,
                inputs_missing=irrig_res.inputs_missing,
                urgency=irrig_res.urgency,
                target_water_mm=irrig_res.target_water_mm,
                threshold_source=getattr(irrig_res, "threshold_source", None),
                validation_status=getattr(irrig_res, "validation_status", "UNVALIDATED_AGAINST_FIELD_OUTCOMES")
            )
            actions = ([f"Apply {irrig_res.target_water_mm} mm irrigation to root zone.",
                        "Monitor soil moisture 4 hours post-irrigation."]
                       if irrig_res.irrigation_needed
                       else ["Maintain current irrigation schedule.",
                             "Re-assess after scheduled soil sensor refresh."])
            conf = irrig_res.confidence
        else:
            decision_item = DecisionItem(
                result="Decision unavailable â€” required inputs are missing",
                provenance=DataProvenance.UNAVAILABLE.value,
                explanation="Irrigation provider engine offline.",
                inputs_used=[],
                inputs_missing=["irrigation_engine"]
            )
            actions = ["Maintain standard manual observation"]
            conf = ModelConfidence(overall=0.5, level="uncertain")

        # --------------------------------------------------------
        # Step 6: Render Standardized Advisory Display
        # --------------------------------------------------------
        rendered_answer = render_advisory_text(
            crop=req.crop or "Rice",
            growth_stage=req.stage or "Vegetative",
            field_status=field_status,
            weather=weather_item,
            knowledge=knowledge_items,
            decision=decision_item,
            is_demo_mode=is_demo_mode,
            device_id=device_id,
            telemetry_timestamp=telemetry_ts
        )

        overall_status_val = determine_overall_status(
            field_status=field_status,
            weather=weather_item,
            knowledge=knowledge_items,
            is_demo_mode=is_demo_mode
        )

        # Data quality map
        t_badge = "Live" if telemetry_source == DataProvenance.LIVE_SENSOR.value else ("Simulated" if telemetry_source == DataProvenance.SIMULATED.value else "Unavailable")
        w_badge = "Live" if weather_item.provenance == DataProvenance.LIVE_WEATHER.value else ("Simulated" if weather_item.provenance == DataProvenance.SIMULATED.value else ("Stale" if weather_item.status == "STALE" else "Unavailable"))
        k_badge = "Source-backed" if any(k.source_status == "VERIFIED" for k in knowledge_items) else "Unverified"
        data_quality_map = {
            "field_telemetry": t_badge,
            "weather": w_badge,
            "knowledge": k_badge,
            "overall_advisory": overall_status_val.replace("_", " ").capitalize()
        }

        # --------------------------------------------------------
        # Step 7: Save to Conversation Memory
        # --------------------------------------------------------
        farm_context = {
            "crop": req.crop,
            "stage": req.stage,
            "field_id": req.field_id,
            "moisture": moisture,
            "air_temp": air_temp,
            "telemetry_source": telemetry_source,
            "intent": intent
        }
        if mem:
            mem.add_user_message(req.message, context=farm_context)
            mem.add_assistant_message(rendered_answer, context=farm_context)

        # --------------------------------------------------------
        # Step 8: Multilingual Response Wrapping
        # --------------------------------------------------------
        final_answer = build_multilingual_response(rendered_answer, detected_lang, greeting=False)

        return StructuredAgentResponse(
            answer=final_answer,
            language=detected_lang,
            detected_language=detected_lang,
            intent=intent,
            confidence=conf,
            evidence=evidence_list,
            actions=actions,
            sources=sources,
            model_versions=model_versions,
            telemetry_source=telemetry_source,
            # Provenance-Aware Schema Attributes
            advisory_title=f"AgriSaathi Advisory for {req.crop or 'Rice'}",
            crop=req.crop or "Rice",
            growth_stage=req.stage or "Vegetative",
            field_status={k: v.model_dump() for k, v in field_status.items()},
            weather=weather_item.model_dump(),
            knowledge=[k.model_dump() for k in knowledge_items],
            decision=decision_item.model_dump(),
            data_quality=data_quality_map,
            overall_status=overall_status_val
        )

    def _detect_intent(self, text: str, has_image: Optional[str]) -> str:
        if has_image or any(w in text for w in ["disease", "leaf", "spot", "blight", "yellow", "photo", "image", "pest", "fungus", "rot"]):
            return "disease_diagnosis"
        if any(w in text for w in ["water", "irrigat", "moisture", "dry", "thirst", "rain", "flood", "drip"]):
            return "irrigation_assessment"
        if any(w in text for w in ["npk", "fertilizer", "nitrogen", "urea", "phosphorus", "potassium", "soil ph", "ec ", "nutrient", "deficien"]):
            return "soil_npk_analysis"
        if any(w in text for w in ["yield", "harvest", "production", "output", "ton"]):
            return "yield_advisory"
        if any(w in text for w in ["weather", "rain", "temperature", "forecast", "monsoon", "climate"]):
            return "weather_advisory"
        return "general_advisory"


agent_orchestrator = AgentOrchestrator()
