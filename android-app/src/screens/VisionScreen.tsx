import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { theme } from '../styles/theme';
import { ApiClient } from '../services/ApiClient';
import { ProvenanceBadge } from '../components/ProvenanceBadge';

const CROPS = ['Rice', 'Wheat', 'Tomato', 'Cotton', 'Potato'];

type VisionResult = {
  status?: string;
  diagnosis?: string | null;
  confidence_pct?: number | null;
  action?: string;
  reason?: string;
  provenance?: string;
  model_name?: string;
  model_version?: string | null;
  warning?: string;
  quality?: Record<string, number>;
};

export function VisionScreen() {
  const [selectedCrop, setSelectedCrop] = useState('Rice');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VisionResult | null>(null);

  const chooseFromLibrary = async () => {
    setResult(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Photo access required', 'Allow photo access to select a crop leaf image.');
      return;
    }

    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.9,
      base64: true,
    });

    if (!picked.canceled && picked.assets[0]?.base64) {
      setImageUri(picked.assets[0].uri);
      setImageBase64(picked.assets[0].base64);
    }
  };

  const takePhoto = async () => {
    setResult(null);
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Camera access required', 'Allow camera access to photograph a crop leaf.');
      return;
    }

    const captured = await ImagePicker.launchCameraAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.9,
      base64: true,
    });

    if (!captured.canceled && captured.assets[0]?.base64) {
      setImageUri(captured.assets[0].uri);
      setImageBase64(captured.assets[0].base64);
    }
  };

  const reset = () => {
    setImageUri(null);
    setImageBase64(null);
    setResult(null);
    setLoading(false);
  };

  const handleDiagnose = async () => {
    if (!imageBase64) {
      Alert.alert('No image selected', 'Take a photo or upload a clear crop leaf image first.');
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const res = await ApiClient.vision.diagnoseLeafImage(imageBase64, selectedCrop, 'Vegetative');
      setResult(res || {
        status: 'NO_RELIABLE_RESULT',
        diagnosis: null,
        confidence_pct: null,
        action: 'No result was returned by the vision service.',
      });
    } catch (error: any) {
      setResult({
        status: 'NETWORK_OR_SERVER_ERROR',
        diagnosis: null,
        confidence_pct: null,
        action: 'The image could not be analyzed. Check the backend connection and try again.',
        reason: error?.message || 'Vision request failed.',
      });
    } finally {
      setLoading(false);
    }
  };

  const predictionAvailable = result?.status === 'EXPERIMENTAL_PREDICTION' && !!result.diagnosis;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer} showsVerticalScrollIndicator={false}>
      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.screenTitle}>Leaf Disease Diagnostics</Text>
          <Text style={styles.screenSub}>Upload the actual leaf photo — no demo image or fallback diagnosis</Text>
        </View>
        <ProvenanceBadge source="EXPERIMENTAL" label="EXPERIMENTAL AI" />
      </View>

      <View style={styles.cropRow}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {CROPS.map((crop) => (
            <TouchableOpacity
              key={crop}
              style={[styles.cropChip, selectedCrop === crop && styles.cropChipActive]}
              onPress={() => setSelectedCrop(crop)}
            >
              <Text style={[styles.cropChipText, selectedCrop === crop && styles.cropChipTextActive]}>{crop}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      <View style={styles.scannerCard}>
        {imageUri ? (
          <Image source={{ uri: imageUri }} style={styles.preview} resizeMode="cover" />
        ) : (
          <View style={styles.placeholder}>
            <Text style={{ fontSize: 44 }}>🍃</Text>
            <Text style={styles.scannerPrompt}>Select or photograph one crop leaf</Text>
            <Text style={styles.scannerTip}>Use good lighting and keep the leaf in focus</Text>
          </View>
        )}

        <View style={styles.actionRow}>
          <TouchableOpacity style={styles.secondaryBtn} onPress={takePhoto} disabled={loading}>
            <Text style={styles.secondaryBtnText}>📷 Take Photo</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.secondaryBtn} onPress={chooseFromLibrary} disabled={loading}>
            <Text style={styles.secondaryBtnText}>🖼️ Upload Image</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.resetBtn} onPress={reset} disabled={loading}>
            <Text style={styles.resetBtnText}>Reset</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.primaryScanBtn} onPress={handleDiagnose} disabled={loading || !imageBase64}>
          {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.primaryScanBtnText}>🔬 Analyze Actual Leaf Photo</Text>}
        </TouchableOpacity>
      </View>

      {result && (
        <View style={[styles.resultCard, !predictionAvailable && styles.resultCardWarning]}>
          <View style={styles.resultHeader}>
            <View style={styles.diseaseIconBadge}>
              <Text style={{ fontSize: 24 }}>{predictionAvailable ? '🔬' : '⚠️'}</Text>
            </View>
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={[styles.diagnosisTag, !predictionAvailable && { color: theme.colors.warning }]}>VISION STATUS</Text>
              <Text style={styles.diseaseName}>{predictionAvailable ? result.diagnosis : formatStatus(result.status)}</Text>
              {!!result.reason && <Text style={styles.pathogenName}>{result.reason}</Text>}
            </View>
            <ProvenanceBadge source={result.provenance || (predictionAvailable ? 'EXPERIMENTAL' : 'UNAVAILABLE')} size="small" />
          </View>

          {predictionAvailable ? (
            <>
              <View style={styles.metricsRow}>
                <View style={styles.metricBox}>
                  <Text style={styles.metricBoxLabel}>Confidence</Text>
                  <Text style={styles.metricBoxVal}>{(result.confidence_pct ?? 0).toFixed(1)}%</Text>
                </View>
                <View style={styles.metricBox}>
                  <Text style={styles.metricBoxLabel}>Crop context</Text>
                  <Text style={styles.metricBoxVal}>{selectedCrop}</Text>
                </View>
                <View style={styles.metricBox}>
                  <Text style={styles.metricBoxLabel}>Model</Text>
                  <Text style={styles.metricBoxVal}>Experimental</Text>
                </View>
              </View>
              <View style={styles.divider} />
              <View style={styles.treatmentSection}>
                <Text style={styles.treatmentTitle}>Recommended next step</Text>
                <Text style={styles.treatmentBody}>{result.action || 'Confirm the result with a qualified agronomist.'}</Text>
              </View>
              {!!result.warning && <Text style={styles.warningText}>{result.warning}</Text>}
            </>
          ) : (
            <View style={styles.treatmentSection}>
              <Text style={styles.treatmentBody}>{result.action || 'No diagnosis was made.'}</Text>
              <Text style={styles.warningText}>No disease name or confidence is shown because the image was not reliably analyzed.</Text>
            </View>
          )}
        </View>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

function formatStatus(status?: string) {
  return (status || 'NO_RELIABLE_RESULT').replaceAll('_', ' ');
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAF8' },
  contentContainer: { padding: 16, paddingBottom: 110 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  screenTitle: { fontSize: 18, fontWeight: '800', color: theme.colors.textPrimary },
  screenSub: { fontSize: 12, color: theme.colors.textSecondary, marginTop: 2, paddingRight: 8 },
  cropRow: { marginBottom: 14 },
  cropChip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E2E8F0', marginRight: 8 },
  cropChipActive: { backgroundColor: theme.colors.primary, borderColor: theme.colors.primary },
  cropChipText: { fontSize: 11, fontWeight: '700', color: '#64748B' },
  cropChipTextActive: { color: '#FFFFFF' },
  scannerCard: { backgroundColor: '#FFFFFF', borderRadius: 14, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: '#E2E8F0' },
  preview: { width: '100%', height: 230, borderRadius: 12, backgroundColor: '#E2E8F0' },
  placeholder: { height: 230, borderRadius: 12, backgroundColor: '#0F172A', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20 },
  scannerPrompt: { color: '#F8FAFC', fontSize: 13, fontWeight: '700', textAlign: 'center', marginTop: 8 },
  scannerTip: { color: '#94A3B8', fontSize: 11, marginTop: 4, textAlign: 'center' },
  actionRow: { flexDirection: 'row', gap: 8, marginTop: 12 },
  secondaryBtn: { flex: 1, minHeight: 48, borderRadius: 10, backgroundColor: '#F1F5F9', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 6 },
  secondaryBtnText: { color: '#334155', fontSize: 12, fontWeight: '700', textAlign: 'center' },
  resetBtn: { minWidth: 58, borderRadius: 10, backgroundColor: '#FEE2E2', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 },
  resetBtnText: { color: '#B91C1C', fontSize: 12, fontWeight: '800' },
  primaryScanBtn: { marginTop: 12, backgroundColor: theme.colors.primary, borderRadius: 10, paddingVertical: 13, alignItems: 'center' },
  primaryScanBtnText: { color: '#FFFFFF', fontSize: 14, fontWeight: '700' },
  resultCard: { backgroundColor: '#FFFFFF', borderRadius: 14, padding: 16, borderWidth: 1, borderColor: '#E2E8F0' },
  resultCardWarning: { borderColor: '#FCD34D' },
  resultHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  diseaseIconBadge: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#FEE2E2', alignItems: 'center', justifyContent: 'center' },
  diagnosisTag: { fontSize: 10, fontWeight: '800', color: '#DC2626', letterSpacing: 0.5 },
  diseaseName: { fontSize: 16, fontWeight: '800', color: theme.colors.textPrimary },
  pathogenName: { fontSize: 11, color: '#64748B', marginTop: 3 },
  metricsRow: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: '#F8FAFC', borderRadius: 8, padding: 8, marginBottom: 12 },
  metricBox: { flex: 1, alignItems: 'center' },
  metricBoxLabel: { fontSize: 10, color: '#64748B', marginBottom: 2, textAlign: 'center' },
  metricBoxVal: { fontSize: 12, fontWeight: '700', color: theme.colors.textPrimary, textAlign: 'center' },
  divider: { height: 1, backgroundColor: '#E2E8F0', marginBottom: 12 },
  treatmentSection: { marginBottom: 12 },
  treatmentTitle: { fontSize: 12, fontWeight: '700', color: theme.colors.textPrimary, marginBottom: 4 },
  treatmentBody: { fontSize: 12, color: '#475569', lineHeight: 18 },
  warningText: { fontSize: 11, color: '#92400E', lineHeight: 16, marginTop: 8 },
});
