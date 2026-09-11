"""
AgriSaathi Vision Pipeline — Rich Foliar Feature Extraction
============================================================
Extracts a comprehensive feature vector from plant leaf images for disease classification.

Feature Groups (50+ features total):
1. Color Channel Statistics (24 features) — mean, std, skew, kurtosis per R,G,B,H,S,V channel
2. Color Histograms (48 features) — 8-bin histograms per R,G,B,H,S,V channel  
3. Disease Region Ratios (6 features) — green, yellow, brown, dark, bright, white masks
4. Texture Features (8 features) — GLCM-inspired contrast, homogeneity, entropy, edge density
5. Spatial Features (4 features) — center vs edge color difference, symmetry measures

Total: ~90 features per image — sufficient for 27+ class discrimination with ensemble classifiers.

Dependencies: PIL, numpy (already installed)
"""

import io
import numpy as np
from PIL import Image
from typing import Dict, Any, List


def _channel_statistics(channel: np.ndarray) -> List[float]:
    """Compute mean, std, skewness, kurtosis for a single channel."""
    mean = float(np.mean(channel))
    std = float(np.std(channel))
    
    if std < 1e-8:
        skew = 0.0
        kurt = 0.0
    else:
        centered = channel - mean
        skew = float(np.mean(centered ** 3) / (std ** 3))
        kurt = float(np.mean(centered ** 4) / (std ** 4) - 3.0)
    
    return [mean, std, skew, kurt]


def _histogram_features(channel: np.ndarray, bins: int = 8) -> List[float]:
    """Compute normalized histogram for a channel."""
    hist, _ = np.histogram(channel, bins=bins, range=(0.0, 1.0))
    total = hist.sum()
    if total > 0:
        hist = hist.astype(np.float64) / total
    return hist.tolist()


def _rgb_to_hsv_array(rgb_arr: np.ndarray) -> np.ndarray:
    """Convert RGB float array [0,1] to HSV float array [0,1]."""
    r, g, b = rgb_arr[:, :, 0], rgb_arr[:, :, 1], rgb_arr[:, :, 2]
    
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc
    
    # Value
    v = maxc
    
    # Saturation
    s = np.where(maxc > 1e-8, delta / maxc, 0.0)
    
    # Hue
    h = np.zeros_like(maxc)
    mask_delta = delta > 1e-8
    
    mask_r = mask_delta & (maxc == r)
    mask_g = mask_delta & (maxc == g) & ~mask_r
    mask_b = mask_delta & ~mask_r & ~mask_g
    
    h[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6.0
    h[mask_g] = ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2.0
    h[mask_b] = ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4.0
    
    h = h / 6.0  # Normalize to [0, 1]
    h = np.clip(h, 0.0, 1.0)
    
    return np.stack([h, s, v], axis=-1)


def _texture_features(gray: np.ndarray) -> List[float]:
    """Compute texture features from grayscale image."""
    features = []
    
    # 1. Overall texture variance
    features.append(float(np.std(gray)))
    
    # 2. Edge density using simple gradient magnitude
    gy = np.abs(np.diff(gray, axis=0))
    gx = np.abs(np.diff(gray, axis=1))
    edge_density_y = float(np.mean(gy))
    edge_density_x = float(np.mean(gx))
    features.append(edge_density_y)
    features.append(edge_density_x)
    features.append(float(np.mean(np.sqrt(gy[:, :-1]**2 + gx[:-1, :]**2))))  # gradient magnitude
    
    # 3. Local contrast (difference between neighboring pixels)
    if gray.shape[0] > 1 and gray.shape[1] > 1:
        local_contrast = np.abs(gray[1:, :] - gray[:-1, :])
        features.append(float(np.mean(local_contrast)))
        features.append(float(np.std(local_contrast)))
    else:
        features.extend([0.0, 0.0])
    
    # 4. Entropy approximation (histogram-based)
    hist, _ = np.histogram(gray, bins=32, range=(0.0, 1.0))
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total > 0:
        hist = hist / total
        nonzero = hist[hist > 0]
        entropy = -float(np.sum(nonzero * np.log2(nonzero)))
    else:
        entropy = 0.0
    features.append(entropy)
    
    # 5. Uniformity (energy)
    if total > 0:
        uniformity = float(np.sum(hist ** 2))
    else:
        uniformity = 0.0
    features.append(uniformity)
    
    return features


def _spatial_features(arr: np.ndarray) -> List[float]:
    """Compute spatial distribution features."""
    h, w = arr.shape[:2]
    features = []
    
    gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    
    # Center vs periphery brightness
    ch, cw = h // 4, w // 4
    center = gray[ch:h-ch, cw:w-cw]
    center_mean = float(np.mean(center)) if center.size > 0 else 0.5
    overall_mean = float(np.mean(gray))
    features.append(center_mean - overall_mean)  # Center-periphery difference
    
    # Top-bottom asymmetry
    top_half = float(np.mean(gray[:h//2, :]))
    bot_half = float(np.mean(gray[h//2:, :]))
    features.append(top_half - bot_half)
    
    # Left-right asymmetry
    left_half = float(np.mean(gray[:, :w//2]))
    right_half = float(np.mean(gray[:, w//2:]))
    features.append(left_half - right_half)
    
    # Radial intensity gradient
    cy, cx = h // 2, w // 2
    y_coords, x_coords = np.mgrid[:h, :w]
    dist = np.sqrt((y_coords - cy) ** 2 + (x_coords - cx) ** 2)
    max_dist = np.sqrt(cy ** 2 + cx ** 2)
    if max_dist > 0:
        norm_dist = dist / max_dist
        inner = gray[norm_dist < 0.4]
        outer = gray[norm_dist > 0.6]
        inner_mean = float(np.mean(inner)) if inner.size > 0 else 0.5
        outer_mean = float(np.mean(outer)) if outer.size > 0 else 0.5
        features.append(inner_mean - outer_mean)
    else:
        features.append(0.0)
    
    return features


def _disease_region_ratios(arr: np.ndarray) -> List[float]:
    """Compute color-based disease region masks."""
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    
    # Green regions (healthy chlorophyll)
    green_mask = (g > r * 1.05) & (g > b * 1.05) & (g > 0.20)
    greenness = float(np.mean(green_mask))
    
    # Yellow regions (chlorosis / nitrogen deficiency / drought)
    yellow_mask = (r > 0.40) & (g > 0.40) & (b < 0.35) & (np.abs(r - g) < 0.25)
    yellowing = float(np.mean(yellow_mask))
    
    # Brown regions (necrotic fungal spots & lesions)
    brown_mask = (r > b * 1.2) & (g > b) & (r < 0.65) & (g < 0.55) & (r > 0.15)
    browning = float(np.mean(brown_mask))
    
    # Dark regions (severe damage, mold)
    dark_mask = (r < 0.15) & (g < 0.15) & (b < 0.15)
    dark_ratio = float(np.mean(dark_mask))
    
    # Very bright / white regions (powdery mildew, mineral deposits)
    bright_mask = (r > 0.85) & (g > 0.85) & (b > 0.85)
    bright_ratio = float(np.mean(bright_mask))
    
    # Reddish-purple regions (anthocyanin, phosphorus deficiency)
    purple_mask = (r > 0.25) & (b > 0.20) & (g < r * 0.8) & (g < b * 0.9)
    purple_ratio = float(np.mean(purple_mask))
    
    return [greenness, yellowing, browning, dark_ratio, bright_ratio, purple_ratio]


def extract_features_from_image_bytes(image_bytes: bytes) -> Dict[str, float]:
    """
    Extracts a rich feature vector from leaf photo bytes.
    
    Returns dict with 4 original features for backward compatibility,
    plus a 'feature_vector' key with the full 90-feature vector.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((160, 160))
        arr = np.array(img, dtype=np.float32) / 255.0
        
        features = []
        
        # === 1. RGB Channel Statistics (12 features) ===
        for c in range(3):
            features.extend(_channel_statistics(arr[:, :, c]))
        
        # === 2. HSV Channel Statistics (12 features) ===
        hsv = _rgb_to_hsv_array(arr)
        for c in range(3):
            features.extend(_channel_statistics(hsv[:, :, c]))
        
        # === 3. RGB Histograms (24 features) ===
        for c in range(3):
            features.extend(_histogram_features(arr[:, :, c], bins=8))
        
        # === 4. HSV Histograms (24 features) ===
        for c in range(3):
            features.extend(_histogram_features(hsv[:, :, c], bins=8))
        
        # === 5. Disease Region Ratios (6 features) ===
        region_ratios = _disease_region_ratios(arr)
        features.extend(region_ratios)
        
        # === 6. Texture Features (8 features) ===
        gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        features.extend(_texture_features(gray))
        
        # === 7. Spatial Features (4 features) ===
        features.extend(_spatial_features(arr))
        
        # Backward compatibility: return original 4 keys + full vector
        return {
            "greenness": round(region_ratios[0], 4),
            "yellowing": round(region_ratios[1], 4),
            "browning": round(region_ratios[2], 4),
            "texture": round(float(np.std(gray) * 2.5), 4),
            "feature_vector": features
        }
        
    except Exception as e:
        # Return zeros for all features on error
        n_features = 90  # 12+12+24+24+6+8+4
        return {
            "greenness": 0.0,
            "yellowing": 0.0,
            "browning": 0.0,
            "texture": 0.0,
            "feature_vector": [0.0] * n_features
        }


def get_feature_names() -> List[str]:
    """Returns ordered list of feature names matching feature_vector indices."""
    names = []
    
    for ch in ["R", "G", "B"]:
        for stat in ["mean", "std", "skew", "kurtosis"]:
            names.append(f"{ch}_{stat}")
    
    for ch in ["H", "S", "V"]:
        for stat in ["mean", "std", "skew", "kurtosis"]:
            names.append(f"{ch}_{stat}")
    
    for ch in ["R", "G", "B"]:
        for i in range(8):
            names.append(f"{ch}_hist_bin{i}")
    
    for ch in ["H", "S", "V"]:
        for i in range(8):
            names.append(f"{ch}_hist_bin{i}")
    
    names.extend(["green_ratio", "yellow_ratio", "brown_ratio", "dark_ratio", "bright_ratio", "purple_ratio"])
    names.extend(["texture_std", "edge_y", "edge_x", "gradient_mag", "local_contrast_mean", "local_contrast_std", "entropy", "uniformity"])
    names.extend(["center_periphery_diff", "top_bottom_asym", "left_right_asym", "radial_gradient"])
    
    return names
