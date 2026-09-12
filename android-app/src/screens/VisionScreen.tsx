import React, { useState } from 'react';
import {
  Alert,
  ActivityIndicator,
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

type VisionResult = {
  status?: string;
  prediction?: string | null;
  diagnosis?: string | null;
  confidence?: number | null;
  confidence_pct?: number | null;
  model_status?: string;
  provenance?: string;
  warning?: string;
  evidence?: string[];
  remedy?: string;
  action?: string;
  crop?: string | null;
};

export function VisionScreen() {
  const [selectedCrop, setSelectedCrop] = useState<string | null>(null);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VisionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const chooseImage = async () => {
    setResult(null);
    setError(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError('Photo-library permission is required to select a leaf image.');
      return;
    }

    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.9,
      base64: true,
    });

    if (picked.canceled || !picked.assets?.[0]) return;
    const asset = picked.assets[0];
    if (!asset.base64) {
      setError('The selected image could not be read. Please choose another image.');
      return;
    }
    setImageUri(asset.uri);
    setImageBase64(asset.base64);
  };

  const takePhoto = async () => {
    setResult(null);
    setError(null);
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      setError('Camera permission is required to take a leaf photo.');
      return;
    }

    const captured = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      quality: 0.9,
      base64: true,
    });

    if (captured.canceled || !captured.assets?.[0]) return;
    const asset = captured.assets[0];
    if (!asset.base64) {
      setError('The captured image could not be read. Please try again.');
      return;
    }
    setImageUri(asset.uri);
    setImageBase64(asset.base64);
  };

  const handleDiagnose = async () => {
    if (!imageBase64) {
      setError('Select or capture a clear crop-leaf photo before analyzing.');
      return;
    }

    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const response = await ApiClient.vision.diagnoseLeafImage(
        imageBase64,
        selectedCrop ?? undefined,
        'Vegetative',
      );
      setResult(response || { status: 'NO_RELIABLE_RESULT' });
    } catch (e: any) {
      setError(e?.message || 'Vision analysis failed. No diagnosis was produced.');
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setImageUri(null);
    setImageBase64(null);
    setResult(null);
    setError(null);
    setSelectedCrop(null);
  };

  const prediction = result?.prediction ?? result?.diagnosis ?? null;
  const confidence = result?.confidence_pct != null
    ? result.confidence_pct
    : result?.confidence != null
      ? result.confidence * 100
      : null;
  const reliable = result?.status === 'PREDICTION_AVAILABLE' && !!prediction && confidence != null;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer} showsVerticalScrollIndicator={false}>
      <View style={styles.headerRow}>
        <View style={styles.headerText}>
          <Text style={styles.screenTitle}>Leaf Disease Diagnostics</Text>
          <Text style={styles.screenSub}>Upload a real crop-leaf photo for analysis</Text>
        </View>
        <ProvenanceBadge source="EXPERIMENTAL" label="EXPERIMENTAL AI" />
      </View>

      <View style={styles.cropRow}>
        {['Rice', 'Wheat', 'Tomato', 'Cotton', 'Potato'].map((crop) => (
          <TouchableOpacity
            key={crop}
            style={[styles.cropChip, selectedCrop === crop && styles.cropChipActive]}
            onPress={() => setSelectedCrop(crop)}
          >
            <Text style={[styles.cropChipText, selectedCrop === crop && styles.cropChipTextActive]}>{crop}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.scannerCard}>
        <View style={styles.previewFrame}>
          {imageUri ? (
            <Image source={{ uri: imageUri }} style={styles.previewImage} resizeMode="contain" />
          ) : (
            <View style={styles.emptyPreview}>
              <Text style={styles.leafEmoji}>🍃</Text>
              <Text style={styles.scannerPrompt}>Choose a clear close-up leaf photo</Text>
              <Text style={styles.scannerTip}>Do not upload screenshots, documents, or unrelated images</Text>
            </View>
          )}
        </View>

        <View style={styles.actionRow}>
          <TouchableOpacity style={styles.secondaryButton} onPress={takePhoto} disabled={loading}>
            <Text style={styles.secondaryButtonText}>Take Photo</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.secondaryButton} onPress={chooseImage} disabled={loading}>
            <Text style={styles.secondaryButtonText}>Upload Image</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.resetButton} onPress={reset} disabled={loading}>
            <Text style={styles.resetButtonText}>Reset</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.primaryButton} onPress={handleDiagnose} disabled={loading || !imageBase64}>
          {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.primaryButtonText}>Analyze Selected Photo</Text>}
        </TouchableOpacity>
      </View>

      {error && (
        <View style={styles.errorCard}>
          <Text style={styles.errorTitle}>Analysis unavailable</Text>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {result && (
        <View style={styles.resultCard}>
          <View style={styles.resultHeader}>
            <View style={styles.diseaseIconBadge}><Text style={styles.iconText}>🔬</Text></View>
            <View style={styles.resultHeaderText}>
              <Text style={styles.diagnosisTag}>{reliable ? 'MODEL RESULT' : 'NO RELIABLE DIAGNOSIS'}</Text>
              <Text style={styles.diseaseName}>{reliable ? prediction : 'Unable to determine'}</Text>
              <Text style={styles.pathogenName}>{result.warning || 'No diagnosis is shown unless the image and model pass validation.'}</Text>
            </View>
            <ProvenanceBadge source={result.provenance || 'UNAVAILABLE'} size="small" />
          </View>

          {reliable ? (
            <View style={styles.metricsRow}>
              <View style={styles.metricBox}>
                <Text style={styles.metricBoxLabel}>Confidence</Text>
                <Text style={styles.metricBoxVal}>{confidence!.toFixed(1)}%</Text>
              </View>
              <View style={styles.metricBox}>
                <Text style={styles.metricBoxLabel}>Crop</Text>
                <Text style={styles.metricBoxVal}>{selectedCrop || result.crop || 'Not identified'}</Text>
              </View>
              <View style={styles.metricBox}>
                <Text style={styles.metricBoxLabel}>Status</Text>
                <Text style={styles.metricBoxVal}>Experimental</Text>
              </View>
            </View>
          ) : (
            <Text style={styles.noResultText}>Upload a clear close-up photograph of one crop leaf. The app will not assign a crop, disease, severity, or confidence to an invalid image.</Text>
          )}

          {reliable && (result.remedy || result.action) && (
            <View style={styles.treatmentSection}>
              <Text style={styles.treatmentTitle}>Suggested next step</Text>
              <Text style={styles.treatmentBody}>{result.remedy || result.action}</Text>
            </View>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAF8' },
  contentContainer: { padding: 16, paddingBottom: 110 },
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  headerText: { flex: 1, marginRight: 8 },
  screenTitle: { fontSize: 18, fontWeight: '800', color: theme.colors.textPrimary },
  screenSub: { fontSize: 12, color: theme.colors.textSecondary, marginTop: 2 },
  cropRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 14 },
  cropChip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E2E8F0', marginRight: 8, marginBottom: 8 },
  cropChipActive: { backgroundColor: theme.colors.primary, borderColor: theme.colors.primary },
  cropChipText: { fontSize: 11, fontWeight: '700', color: '#64748B' },
  cropChipTextActive: { color: '#FFFFFF' },
  scannerCard: { backgroundColor: '#FFFFFF', borderRadius: 14, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: '#E2E8F0' },
  previewFrame: { height: 220, backgroundColor: '#0F172A', borderRadius: 12, overflow: 'hidden', alignItems: 'center', justifyContent: 'center' },
  previewImage: { width: '100%', height: '100%' },
  emptyPreview: { alignItems: 'center', paddingHorizontal: 20 },
  leafEmoji: { fontSize: 44, marginBottom: 8 },
  scannerPrompt: { color: '#F8FAFC', fontSize: 13, fontWeight: '700', textAlign: 'center' },
  scannerTip: { color: '#CBD5E1', fontSize: 11, marginTop: 6, textAlign: 'center' },
  actionRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 12 },
  secondaryButton: { flex: 1, minWidth: 90, borderWidth: 1, borderColor: '#CBD5E1', borderRadius: 10, paddingVertical: 11, alignItems: 'center', marginRight: 8, marginBottom: 8 },
  secondaryButtonText: { color: '#334155', fontWeight: '700', fontSize: 12 },
  resetButton: { borderWidth: 1, borderColor: '#FCA5A5', borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11, alignItems: 'center', marginBottom: 8 },
  resetButtonText: { color: '#B91C1C', fontWeight: '700', fontSize: 12 },
  primaryButton: { backgroundColor: theme.colors.primary, borderRadius: 10, paddingVertical: 13, alignItems: 'center', marginTop: 4 },
  primaryButtonText: { color: '#FFFFFF', fontSize: 14, fontWeight: '700' },
  errorCard: { backgroundColor: '#FEF2F2', borderRadius: 14, padding: 16, borderWidth: 1, borderColor: '#FECACA', marginBottom: 14 },
  errorTitle: { color: '#991B1B', fontWeight: '800', marginBottom: 4 },
  errorText: { color: '#7F1D1D', fontSize: 13, lineHeight: 19 },
  resultCard: { backgroundColor: '#FFFFFF', borderRadius: 14, padding: 16, borderWidth: 1, borderColor: '#E2E8F0' },
  resultHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  diseaseIconBadge: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#FEE2E2', alignItems: 'center', justifyContent: 'center' },
  iconText: { fontSize: 24 },
  resultHeaderText: { flex: 1, marginLeft: 12, marginRight: 8 },
  diagnosisTag: { fontSize: 10, fontWeight: '800', color: '#DC2626', letterSpacing: 0.5 },
  diseaseName: { fontSize: 17, fontWeight: '800', color: theme.colors.textPrimary },
  pathogenName: { fontSize: 11, color: '#64748B', fontStyle: 'italic', marginTop: 4 },
  metricsRow: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: '#F8FAFC', borderRadius: 8, padding: 8, marginBottom: 12 },
  metricBox: { flex: 1, alignItems: 'center' },
  metricBoxLabel: { fontSize: 10, color: '#64748B', marginBottom: 2 },
  metricBoxVal: { fontSize: 12, fontWeight: '700', color: theme.colors.textPrimary, textAlign: 'center' },
  noResultText: { color: '#475569', fontSize: 13, lineHeight: 19 },
  treatmentSection: { marginTop: 12 },
  treatmentTitle: { fontSize: 12, fontWeight: '700', color: theme.colors.textPrimary, marginBottom: 4 },
  treatmentBody: { fontSize: 12, color: '#475569', lineHeight: 18 },
});
