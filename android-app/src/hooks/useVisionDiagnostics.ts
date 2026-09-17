import { useState } from 'react';
import { Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { ApiClient } from '../services/ApiClient';

export type VisionResult = {
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

export function useVisionDiagnostics() {
  const [selectedCrop, setSelectedCrop] = useState('Rice');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VisionResult | null>(null);

  const chooseFromLibrary = async () => {
    setResult(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      return Alert.alert('Photo access required', 'Allow photo access to select a crop leaf image.');
    }
    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
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
      return Alert.alert('Camera access required', 'Allow camera access to photograph a crop leaf.');
    }
    const captured = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
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
      return Alert.alert('No image selected', 'Take a photo or upload a clear crop leaf image first.');
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await ApiClient.vision.diagnoseLeafImage(imageBase64, selectedCrop, 'Vegetative');
      setResult(res || { status: 'NO_RELIABLE_RESULT', diagnosis: null, confidence_pct: null, action: 'No result was returned by the vision service.' });
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

  return {
    selectedCrop,
    setSelectedCrop,
    imageUri,
    imageBase64,
    loading,
    result,
    chooseFromLibrary,
    takePhoto,
    reset,
    handleDiagnose,
  };
}
