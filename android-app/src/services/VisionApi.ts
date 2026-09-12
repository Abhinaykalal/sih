import { getAuthToken, getBackendBaseUrl } from './ApiClient';

export type VisionApiResponse = {
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

export async function diagnoseLeafImage(
  base64Image: string,
  cropName?: string,
  growthStage = 'Vegetative',
): Promise<VisionApiResponse> {
  if (!base64Image || base64Image.trim().length === 0) {
    throw new Error('No image was selected.');
  }

  const baseUrl = await getBackendBaseUrl();
  const token = await getAuthToken();
  const response = await fetch(`${baseUrl}/api/vision-diagnose`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      image_base64: base64Image,
      ...(cropName ? { crop_type: cropName } : {}),
      growth_stage: growthStage,
    }),
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.detail || `Vision API failed with HTTP ${response.status}.`);
  }
  return body;
}
