import { OfflineStore } from './OfflineStore';

export interface OfflineAdvisoryResult {
  answer: string;
  provenance: string;
  citations: Array<{ chunk_id: string; title: string; source: string; section?: string }>;
  warnings: string[];
}

export class LocalOfflineAdvisor {
  static async generateOfflineResponse(
    query: string,
    language: 'en' | 'hi' | 'te' = 'en'
  ): Promise<OfflineAdvisoryResult> {
    const q = query.toLowerCase();
    const cachedSensors = await OfflineStore.getCachedSensorTelemetry();
    const soilMoisture = cachedSensors?.data?.soil_moisture ?? cachedSensors?.data?.soil_moisture_pct ?? null;
    const temp = cachedSensors?.data?.temperature ?? cachedSensors?.data?.temperature_c ?? 28;

    let adviceEn = '';
    let adviceHi = '';
    let adviceTe = '';
    let citation = {
      chunk_id: 'icar-pkg-offline-01',
      title: 'ICAR Standard Package of Practices & Advisory Protocols',
      source: 'Indian Council of Agricultural Research (ICAR)',
      section: 'Offline On-Device Agronomic Engine'
    };

    // 1. IRRIGATION & WATER MANAGEMENT
    if (q.includes('irriga') || q.includes('water') || q.includes('paani') || q.includes('sinchai') || q.includes('neeru') || q.includes('pump')) {
      if (soilMoisture !== null) {
        if (soilMoisture < 35) {
          adviceEn = `[OFFLINE ON-DEVICE ADVISOR]\n\nField Status: Soil moisture is at ${soilMoisture.toFixed(1)}% (BELOW critical threshold of 35%).\n\nRecommendation:\n1. Apply irrigation for 45-60 minutes.\n2. Water in the early morning or evening to minimize evaporation.\n3. Check root zone depth after 2 hours.`;
          adviceHi = `[ऑफ़लाइन स्थानीय सलाह]\n\nखेत की स्थिति: मिट्टी की नमी ${soilMoisture.toFixed(1)}% है (35% के न्यूनतम स्तर से कम)।\n\nसिफारिश:\n1. 45-60 मिनट के लिए सिंचाई करें।\n2. वाष्पीकरण कम करने के लिए सुबह या शाम को पानी दें।`;
          adviceTe = `[ఆఫ్‌లైన్ పరికర సలహా]\n\nపొలం స్థితి: నేల తేమ ${soilMoisture.toFixed(1)}% వద్ద ఉంది (35% కంటే తక్కువ).\n\nసిఫార్సు:\n1. 45-60 నిమిషాల పాటు నీటిపారుదల చేయండి.\n2. ఉదయం లేదా సాయంత్రం సమయంలో నీరు పెట్టండి.`;
        } else if (soilMoisture > 70) {
          adviceEn = `[OFFLINE ON-DEVICE ADVISOR]\n\nField Status: Soil moisture is optimal to saturated (${soilMoisture.toFixed(1)}%).\n\nRecommendation:\n1. DO NOT IRRIGATE at this time to avoid waterlogging and root rot.\n2. Ensure proper drainage channels are clear.`;
          adviceHi = `[ऑफ़लाइन स्थानीय सलाह]\n\nखेत की स्थिति: मिट्टी की नमी पर्याप्त है (${soilMoisture.toFixed(1)}%)।\n\nसिफारिश:\n1. अभी सिंचाई न करें ताकि जलभराव और जड़ों के सड़ने से बचा जा सके।`;
          adviceTe = `[ఆఫ్‌లైన్ పరికర సలహా]\n\nపొలం స్థితి: నేల తేమ సమృద్ధిగా ఉంది (${soilMoisture.toFixed(1)}%).\n\nసిఫార్సు:\n1. ఇప్పుడు నీరు పెట్టవద్దు.\n2. మురుగు కాలువలు సరిగ్గా ఉండేలా చూసుకోండి.`;
        } else {
          adviceEn = `[OFFLINE ON-DEVICE ADVISOR]\n\nField Status: Soil moisture is adequate (${soilMoisture.toFixed(1)}%).\n\nRecommendation:\n1. Next irrigation cycle recommended in 48-72 hours.\n2. Maintain Alternate Wetting and Drying (AWD) depth of 2-5 cm for rice.`;
          adviceHi = `[ऑफ़लाइन स्थानीय सलाह]\n\nखेत की स्थिति: मिट्टी की नमी सामान्य है (${soilMoisture.toFixed(1)}%)। अगले 48-72 घंटों में दोबारा जांचें।`;
          adviceTe = `[ఆఫ్‌లైన్ పరికర సలహా]\n\nపొలం స్థితి: నేల తేమ సాధారణంగా ఉంది (${soilMoisture.toFixed(1)}%). రాబోయే 2-3 రోజుల్లో మళ్లీ పరీక్షించండి.`;
        }
      } else {
        adviceEn = `[OFFLINE ON-DEVICE ADVISOR]\n\nIrrigation Protocol (General):\n1. Maintain field capacity between 50-70% for cereal crops.\n2. Adopt drip or Alternate Wetting and Drying (AWD) to save up to 30% water.\n3. Avoid irrigating if rainfall > 5mm is expected.`;
        adviceHi = `[ऑफ़लाइन स्थानीय सलाह]\n\nसिंचाई दिशा-निर्देश:\n1. फसलों के लिए 50-70% नमी बनाए रखें।\n2. पानी बचाने के लिए ड्रिप या एडब्ल्यूडी विधि अपनाएं।`;
        adviceTe = `[ఆఫ్‌లైన్ పరికర సలహా]\n\nసాగునీటి సూచనలు:\n1. తేమను 50-70% మధ్య నిర్వహించండి.\n2. బిందు సేద్యం ద్వారా 30% నీటిని ఆదా చేయండి.`;
      }
      citation = {
        chunk_id: 'fao-56-offline-irr',
        title: 'FAO-56 Irrigation & Soil Moisture Depletion Protocol',
        source: 'FAO Irrigation & Drainage Paper 56',
        section: 'Crop Evapotranspiration & AWD Guidelines'
      };
    }

    // 2. FERTILIZER & NUTRIENT (NPK)
    else if (q.includes('fertiliz') || q.includes('npk') || q.includes('urea') || q.includes('dap') || q.includes('khad') || q.includes('poshak') || q.includes('eruvu')) {
      adviceEn = `[OFFLINE ON-DEVICE ADVISOR]\n\nICAR Balanced Nutrient Management:\n1. Basal Application: Full dose of Phosphorus (DAP) and 50% Potash (MOP) at sowing.\n2. Top Dressing: Split Nitrogen (Urea) into 3 equal splits (tillering, panicle initiation, flowering).\n3. Apply Zinc Sulphate @ 25 kg/ha if yellowing appears on lower leaves.`;
      adviceHi = `[ऑफ़लाइन स्थानीय सलाह]\n\nसंतुलित उर्वरक प्रबंधन (ICAR):\n1. बुवाई के समय: डीएपी (फास्फोरस) की पूरी मात्रा और एमओपी (पोटाश) की आधी मात्रा डालें।\n2. यूरिया (नाइट्रोजन): तीन बराबर भागों में दें (कल्ले फूटते समय, बाली बनते समय और फूल आते समय)।`;
      adviceTe = `[ఆఫ్‌లైన్ పరికర సలహా]\n\nసమతుల్య ఎరువుల నిర్వహణ:\n1. విత్తే సమయంలో DAP మరియు సగం MOP వేయండి.\n2. యూరియాను మూడు దఫాలుగా వేయండి.`;
      citation = {
        chunk_id: 'icar-iiss-npk-offline',
        title: 'ICAR-IISS Fertilizer Recommendation & Soil Health Guidelines',
        source: 'Indian Institute of Soil Science (ICAR-IISS)',
        section: 'Split Nitrogen & Micronutrient Balancing'
      };
    }

    // 3. PEST & LEAF DISEASE
    else if (q.includes('disease') || q.includes('pest') || q.includes('yellow') || q.includes('spot') || q.includes('keeda') || q.includes('rog') || q.includes('purugu')) {
      adviceEn = `[OFFLINE ON-DEVICE ADVISOR]\n\nIntegrated Pest Management (IPM):\n1. Yellowing of lower leaves: Typically Nitrogen deficiency or water stagnation.\n2. Brown circular spots: Inspect for Fungal Leaf Spot / Blast. Spray Neem oil (5ml/L) as first line of defense.\n3. Install yellow sticky traps (10-12 per acre) to monitor sucking pests.\n4. Avoid excessive nitrogen application which attracts stem borers.`;
      adviceHi = `[ऑफ़लाइन स्थानीय सलाह]\n\nएकीकृत कीट प्रबंधन:\n1. पत्तियों का पीलापन: नाइट्रोजन की कमी या जलभराव के कारण हो सकता है।\n2. भूरे धब्बे: फफूंद जनित रोग (ब्लास्ट) का लक्षण। नीम का तेल (5 मिली/लीटर) छिड़कें।`;
      adviceTe = `[ఆఫ్‌లైన్ పరికర సలహా]\n\nసమగ్ర తెగుళ్ల నివారణ:\n1. ఆకులు పసుపు రంగులోకి మారడం: నత్రజని లోపం వల్ల కావచ్చు.\n2. మచ్చలు కనిపిస్తే వేప నూనెను పిచికారీ చేయండి.`;
      citation = {
        chunk_id: 'icar-ipm-offline',
        title: 'ICAR Integrated Pest & Disease Management Protocols',
        source: 'National Research Centre for Integrated Pest Management (NCIPM)',
        section: 'Biological Pest Control & Foliar Diagnostics'
      };
    }

    // 4. CROP RECOMMENDATION & SEED SELECTION
    else if (q.includes('crop') || q.includes('fasal') || q.includes('sow') || q.includes('beej') || q.includes('panta')) {
      adviceEn = `[OFFLINE ON-DEVICE ADVISOR]\n\nAgronomic Crop Advisory:\n1. Kharif Season: Rice (Paddy), Maize, Cotton, Soybean, Pulses (Arhar/Moong).\n2. Rabi Season: Wheat, Mustard, Chickpea (Gram), Barley.\n3. Choose certified high-yield drought-tolerant varieties from your local Krishi Vigyan Kendra (KVK).`;
      adviceHi = `[ऑफ़लाइन स्थानीय सलाह]\n\nफसल एवं बीज मार्गदर्शन:\n1. खरीफ: धान, मक्का, कपास, सोयाबीन, दालें।\n2. रबी: गेहूं, सरसों, चना।\n3. केवीके (KVK) द्वारा प्रमाणित उन्नत बीजों का ही चयन करें।`;
      adviceTe = `[ఆఫ్‌లైన్ పరికర సలహా]\n\nపంట సాగు సూచనలు:\n1. ఖరీఫ్: వరి, మొక్కజొన్న, పత్తి, సోయాబీన్.\n2. రబీ: గోధుమ, ఆవాలు, శనగలు.`;
      citation = {
        chunk_id: 'icar-crop-calendar-offline',
        title: 'ICAR National Agricultural Crop Calendar & Advisory',
        source: 'Ministry of Agriculture & Farmers Welfare, Govt. of India',
        section: 'Zonal Crop Suitability & Certified Seed Varieties'
      };
    }

    // 5. DEFAULT HELPFUL AGRICULTURAL ASSISTANCE
    else {
      adviceEn = `[OFFLINE ON-DEVICE ADVISOR]\n\nAgriSaathi Local Engine is active. You can ask about:\n• "When should I irrigate my field?" (Uses cached ESP32 soil moisture)\n• "What fertilizer ratio should I use for rice/wheat?"\n• "How to treat yellow leaves or leaf spots?"\n• "Crop disease prevention steps"`;
      adviceHi = `[ऑफ़लाइन स्थानीय सलाह]\n\nएग्रीसाथी ऑफ़लाइन इंजन सक्रिय है। आप पूछ सकते हैं:\n• "खेत में सिंचाई कब करें?"\n• "धान/गेहूं के लिए खाद की मात्रा?"\n• "पीली पत्तियों का उपचार?"`;
      adviceTe = `[ఆఫ్‌లైన్ పరికర సలహా]\n\nఆఫ్‌లైన్ అసిస్టెంట్ సిద్ధంగా ఉంది. మీరు అడగవచ్చు:\n• "నీటిపారుదల ఎప్పుడు చేయాలి?"\n• "ఎరువుల మోతాదు ఎంత?"\n• "ఆకుల పసుపు రంగు నివారణ?"`;
    }

    const selectedText = language === 'hi' ? adviceHi : language === 'te' ? adviceTe : adviceEn;

    return {
      answer: selectedText,
      provenance: 'OFFLINE_ONDEVICE_ENGINE',
      citations: [citation],
      warnings: ['Offline mode: Generated locally using on-device agronomic intelligence & cached telemetry.']
    };
  }
}
