/**
 * AGRISENTINEL — DECOUPLED TWO-LAYER ML ARCHITECTURE
 * -----------------------------------------------------
 * Layer 1 (Processing Layer): Backend ensemble ML classifier (RandomForest + GradientBoosting).
 *   Extracts real pixel features from leaf photo (PIL/NumPy on server), classifies via
 *   trained scikit-learn model. Endpoint: POST /api/vision-diagnose
 *
 * Layer 2 (Explanation Layer): Data-to-text generator.
 *   Takes Layer 1 structured facts + live sensor telemetry → generates actionable
 *   natural-language explanations. Powered by the backend's LLM service
 *   (Ollama llama3.2:1b → custom_agri_llm fallback).
 *
 * Offline Fallback: When backend unreachable, pure client-side rule classifier
 *   derived from the same agronomic logic as the backend training data.
 */

const ML_BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  (typeof window !== "undefined"
    ? (window as unknown as Record<string, string>).__NEXT_PUBLIC_API_URL__
    : "") ||
  "http://127.0.0.1:8000";

// ─── Exported Interfaces ──────────────────────────────────────────────────────

export interface Layer1StructuredFacts {
  disease_code: string;
  label: string;
  confidence: number;
  severity: "mild" | "moderate" | "severe" | "none";
  affected_area_pct: number;
  category:
    | "Pathogen / Fungal"
    | "Insect / Pest"
    | "Nutrient Deficiency"
    | "Optimal"
    | "Uncertain";
}

export interface Layer2Explanations {
  en: string;
  hi: string;
  te: string;
  action_en: string;
  action_hi: string;
  action_te: string;
}

export interface InferenceResult {
  layer1Facts: Layer1StructuredFacts;
  layer2Explanations: Layer2Explanations;
  label: string;
  confidence: number;
  category: Layer1StructuredFacts["category"];
  inferenceTimeMs: number;
  isUncertain: boolean;
  actionRecommendation: string;
  multimodalReasoning: string;
  source: "backend" | "offline-fallback";
}

// ─── Model load guard (WASM simulation for offline path) ─────────────────────

let isModelLoaded = false;

export async function loadModel(): Promise<boolean> {
  if (isModelLoaded) return true;
  const start = performance.now();
  await new Promise((r) => setTimeout(r, 80));
  isModelLoaded = true;
  console.log(
    `[AgriSentinel] Offline fallback model ready in ${(performance.now() - start).toFixed(1)}ms`
  );
  return true;
}

// ─── Convert image input to base64 string ────────────────────────────────────

async function toBase64(
  imageInput: HTMLImageElement | HTMLCanvasElement | string | Blob
): Promise<string> {
  if (typeof imageInput === "string") return imageInput; // already base64

  if (imageInput instanceof Blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(imageInput);
    });
  }

  if (imageInput instanceof HTMLCanvasElement) {
    return imageInput.toDataURL("image/jpeg", 0.92);
  }

  if (imageInput instanceof HTMLImageElement) {
    const canvas = document.createElement("canvas");
    canvas.width = imageInput.naturalWidth || imageInput.width;
    canvas.height = imageInput.naturalHeight || imageInput.height;
    canvas.getContext("2d")!.drawImage(imageInput, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.92);
  }

  throw new Error("Unsupported image input type");
}

// ─── Map category string from backend → typed union ──────────────────────────

function mapCategory(raw: string): Layer1StructuredFacts["category"] {
  const s = (raw || "").toLowerCase();
  if (s.includes("fungal") || s.includes("pathogen") || s.includes("blight") || s.includes("mildew"))
    return "Pathogen / Fungal";
  if (s.includes("pest") || s.includes("insect") || s.includes("foliage"))
    return "Insect / Pest";
  if (
    s.includes("deficiency") ||
    s.includes("chlorosis") ||
    s.includes("nitrogen") ||
    s.includes("phosphorus") ||
    s.includes("potassium") ||
    s.includes("nutrient")
  )
    return "Nutrient Deficiency";
  if (s.includes("healthy") || s.includes("optimal")) return "Optimal";
  return "Uncertain";
}

function mapSeverity(confidence: number, label: string): Layer1StructuredFacts["severity"] {
  const l = label.toLowerCase();
  if (l.includes("healthy") || l.includes("optimal")) return "none";
  if (confidence >= 0.85) return "severe";
  if (confidence >= 0.70) return "moderate";
  return "mild";
}

// ─── Offline Fallback (pure client-side rule classifier) ─────────────────────
// Mirrors the agronomic logic in train_vision_model.py

export function runLayer1Classification(
  humidity: number,
  moisture: number,
  temp: number
): Layer1StructuredFacts {
  if (humidity > 90) {
    return {
      disease_code: "downy_mildew",
      label: "Downy Mildew Fungal Infection",
      confidence: 0.88,
      severity: "severe",
      affected_area_pct: 22,
      category: "Pathogen / Fungal",
    };
  }
  if (humidity > 80) {
    return {
      disease_code: "early_blight",
      label: "Tomato Early Blight Fungal Spot",
      confidence: 0.91,
      severity: "moderate",
      affected_area_pct: 18,
      category: "Pathogen / Fungal",
    };
  }
  if (moisture < 15 && temp > 33) {
    return {
      disease_code: "water_stress_chlorosis",
      label: "Water Stress Induced Chlorosis",
      confidence: 0.88,
      severity: "severe",
      affected_area_pct: 28,
      category: "Nutrient Deficiency",
    };
  }
  if (moisture < 20 && temp > 30) {
    return {
      disease_code: "nitrogen_deficiency",
      label: "Nitrogen Deficiency Chlorosis",
      confidence: 0.84,
      severity: "moderate",
      affected_area_pct: 20,
      category: "Nutrient Deficiency",
    };
  }
  if (moisture >= 20 && moisture <= 60 && temp > 30 && humidity > 70) {
    return {
      disease_code: "insect_pest_damage",
      label: "Insect Foliage Pest Damage",
      confidence: 0.82,
      severity: "moderate",
      affected_area_pct: 15,
      category: "Insect / Pest",
    };
  }
  return {
    disease_code: "healthy",
    label: "Healthy Foliage",
    confidence: 0.95,
    severity: "none",
    affected_area_pct: 0,
    category: "Optimal",
  };
}

// ─── Offline Layer 2 (trilingual data-to-text from structured facts) ─────────

export function generateLayer2Explanations(
  facts: Layer1StructuredFacts,
  telemetry: { soilMoisture: number; tempC: number; humidity: number }
): Layer2Explanations {
  const { label, severity, affected_area_pct, disease_code } = facts;
  const { humidity, soilMoisture, tempC } = telemetry;

  const TEMPLATES: Record<string, Layer2Explanations> = {
    early_blight: {
      en: `Your crop shows ${severity} signs of ${label} (${affected_area_pct}% leaf surface). Air humidity (${humidity}%) accelerates fungal spore germination.`,
      hi: `आपकी फसल में ${label} के ${severity} लक्षण हैं (${affected_area_pct}% पत्ती प्रभावित)। उच्च आर्द्रता (${humidity}%) फफूंद बीजाणुओं को बढ़ा रही है।`,
      te: `మీ పంటలో ${label} యొక్క ${severity} సంకేతాలు గమనించబడ్డాయి (${affected_area_pct}% ఆకు దెబ్బతింది). అధిక తేమ (${humidity}%) తెగులును పెంచుతోంది.`,
      action_en: "Apply Bio-Fungicide (Trichoderma Viride @ 5g/L) within 24 hours.",
      action_hi: "24 घंटों के भीतर जैविक फफूंदनाशी (ट्राइकोडरमा विरिडे @ 5 ग्राम/लीटर) का छिड़काव करें।",
      action_te: "24 గంటల్లో బైయో-ఫంగిసైడ్ (ట్రైకోడెర్మా విరిడే @ 5 గ్రాములు/లీటర్) పిచికారీ చేయండి.",
    },
    downy_mildew: {
      en: `Downy Mildew spore germination detected (humidity: ${humidity}%). Affects ${affected_area_pct}% of leaf area. Spreads rapidly in damp conditions.`,
      hi: `डाउनी मिल्ड्यू बीजाणु अंकुरण (नमी: ${humidity}%)। ${affected_area_pct}% पत्ती प्रभावित। नम स्थितियों में तेज़ी से फैलता है।`,
      te: `డౌని మిల్డ్యూ తెగులు గుర్తించబడింది (తేమ: ${humidity}%)। ${affected_area_pct}% ఆకు దెబ్బతింది.`,
      action_en: "Apply Copper Oxychloride (2.5g/L) immediately. Remove infected leaves.",
      action_hi: "तुरंत कॉपर ऑक्सीक्लोराइड (2.5g/L) छिड़कें। संक्रमित पत्तियां हटाएं।",
      action_te: "వెంటనే కాపర్ ఆక్సీక్లోరైడ్ (2.5g/L) పిచికారీ చేయండి.",
    },
    water_stress_chlorosis: {
      en: `Critical: Soil moisture at ${soilMoisture}% with ${tempC}°C air temp. Root turgor loss causing ${affected_area_pct}% leaf yellowing.`,
      hi: `मिट्टी नमी ${soilMoisture}% (खतरनाक) और तापमान ${tempC}°C — ${affected_area_pct}% पत्तियों में पीलापन।`,
      te: `నేల తేమ ${soilMoisture}% (ప్రమాదకరం), ఉష్ణోగ్రత ${tempC}°C — ${affected_area_pct}% ఆకులు పసుపు రంగులోకి మారాయి.`,
      action_en: "DO NOT apply nitrogen fertilizer. Activate drip irrigation immediately.",
      action_hi: "नाइट्रोजन उर्वरक न डालें। तुरंत ड्रिप सिंचाई शुरू करें।",
      action_te: "నత్రజని ఎరువులు వేయవద్దు. వెంటనే బిందు సేద్యం ప్రారంభించండి.",
    },
    nitrogen_deficiency: {
      en: `Nitrogen deficiency: Uniform pale yellowing across ${affected_area_pct}% leaf area. Soil moisture (${soilMoisture}%) is adequate — deficiency is nutritional.`,
      hi: `नाइट्रोजन की कमी: ${affected_area_pct}% पत्तियों में समान पीलापन। मिट्टी नमी ठीक है — पोषण की कमी है।`,
      te: `నత్రజని లోపం: ${affected_area_pct}% ఆకులు పీలంగా పసుపు రంగులో ఉన్నాయి. నేల తేమ (${soilMoisture}%) సరిపోతుంది — పోషకాహార లోపం.`,
      action_en: "Apply Urea @ 25–30 kg/acre or organic liquid bio-nitrogen foliar spray.",
      action_hi: "यूरिया @ 25-30 किग्रा/एकड़ या जैविक तरल नाइट्रोजन फॉलियर स्प्रे लगाएं।",
      action_te: "యూరియా @ 25-30 kg/ఎకరం లేదా ఆర్గానిక్ నత్రజని ఫోలియర్ స్ప్రే వేయండి.",
    },
    insect_pest_damage: {
      en: `Insect feeding damage on ${affected_area_pct}% leaf area. Elevated pest activity with humidity at ${humidity}% provides conducive conditions.`,
      hi: `${affected_area_pct}% पत्ती पर कीट क्षति। आर्द्रता (${humidity}%) कीट गतिविधि को बढ़ावा दे रही है।`,
      te: `${affected_area_pct}% ఆకు వైశాల్యంలో పురుగుల దాడి. తేమ (${humidity}%) పురుగుల శాతాన్ని పెంచుతోంది.`,
      action_en: "Deploy sticky traps. Apply Azadirachtin (Neem Extract 1500ppm) foliar spray.",
      action_hi: "स्टिकी ट्रैप लगाएं। आज़ाडिरेक्टिन (नीम अर्क 1500ppm) का पर्णीय छिड़काव करें।",
      action_te: "స్టిక్కీ ట్రాప్లు ఏర్పాటు చేయండి. అజాడిరాక్టిన్ (వేప సారం 1500ppm) పిచికారీ చేయండి.",
    },
    healthy: {
      en: "Crop foliage is healthy with optimal cellular structure. 0% pathogen damage detected.",
      hi: "फसल की पत्तियां स्वस्थ हैं — 0% रोग का असर। इष्टतम पोषण बनी हुई है।",
      te: "పంట ఆకుల కణజాలం ఆరోగ్యంగా ఉంది — 0% తెగులు నష్టం గుర్తించబడింది.",
      action_en: "Maintain scheduled drip irrigation cycle. Continue standard monitoring.",
      action_hi: "नियमित ड्रिप सिंचाई चक्र बनाए रखें। मानक निगरानी जारी रखें।",
      action_te: "సాధారణ బిందు సేద్యం విధానాన్ని కొనసాగించండి.",
    },
  };

  return (
    TEMPLATES[disease_code] ||
    TEMPLATES[label.toLowerCase().replace(/ /g, "_")] || {
      en: `${label} detected (${severity} severity, ${affected_area_pct}% affected).`,
      hi: `${label} पाया गया (गंभीरता: ${severity}, ${affected_area_pct}% प्रभावित)।`,
      te: `${label} గుర్తించబడింది (తీవ్రత: ${severity}, ${affected_area_pct}% దెబ్బతింది).`,
      action_en: "Consult your agricultural extension officer for treatment.",
      action_hi: "उपचार के लिए अपने कृषि अधिकारी से परामर्श करें।",
      action_te: "చికిత్స కోసం మీ వ్యవసాయ విస్తరణ అధికారిని సంప్రదించండి.",
    }
  );
}

// ─── Primary: Real Backend Call ───────────────────────────────────────────────

async function callBackendVisionDiagnose(
  base64Image: string,
  telemetry: { soilMoisture: number; tempC: number; humidity: number }
): Promise<{
  diagnosis: string;
  confidence_pct: number;
  action: string;
  category: string;
  features: Record<string, number>;
  multimodal_reasoning?: string;
} | null> {
  try {
    const res = await fetch(`${ML_BASE}/api/vision-diagnose`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_base64: base64Image,
        soil_moisture: telemetry.soilMoisture,
        temp_c: telemetry.tempC,
        ec_salinity: 1.2,
      }),
      signal: AbortSignal.timeout(15000), // 15s timeout
    });

    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    console.warn("[AgriSentinel] Backend vision diagnose failed, using offline fallback:", e);
    return null;
  }
}

// ─── Combined 2-Layer Classification ─────────────────────────────────────────

export async function classifyImage(
  imageInput: HTMLImageElement | HTMLCanvasElement | string | Blob,
  contextTelemetry?: { soilMoisture?: number; tempC?: number; humidity?: number }
): Promise<InferenceResult> {
  const startTime = performance.now();

  const moisture = contextTelemetry?.soilMoisture ?? 42.5;
  const temp = contextTelemetry?.tempC ?? 31.8;
  const humidity = contextTelemetry?.humidity ?? 65;

  // Attempt backend call first
  let source: "backend" | "offline-fallback" = "backend";
  let layer1Facts: Layer1StructuredFacts;
  let layer2Explanations: Layer2Explanations;
  let actionRecommendation: string;
  let multimodalReasoning: string;

  try {
    const base64 = await toBase64(imageInput);
    const backendResult = await callBackendVisionDiagnose(base64, { soilMoisture: moisture, tempC: temp, humidity });

    if (backendResult) {
      // Map backend response to Layer1StructuredFacts
      const confidence01 = backendResult.confidence_pct / 100;
      const label = backendResult.diagnosis;
      const category = mapCategory(backendResult.category || label);
      const severity = mapSeverity(confidence01, label);
      const features = backendResult.features || {};

      // Derive affected_area_pct from browning/yellowing pixel features
      const affectedPct = Math.round(
        ((features.browning || 0) + (features.yellowing || 0)) * 100 * 0.6
      );

      // Create a stable disease_code from the label
      const disease_code = label
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/_+$/, "");

      layer1Facts = {
        disease_code,
        label,
        confidence: Math.round(confidence01 * 1000) / 1000,
        severity,
        affected_area_pct: Math.min(80, affectedPct),
        category,
      };

      // Generate trilingual Layer 2 explanations using structured facts
      layer2Explanations = generateLayer2Explanations(layer1Facts, {
        soilMoisture: moisture,
        tempC: temp,
        humidity,
      });

      // Prefer backend's action if richer
      actionRecommendation = backendResult.action || layer2Explanations.action_en;

      multimodalReasoning =
        backendResult.multimodal_reasoning ||
        `[Backend ML] ${label} classified with ${backendResult.confidence_pct}% confidence. ` +
          `Leaf features: greenness=${(features.greenness || 0).toFixed(3)}, ` +
          `yellowing=${(features.yellowing || 0).toFixed(3)}, ` +
          `browning=${(features.browning || 0).toFixed(3)}. ` +
          `Sensor context: moisture=${moisture}%, temp=${temp}°C.`;
    } else {
      throw new Error("Backend returned null");
    }
  } catch (_) {
    // Offline fallback path
    source = "offline-fallback";
    await loadModel();

    layer1Facts = runLayer1Classification(humidity, moisture, temp);
    layer2Explanations = generateLayer2Explanations(layer1Facts, {
      soilMoisture: moisture,
      tempC: temp,
      humidity,
    });
    actionRecommendation = layer2Explanations.action_en;
    multimodalReasoning = `[Offline Fallback] Sensor-only classification: moisture=${moisture}%, temp=${temp}°C, humidity=${humidity}%. No image analysis.`;
  }

  const inferenceTimeMs = Math.round((performance.now() - startTime) * 10) / 10;

  const CONFIDENCE_THRESHOLD = 0.60;
  const isUncertain = layer1Facts.confidence < CONFIDENCE_THRESHOLD;

  return {
    layer1Facts,
    layer2Explanations,
    label: isUncertain ? "Uncertain — retake photo in clearer lighting" : layer1Facts.label,
    confidence: Math.round(layer1Facts.confidence * 1000) / 10,
    category: isUncertain ? "Uncertain" : layer1Facts.category,
    inferenceTimeMs,
    isUncertain,
    actionRecommendation,
    multimodalReasoning,
    source,
  };
}
