"""
AgriSaathi AI — Comprehensive Test Suite for Advisory Data Provenance
=====================================================================
Tests all 14 required provenance, weather null rendering, simulation labeling,
RAG citation, decision logic, and data quality scenarios.
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

# Ensure mlbackend is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
from model_providers import irrigation_provider
from rag_engine import rag_engine, KnowledgeDocument
from agent_orchestrator import agent_orchestrator, AgentChatRequest


class TestAdvisoryProvenance(unittest.TestCase):

    def test_01_live_telemetry_plus_unavailable_weather(self):
        """1. Live telemetry plus unavailable weather."""
        req = AgentChatRequest(
            message="Provide advisory for rice field",
            crop="Rice",
            stage="Vegetative",
            mock_telemetry={
                "soilMoisture": 45.1,
                "airTemperature": 26.9,
                "device_id": "ESP32_NODE_01",
                "timestamp": "2026-09-11 12:00:00 UTC",
                "provenance": "LIVE_SENSOR"
            },
            mock_weather={
                "status": "UNAVAILABLE",
                "temp": None,
                "reason": "No verified weather reading received"
            }
        )
        res = agent_orchestrator.process_query(req)

        self.assertIn("Soil moisture: 45.1% [Live sensor]", res.answer)
        self.assertIn("Air temperature: 26.9", res.answer)
        self.assertIn("[Live sensor]", res.answer.split("Air temperature: 26.9")[1].split("\\n")[0])
        self.assertIn("Weather\n- Status: Not available\n- Temperature: Not available", res.answer)
        self.assertNotIn("Temp: None°C", res.answer)
        self.assertNotIn("Data source: SIMULATED", res.answer)
        self.assertEqual(res.field_status["soil_moisture_pct"]["provenance"], "LIVE_SENSOR")
        self.assertEqual(res.weather["provenance"], "UNAVAILABLE")
        self.assertEqual(res.overall_status, "PARTIALLY_GROUNDED")

    def test_02_live_telemetry_plus_source_backed_knowledge(self):
        """2. Live telemetry plus source-backed knowledge."""
        req = AgentChatRequest(
            message="How to manage water in vegetative rice?",
            crop="Rice",
            stage="Vegetative",
            mock_telemetry={
                "soilMoisture": 48.0,
                "airTemperature": 28.0,
                "device_id": "ESP32_NODE_01",
                "timestamp": "2026-09-11 12:00:00 UTC",
                "provenance": "LIVE_SENSOR"
            }
        )
        res = agent_orchestrator.process_query(req)

        self.assertIn("Field telemetry: Live", res.answer)
        self.assertIn("Knowledge: Source-backed", res.answer)
        self.assertIn("ICAR Package of Practices", res.answer)
        self.assertTrue(len(res.knowledge) > 0)
        self.assertEqual(res.knowledge[0]["provenance"], "SOURCE_BACKED_KNOWLEDGE")

    def test_03_fully_simulated_demo_mode(self):
        """3. Fully simulated demo mode."""
        req = AgentChatRequest(
            message="Show advisory in demo mode",
            crop="Rice",
            stage="Vegetative",
            demo_mode=True,
            mock_telemetry={
                "soilMoisture": 45.1,
                "airTemperature": 26.9,
                "device_id": "ESP32_NODE_01",
                "timestamp": "2026-09-11 12:00:00 UTC",
                "provenance": "SIMULATED"
            }
        )
        res = agent_orchestrator.process_query(req)

        self.assertIn("DEMO MODE — SIMULATED DATA", res.answer)
        self.assertIn("Soil moisture: 45.1% [Simulated]", res.answer)
        self.assertIn("Air temperature: 26.9", res.answer)
        self.assertIn("[Simulated]", res.answer.split("Air temperature: 26.9")[1].split("\\n")[0])
        self.assertIn("Field telemetry: Simulated", res.answer)
        self.assertEqual(res.overall_status, "SIMULATED")

    def test_04_missing_soil_moisture(self):
        """4. Missing soil moisture."""
        req = AgentChatRequest(
            message="Irrigation check",
            crop="Rice",
            stage="Vegetative",
            mock_telemetry={
                "airTemperature": 27.5,
                "device_id": "ESP32_NODE_01",
                "provenance": "LIVE_SENSOR"
            }
        )
        res = agent_orchestrator.process_query(req)

        self.assertIn("Soil moisture: Not available [Unavailable]", res.answer)
        self.assertIn("Decision unavailable — required inputs are missing", res.answer)
        self.assertIn("soil_moisture", res.decision["inputs_missing"])
        self.assertEqual(res.decision["provenance"], "UNAVAILABLE")

    def test_05_missing_temperature(self):
        """5. Missing temperature."""
        req = AgentChatRequest(
            message="Telemetry check",
            crop="Rice",
            stage="Vegetative",
            mock_telemetry={
                "soilMoisture": 44.0,
                "airTemperature": None,
                "device_id": "ESP32_NODE_01",
                "provenance": "LIVE_SENSOR"
            }
        )
        res = agent_orchestrator.process_query(req)

        self.assertIn("Air temperature: Not available [Unavailable]", res.answer)
        self.assertIn("Soil moisture: 44.0% [Live sensor]", res.answer)
        self.assertIsNone(res.field_status["air_temperature_c"]["value"])

    def test_06_null_weather_temperature(self):
        """6. Null weather temperature & null-safe rendering."""
        # Case A: Weather dict with None temp
        w_none = format_weather_display({"status": "UNAVAILABLE", "temp": None, "humidity": 60})
        self.assertIsNone(w_none.temperature_c)
        self.assertEqual(w_none.status, "UNAVAILABLE")
        self.assertEqual(w_none.provenance, "UNAVAILABLE")

        # Case B: Weather provider failed
        w_err = format_weather_display({"status": "TEMPORARILY_UNAVAILABLE", "error": "Connection timed out"})
        self.assertIsNone(w_err.temperature_c)
        self.assertEqual(w_err.status, "TEMPORARILY_UNAVAILABLE")

        # Case C: None object entirely
        w_obj_none = format_weather_display(None)
        self.assertIsNone(w_obj_none.temperature_c)
        self.assertEqual(w_obj_none.status, "UNAVAILABLE")

        # Case D: Valid weather
        w_val = format_weather_display({"temp": 28.3, "humidity": 65, "rainfall_last_3h": 2.0, "weather": [{"description": "Light rain"}]})
        self.assertEqual(w_val.temperature_c, 28.3)
        self.assertEqual(w_val.status, "AVAILABLE")
        self.assertEqual(w_val.provenance, "LIVE_WEATHER")

    def test_07_stale_telemetry(self):
        """7. Stale telemetry handling in irrigation decision."""
        res = irrigation_provider.assess_irrigation_needs(
            soil_moisture=42.0,
            air_temp=27.0,
            crop="Rice",
            growth_stage="Vegetative",
            last_updated_seconds_ago=25000 # > 6 hours
        )
        self.assertFalse(res.irrigation_needed)
        self.assertIn("stale", res.recommendation_text.lower())
        self.assertEqual(res.provenance, "UNAVAILABLE")
        self.assertIn("fresh_soil_moisture", res.inputs_missing)

    def test_08_device_offline(self):
        """8. Device offline (no telemetry available)."""
        req = AgentChatRequest(
            message="Check status",
            crop="Rice",
            stage="Vegetative",
            mock_telemetry=None
        )
        res = agent_orchestrator.process_query(req)

        self.assertIn("Soil moisture: Not available [Unavailable]", res.answer)
        self.assertIn("Air temperature: Not available [Unavailable]", res.answer)
        self.assertIn("Field telemetry: Unavailable", res.answer)
        self.assertEqual(res.field_status["soil_moisture_pct"]["freshness"], "OFFLINE")

    def test_09_source_backed_rag_response(self):
        """9. Source-backed RAG response."""
        docs = rag_engine.search("rice water vegetative AWD irrigation", crop="Rice")
        self.assertTrue(len(docs) > 0)
        top_doc = docs[0]
        self.assertEqual(top_doc.crop, "Rice")
        self.assertEqual(top_doc.growth_stage, "Vegetative")
        self.assertTrue(top_doc.url.startswith("https://"))
        self.assertEqual(top_doc.verification_status, "VERIFIED_GOVERNMENT_EXTENSION")

    def test_10_unsupported_or_uncited_knowledge(self):
        """10. Unsupported or uncited knowledge handling."""
        unverified_doc = KnowledgeDocument(
            id="doc_unverified_test",
            title="Random blog agronomy tips",
            source="Unknown Web Page",
            source_organization="Unknown",
            url="",  # No verified source URL
            publication_date="2024-01-01",
            crop="Rice",
            region="Unknown",
            topic="irrigation",
            content="Add salt to irrigation water.",
            verification_status="UNVERIFIED"
        )
        is_verified = (unverified_doc.verification_status == "VERIFIED_GOVERNMENT_EXTENSION" and bool(unverified_doc.url))
        self.assertFalse(is_verified)

    def test_11_rule_based_irrigation_decision(self):
        """11. Rule-based irrigation decision with crop threshold context."""
        # 45.1% moisture in vegetative rice (target: 40-60%)
        res = irrigation_provider.assess_irrigation_needs(
            soil_moisture=45.1,
            air_temp=26.9,
            rain_forecast_mm=0.0,
            crop="Rice",
            growth_stage="Vegetative"
        )
        self.assertFalse(res.irrigation_needed)
        self.assertEqual(res.provenance, "RULE_BASED")
        self.assertIn("Maintain current irrigation schedule", res.recommendation_text)
        self.assertIn("40.0%–60.0%", res.explanation)

        # 32.0% moisture in vegetative rice (below 40% threshold)
        res_dry = irrigation_provider.assess_irrigation_needs(
            soil_moisture=32.0,
            air_temp=30.0,
            rain_forecast_mm=0.0,
            crop="Rice",
            growth_stage="Vegetative"
        )
        self.assertTrue(res_dry.irrigation_needed)
        self.assertIn("Apply approximately", res_dry.recommendation_text)

    def test_12_missing_decision_inputs(self):
        """12. Missing decision inputs."""
        res = irrigation_provider.assess_irrigation_needs(
            soil_moisture=None,
            crop="Rice",
            growth_stage="Vegetative"
        )
        self.assertFalse(res.irrigation_needed)
        self.assertEqual(res.recommendation_text, "Decision unavailable — required inputs are missing")
        self.assertEqual(res.provenance, "UNAVAILABLE")
        self.assertIn("soil_moisture", res.inputs_missing)

    def test_13_duplicate_provenance_labels(self):
        """13. Ensure no duplicate provenance labels in rendered output."""
        req = AgentChatRequest(
            message="Show field status",
            crop="Rice",
            stage="Vegetative",
            mock_telemetry={
                "soilMoisture": 45.1,
                "airTemperature": 26.9,
                "device_id": "ESP32_NODE_01",
                "timestamp": "2026-09-11 12:00:00 UTC",
                "provenance": "LIVE_SENSOR"
            }
        )
        res = agent_orchestrator.process_query(req)
        # Verify that soil moisture line doesn't repeat provenance
        moisture_lines = [l for l in res.answer.splitlines() if "Soil moisture:" in l]
        self.assertEqual(len(moisture_lines), 1)
        self.assertEqual(moisture_lines[0].count("[Live sensor]"), 1)

    def test_14_incorrect_global_simulated_label(self):
        """14. Ensure 'Data source: SIMULATED' is not stamped globally when live sensor is present."""
        req = AgentChatRequest(
            message="Provide advisory for rice irrigation AWD",
            crop="Rice",
            stage="Vegetative",
            mock_telemetry={
                "soilMoisture": 45.1,
                "airTemperature": 26.9,
                "device_id": "ESP32_NODE_01",
                "timestamp": "2026-09-11 12:00:00 UTC",
                "provenance": "LIVE_SENSOR"
            },
            mock_weather={
                "status": "UNAVAILABLE",
                "temp": None
            }
        )
        res = agent_orchestrator.process_query(req)

        self.assertNotIn("Data source: SIMULATED", res.answer)
        self.assertNotIn("DEMO MODE", res.answer)
        self.assertEqual(res.field_status["soil_moisture_pct"]["provenance"], "LIVE_SENSOR")
        self.assertEqual(res.data_quality["field_telemetry"], "Live")
        self.assertEqual(res.data_quality["weather"], "Unavailable")
        self.assertEqual(res.data_quality["knowledge"], "Source-backed")
        self.assertEqual(res.data_quality["overall_advisory"], "Partially grounded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
