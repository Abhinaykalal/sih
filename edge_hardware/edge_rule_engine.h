/*
 * AGRISENTINEL EDGE - RULE-BASED HEURISTICS ENGINE
 * -------------------------------------------------------------
 * Designed specifically for ESP32 / Microcontrollers.
 * Uses static heuristic logic compiled into C++ code.
 * Provides fallback local logic when the backend is unreachable.
 * 
 * Execution Time: < 1.5 milliseconds on ESP32
 */

#ifndef EDGE_RULE_ENGINE_H
#define EDGE_RULE_ENGINE_H

#include <Arduino.h>

struct EdgeRuleResult {
    const char* risk_level; // "SAFE", "WARNING", "CRITICAL"
    int risk_score;         // 0 to 100
    const char* action;     // Recommended on-device action
};

class EdgeRuleEngine {
public:
    static EdgeRuleResult evaluateRisk(float z2_moisture, float air_temp, float humidity) {
        EdgeRuleResult res;
        
        // Simple type casting and clamping
        int moisture = constrain((int)z2_moisture, 0, 100);
        int temp = constrain((int)air_temp, 0, 50);
        int hum = constrain((int)humidity, 0, 100);

        // --- Heuristic 1: Severe Drought / Heat Burn ---
        if (moisture < 20 && temp > 33) {
            res.risk_level = "CRITICAL";
            res.risk_score = 92;
            res.action = "ACTIVATE_PUMP_ZONE_2_IMMEDIATELY";
            return res;
        }

        // --- Heuristic 2: Fungal Spore Risk (High Temp + High Humidity) ---
        if (hum > 85 && temp > 28) {
            res.risk_level = "WARNING";
            res.risk_score = 78;
            res.action = "SCHEDULE_BIO_FUNGICIDE_SPRAY";
            return res;
        }

        // --- Heuristic 3: Over-Irrigation / Root Waterlogging Risk ---
        if (moisture > 80) {
            res.risk_level = "WARNING";
            res.risk_score = 82;
            res.action = "DEACTIVATE_PUMP_DRAIN_SOIL";
            return res;
        }

        // Normal Condition
        res.risk_level = "SAFE";
        res.risk_score = 12;
        res.action = "CONTINUE_MONITORING";
        return res;
    }
};

#endif // EDGE_RULE_ENGINE_H
