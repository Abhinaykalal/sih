/*
 * AgriSaathi EDGE CROP GUARD
 * --------------------------
 * This header contains deterministic advisory rules, NOT a trained TinyML model.
 * It intentionally does not claim model accuracy, quantization, or benchmark
 * results. Hardware actuation must remain behind the backend safety controller.
 */
#ifndef TINYML_CROP_GUARD_H
#define TINYML_CROP_GUARD_H

#include <Arduino.h>

struct TinyMLResult {
    const char* risk_level;       // SAFE | WARNING | CRITICAL | UNAVAILABLE
    int risk_score;               // 0..100 heuristic score, not model confidence
    const char* action;            // Advisory action only; never a relay command
    const char* provenance;        // RULE_BASED
};

class TinyMLCropGuard {
public:
    static TinyMLResult predictRisk(float soil_moisture,
                                    float air_temp,
                                    float humidity,
                                    int pest_count,
                                    float ec_salinity) {
        TinyMLResult res;
        res.provenance = "RULE_BASED";

        // Missing sensor values are represented as NaN and must not be guessed.
        if (isnan(soil_moisture) || isnan(air_temp) || isnan(humidity) || isnan(ec_salinity) || pest_count < 0) {
            res.risk_level = "UNAVAILABLE";
            res.risk_score = 0;
            res.action = "WAIT_FOR_VALID_SENSOR_DATA";
            return res;
        }

        // These thresholds are transparent agronomic heuristics, not learned weights.
        if (ec_salinity > 2.5f) {
            res.risk_level = "CRITICAL";
            res.risk_score = 90;
            res.action = "INSPECT_SALINITY_AND_HALT_FERTILIZER_APPLICATION";
            return res;
        }
        if (soil_moisture < 20.0f && air_temp > 33.0f) {
            res.risk_level = "CRITICAL";
            res.risk_score = 92;
            res.action = "INSPECT_DROUGHT_STRESS_AND_USE_APPROVED_IRRIGATION_POLICY";
            return res;
        }
        if (soil_moisture > 80.0f) {
            res.risk_level = "WARNING";
            res.risk_score = 82;
            res.action = "INSPECT_DRAINAGE_AND_KEEP_PUMP_OFF_UNLESS_AUTHORIZED";
            return res;
        }
        if (humidity > 85.0f && air_temp > 28.0f) {
            res.risk_level = "WARNING";
            res.risk_score = 78;
            res.action = "INSPECT_CROP_FOR_FUNGAL_DISEASE_RISK";
            return res;
        }
        if (pest_count > 30) {
            res.risk_level = "WARNING";
            res.risk_score = 85;
            res.action = "INSPECT_FOR_PEST_OUTBREAK_AND_FOLLOW_LOCAL_GUIDANCE";
            return res;
        }

        res.risk_level = "SAFE";
        res.risk_score = 12;
        res.action = "CONTINUE_MONITORING";
        return res;
    }
};

#endif // TINYML_CROP_GUARD_H
