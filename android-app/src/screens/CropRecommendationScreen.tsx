import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  TextInput,
  Alert,
} from 'react-native';
import { theme } from '../styles/theme';
import { ApiClient } from '../services/ApiClient';
import { ProvenanceBadge } from '../components/ProvenanceBadge';

interface AlternativeCropItem {
  crop: string;
  probability?: number;
  confidence_pct?: number;
}

interface CropResultData {
  recommended_crop: string;
  prediction_confidence: number | null;
  test_accuracy: number;
  model_version: string;
  source: string;
  provenance: string;
  prediction_timestamp?: string;
  request_id?: string;
  alternative_crops: AlternativeCropItem[];
  explanation: string;
  warnings: string[];
}

export function CropRecommendationScreen() {
  // Input parameters
  const [n, setN] = useState('90');
  const [p, setP] = useState('42');
  const [k, setK] = useState('43');
  const [temp, setTemp] = useState('26.8');
  const [humidity, setHumidity] = useState('68.4');
  const [ph, setPh] = useState('6.5');
  const [rainfall, setRainfall] = useState('180');

  // UI state
  const [loading, setLoading] = useState(false);
  const [fetchingTelemetry, setFetchingTelemetry] = useState(false);
  const [telemetryPrefilled, setTelemetryPrefilled] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<CropResultData | null>(null);

  const capitalize = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : '');

  const fetchLiveTelemetry = async () => {
    setFetchingTelemetry(true);
    setErrorMsg(null);
    try {
      const res = await ApiClient.sensor.getTelemetry('ESP32_NODE_01', 1);
      const latest = Array.isArray(res)
        ? res[0]
        : (res?.history && res.history.length > 0
            ? res.history[0]
            : (res?.readings?.[0] || res?.latest || res));
      if (latest && (latest.soil_moisture_pct !== undefined || latest.temperature_c !== undefined || latest.nitrogen !== undefined)) {
        if (latest.nitrogen != null || latest.soil_n != null) setN(String(latest.nitrogen ?? latest.soil_n));
        if (latest.phosphorus != null || latest.soil_p != null) setP(String(latest.phosphorus ?? latest.soil_p));
        if (latest.potassium != null || latest.soil_k != null) setK(String(latest.potassium ?? latest.soil_k));
        if (latest.ph != null || latest.soil_ph != null) setPh(String(latest.ph ?? latest.soil_ph));
        if (latest.temperature_c != null || latest.temperature != null) setTemp(String(latest.temperature_c ?? latest.temperature));
        if (latest.humidity_pct != null || latest.humidity != null) setHumidity(String(latest.humidity_pct ?? latest.humidity));
        setTelemetryPrefilled(true);
      } else {
        Alert.alert('Notice', 'No live telemetry packet found on server. You can enter values manually.');
      }
    } catch (e: any) {
      Alert.alert('Offline Notice', 'Could not reach sensor telemetry backend. You can enter values manually.');
    } finally {
      setFetchingTelemetry(false);
    }
  };

  const resetDefaults = () => {
    setN('90');
    setP('42');
    setK('43');
    setTemp('26.8');
    setHumidity('68.4');
    setPh('6.5');
    setRainfall('180');
    setTelemetryPrefilled(false);
    setErrorMsg(null);
  };

  const runRecommendation = async () => {
    // Validation
    const nVal = parseFloat(n);
    const pVal = parseFloat(p);
    const kVal = parseFloat(k);
    const tempVal = parseFloat(temp);
    const humVal = parseFloat(humidity);
    const phVal = parseFloat(ph);
    const rainVal = parseFloat(rainfall);

    if (isNaN(nVal) || isNaN(pVal) || isNaN(kVal) || isNaN(tempVal) || isNaN(humVal) || isNaN(phVal) || isNaN(rainVal)) {
      setErrorMsg('Please enter valid numeric values for all fields.');
      return;
    }

    if (phVal < 0 || phVal > 14) {
      setErrorMsg('Soil pH must be between 0.0 and 14.0.');
      return;
    }

    if (humVal < 0 || humVal > 100) {
      setErrorMsg('Humidity percentage must be between 0 and 100%.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      const res = await ApiClient.crop.recommendCrop({
        N: nVal,
        P: pVal,
        K: kVal,
        temperature: tempVal,
        humidity: humVal,
        ph: phVal,
        rainfall: rainVal,
      });

      if (res && res.recommended_crop) {
        setResult({
          recommended_crop: res.recommended_crop,
          prediction_confidence: res.prediction_confidence ?? res.confidence ?? null,
          test_accuracy: res.test_accuracy ?? 99.1,
          model_version: res.model_version ?? 'rf-crop-v1.0',
          source: res.source ?? 'MODEL_PREDICTION',
          provenance: res.provenance ?? 'MODEL_PREDICTION',
          prediction_timestamp: res.prediction_timestamp,
          request_id: res.request_id,
          alternative_crops: res.alternative_crops || [],
          explanation: res.explanation || '',
          warnings: res.warnings || [],
        });
      } else {
        throw new Error('Invalid response structure from backend.');
      }
    } catch (e: any) {
      console.warn('Backend recommendation error:', e.message);
      setErrorMsg(`Could not complete prediction: ${e.message || 'Backend unreachable'}. Check settings & connection.`);
    } finally {
      setLoading(false);
    }
  };

  // Run initial prediction on mount
  useEffect(() => {
    runRecommendation();
  }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer} showsVerticalScrollIndicator={false}>
      {/* Screen Title & Header */}
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.screenTitle}>AI Crop Recommendation</Text>
          <Text style={styles.screenSub}>Agronomic soil & climate precision matching</Text>
        </View>
        <ProvenanceBadge source="MODEL_PREDICTION" label="RF MODEL" />
      </View>

      {/* Sensor Pre-fill & Autofill Bar */}
      <View style={styles.prefillCard}>
        <Text style={styles.prefillIcon}>📡</Text>
        <View style={{ flex: 1, marginLeft: 8 }}>
          <Text style={styles.prefillTitle}>
            {telemetryPrefilled ? 'Prefilled from ESP32 Sensor' : 'Sensor Telemetry Integration'}
          </Text>
          <Text style={styles.prefillSub}>
            {telemetryPrefilled ? 'Live NPK, pH & Climate values loaded' : 'Load live values from Node 01'}
          </Text>
        </View>
        <TouchableOpacity
          style={[styles.prefillBtn, fetchingTelemetry && styles.prefillBtnDisabled]}
          onPress={fetchLiveTelemetry}
          disabled={fetchingTelemetry}
        >
          {fetchingTelemetry ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : (
            <Text style={styles.prefillBtnText}>Sync Sensors</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Input Parameters Form Card */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <Text style={styles.cardTitle}>Soil Nutrients & Climate Inputs</Text>
          <TouchableOpacity onPress={resetDefaults}>
            <Text style={styles.resetBtnText}>Reset</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.inputGrid}>
          <View style={styles.inputBox}>
            <Text style={styles.inputLabel}>Nitrogen (N) <Text style={styles.unitText}>mg/kg</Text></Text>
            <TextInput style={styles.input} value={n} onChangeText={setN} keyboardType="numeric" placeholder="0-140" />
          </View>
          <View style={styles.inputBox}>
            <Text style={styles.inputLabel}>Phosphorus (P) <Text style={styles.unitText}>mg/kg</Text></Text>
            <TextInput style={styles.input} value={p} onChangeText={setP} keyboardType="numeric" placeholder="0-145" />
          </View>
          <View style={styles.inputBox}>
            <Text style={styles.inputLabel}>Potassium (K) <Text style={styles.unitText}>mg/kg</Text></Text>
            <TextInput style={styles.input} value={k} onChangeText={setK} keyboardType="numeric" placeholder="0-205" />
          </View>
          <View style={styles.inputBox}>
            <Text style={styles.inputLabel}>Soil pH <Text style={styles.unitText}>0-14</Text></Text>
            <TextInput style={styles.input} value={ph} onChangeText={setPh} keyboardType="numeric" placeholder="3.5-9.0" />
          </View>
          <View style={styles.inputBox}>
            <Text style={styles.inputLabel}>Air Temp <Text style={styles.unitText}>°C</Text></Text>
            <TextInput style={styles.input} value={temp} onChangeText={setTemp} keyboardType="numeric" placeholder="8-45" />
          </View>
          <View style={styles.inputBox}>
            <Text style={styles.inputLabel}>Humidity <Text style={styles.unitText}>%</Text></Text>
            <TextInput style={styles.input} value={humidity} onChangeText={setHumidity} keyboardType="numeric" placeholder="10-100" />
          </View>
          <View style={[styles.inputBox, { width: '100%' }]}>
            <Text style={styles.inputLabel}>Expected Rainfall <Text style={styles.unitText}>mm</Text></Text>
            <TextInput style={styles.input} value={rainfall} onChangeText={setRainfall} keyboardType="numeric" placeholder="20-300" />
          </View>
        </View>

        {errorMsg && (
          <View style={styles.errorBanner}>
            <Text style={styles.errorBannerText}>{errorMsg}</Text>
          </View>
        )}

        <TouchableOpacity style={styles.predictButton} onPress={runRecommendation} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#FFFFFF" size="small" />
          ) : (
            <Text style={styles.predictButtonText}>Predict Optimal Crops</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Best Recommended Crop Card */}
      {result && (
        <View style={styles.resultCard}>
          <View style={styles.resultHeader}>
            <View style={styles.cropIconBadge}>
              <Text style={{ fontSize: 26 }}>🌾</Text>
            </View>
            <View style={{ flex: 1, marginLeft: 12 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 2 }}>
                <Text style={styles.bestMatchLabel}>PRIMARY RECOMMENDATION</Text>
              </View>
              <Text style={styles.cropName}>{capitalize(result.recommended_crop)}</Text>
              <Text style={styles.cropConfidence}>
                Prediction Confidence:{' '}
                <Text style={{ fontWeight: '800', color: theme.colors.primary }}>
                  {result.prediction_confidence != null ? `${result.prediction_confidence.toFixed(1)}%` : 'Unavailable'}
                </Text>
              </Text>
            </View>
            <ProvenanceBadge source={result.provenance} />
          </View>

          {/* Model Accuracy vs Prediction Confidence Explanation */}
          <View style={styles.modelMetaBox}>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Model Benchmark Accuracy:</Text>
              <Text style={styles.metaVal}>{result.test_accuracy}% (Test Set)</Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Model Architecture:</Text>
              <Text style={styles.metaVal}>Random Forest (22 Crop Classes)</Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Model Version:</Text>
              <Text style={styles.metaVal}>{result.model_version}</Text>
            </View>
          </View>

          <View style={styles.divider} />

          {/* Agronomic Explanation */}
          {result.explanation ? (
            <View style={styles.explanationSection}>
              <Text style={styles.sectionTitle}>Agronomic Rationale</Text>
              <Text style={styles.explanationText}>{result.explanation}</Text>
            </View>
          ) : null}

          {/* Boundary / Condition Warnings */}
          {result.warnings && result.warnings.length > 0 && (
            <View style={styles.warningsSection}>
              {result.warnings.map((w, idx) => (
                <View key={idx} style={styles.warningItem}>
                  <Text style={styles.warningText}>{w}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Alternative Ranked Crops */}
          {result.alternative_crops && result.alternative_crops.length > 0 && (
            <View style={styles.alternativesSection}>
              <Text style={styles.sectionTitle}>Top Viable Alternative Crops</Text>
              {result.alternative_crops.map((alt, idx) => (
                <View key={idx} style={styles.altRow}>
                  <View style={styles.altRankBadge}>
                    <Text style={styles.altRankText}>#{idx + 2}</Text>
                  </View>
                  <Text style={styles.altName}>{capitalize(alt.crop)}</Text>
                  <View style={styles.altBarContainer}>
                    <View style={[styles.altBarFill, { width: `${Math.min(alt.confidence_pct || 0, 100)}%` }]} />
                  </View>
                  <Text style={styles.altPct}>
                    {alt.confidence_pct != null ? `${alt.confidence_pct.toFixed(1)}%` : 'Viable'}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>
      )}

      {/* Extra Bottom Clearance */}
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAF8',
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 110, // Generous clearance for bottom navigation
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  screenTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: theme.colors.textPrimary,
  },
  screenSub: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  prefillCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  prefillIcon: {
    fontSize: 20,
  },
  prefillTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  prefillSub: {
    fontSize: 11,
    color: theme.colors.textSecondary,
  },
  prefillBtn: {
    backgroundColor: theme.colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  prefillBtnDisabled: {
    opacity: 0.6,
  },
  prefillBtnText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  resetBtnText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#64748B',
  },
  inputGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  inputBox: {
    width: '48%',
    marginBottom: 12,
  },
  inputLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.textSecondary,
    marginBottom: 4,
  },
  unitText: {
    fontSize: 10,
    fontWeight: '400',
    color: '#94A3B8',
  },
  input: {
    backgroundColor: '#F8FAFC',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    color: theme.colors.textPrimary,
  },
  errorBanner: {
    backgroundColor: '#FEE2E2',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
  },
  errorBannerText: {
    color: '#B91C1C',
    fontSize: 12,
    fontWeight: '600',
  },
  predictButton: {
    backgroundColor: theme.colors.primary,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 4,
  },
  predictButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  resultCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: '#DCFCE7',
    marginBottom: 16,
  },
  resultHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  cropIconBadge: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#DCFCE7',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bestMatchLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: theme.colors.primary,
    letterSpacing: 0.5,
  },
  cropName: {
    fontSize: 20,
    fontWeight: '800',
    color: theme.colors.textPrimary,
  },
  cropConfidence: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  modelMetaBox: {
    backgroundColor: '#F8FAFC',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  metaLabel: {
    fontSize: 11,
    color: '#64748B',
  },
  metaVal: {
    fontSize: 11,
    fontWeight: '700',
    color: '#1E293B',
  },
  divider: {
    height: 1,
    backgroundColor: '#E2E8F0',
    marginVertical: 12,
  },
  explanationSection: {
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: theme.colors.textPrimary,
    marginBottom: 6,
  },
  explanationText: {
    fontSize: 12,
    color: '#475569',
    lineHeight: 18,
  },
  warningsSection: {
    marginBottom: 12,
  },
  warningItem: {
    backgroundColor: '#FEF3C7',
    padding: 8,
    borderRadius: 6,
    marginBottom: 6,
  },
  warningText: {
    fontSize: 11,
    color: '#92400E',
  },
  alternativesSection: {
    marginTop: 6,
  },
  altRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  altRankBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  altRankText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#64748B',
  },
  altName: {
    width: 70,
    fontSize: 13,
    fontWeight: '600',
    color: theme.colors.textPrimary,
  },
  altBarContainer: {
    flex: 1,
    height: 8,
    backgroundColor: '#E2E8F0',
    borderRadius: 4,
    marginHorizontal: 8,
    overflow: 'hidden',
  },
  altBarFill: {
    height: '100%',
    backgroundColor: theme.colors.primary,
    borderRadius: 4,
  },
  altPct: {
    width: 44,
    fontSize: 11,
    fontWeight: '700',
    color: '#475569',
    textAlign: 'right',
  },
});
