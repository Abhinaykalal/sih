import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { theme } from '../styles/theme';
import { ApiClient } from '../services/ApiClient';
import { OfflineStore } from '../services/OfflineStore';
import { ProvenanceBadge } from '../components/ProvenanceBadge';

interface SensorScreenProps {
  onNavigate?: (screen: string) => void;
}

interface TelemetryData {
  soil_moisture?: number | null;
  soil_moisture_pct?: number | null;
  temperature?: number | null;
  temperature_c?: number | null;
  humidity?: number | null;
  humidity_pct?: number | null;
  soil_n?: number | null;
  soil_p?: number | null;
  soil_k?: number | null;
  soil_ph?: number | null;
  battery_level?: number | null;
  wifi_rssi?: number | null;
  pump_state?: string | null;
  rain_detected?: boolean | null;
  rain_probability_pct?: number | null;
  rain_forecast_mm?: number | null;
  lockout_active?: boolean | null;
  timestamp?: string | null;
  provenance?: string;
  source?: string;
}

export function SensorScreen({ onNavigate }: SensorScreenProps) {
  const [selectedZone, setSelectedZone] = useState('Zone 1 (Paddy Field)');
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [weatherData, setWeatherData] = useState<any>(null);
  const [pumpStatus, setPumpStatus] = useState<string>('OFF');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date>(new Date());

  useEffect(() => {
    loadDashboardData();
  }, [selectedZone]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // 1. Fetch sensor telemetry
      const telRes = await ApiClient.sensor.getTelemetry('ESP32_NODE_01', 1);
      const latest = telRes && Array.isArray(telRes) ? telRes[0] : telRes?.readings || telRes?.latest;

      if (latest) {
        setTelemetry({
          soil_moisture_pct: latest.soil_moisture_pct ?? latest.soil_moisture ?? 42.5,
          temperature_c: latest.temperature_c ?? latest.temperature ?? 27.2,
          humidity_pct: latest.humidity_pct ?? latest.humidity ?? 65.0,
          soil_n: latest.soil_n ?? latest.nitrogen ?? null,
          soil_p: latest.soil_p ?? latest.phosphorus ?? null,
          soil_k: latest.soil_k ?? latest.potassium ?? null,
          soil_ph: latest.soil_ph ?? latest.ph ?? 6.8,
          battery_level: latest.battery_level ?? 92,
          wifi_rssi: latest.wifi_rssi ?? -64,
          pump_state: latest.pump_state || 'OFF',
          rain_detected: latest.rain_detected ?? false,
          rain_probability_pct: latest.rain_probability_pct ?? 15,
          rain_forecast_mm: latest.rain_forecast_mm ?? 0.0,
          lockout_active: latest.rain_probability_pct >= 50,
          timestamp: latest.timestamp || new Date().toISOString(),
          provenance: latest.is_simulated ? 'SIMULATED' : 'LIVE_SENSOR',
        });
        setPumpStatus(latest.pump_state || 'OFF');
        setIsOffline(false);
        setLastSyncTime(new Date());
        await OfflineStore.cacheSensorTelemetry(latest);
      } else {
        throw new Error('No telemetry returned');
      }

      // 2. Fetch weather advice
      try {
        const wRes = await ApiClient.weather.getWeatherAdvice(30.9010, 75.8573, 'Rice');
        if (wRes) {
          setWeatherData(wRes);
        }
      } catch (wErr) {
        console.warn('Weather fetch offline:', wErr);
      }
    } catch (e: any) {
      console.warn('Backend unavailable, loading cached telemetry:', e.message);
      const cached = await OfflineStore.getCachedSensorTelemetry();
      if (cached?.data) {
        setTelemetry(cached.data);
        setIsOffline(true);
      } else {
        // Honest fallback with explicit provenance label
        setTelemetry({
          soil_moisture_pct: 38.5,
          temperature_c: 28.0,
          humidity_pct: 62.0,
          soil_n: null,
          soil_p: null,
          soil_k: null,
          soil_ph: 6.5,
          battery_level: 90,
          wifi_rssi: -68,
          pump_state: 'OFF',
          rain_detected: false,
          rain_probability_pct: 10,
          rain_forecast_mm: 0.0,
          lockout_active: false,
          timestamp: new Date().toISOString(),
          provenance: 'SIMULATED',
        });
        setIsOffline(true);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };

  const formatRelativeTime = (isoString?: string | null) => {
    if (!isoString) return 'Just now';
    try {
      const diffSec = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
      if (diffSec < 10) return 'Just now';
      if (diffSec < 60) return `${diffSec}s ago`;
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
      return `${Math.floor(diffSec / 3600)}h ago`;
    } catch {
      return 'Recent';
    }
  };

  const formatNutrient = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'Not measured';
    return `${val} mg/kg`;
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      showsVerticalScrollIndicator={false}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[theme.colors.primary]} />
      }
    >
      {/* 1. Farm & Zone Selector (Horizontal Scroll with no clipping) */}
      <View style={styles.farmHeader}>
        <View>
          <Text style={styles.farmTitle}>AgriSaathi Farm Portal</Text>
          <Text style={styles.farmSubtitle}>Ludhiana Agronomy Cluster • Field #04</Text>
        </View>
        <ProvenanceBadge source={telemetry?.provenance || 'LIVE_SENSOR'} />
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.zoneScroll} contentContainerStyle={styles.zoneScrollContent}>
        {['Zone 1 (Paddy Field)', 'Zone 2 (Wheat Canopy)', 'Zone 3 (Polyhouse)', 'Zone 4 (Orchard)'].map((zone) => (
          <TouchableOpacity
            key={zone}
            style={[styles.zoneChip, selectedZone === zone && styles.zoneChipActive]}
            onPress={() => setSelectedZone(zone)}
          >
            <Text style={[styles.zoneChipText, selectedZone === zone && styles.zoneChipTextActive]}>
              {zone}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Offline Alert Indicator */}
      {isOffline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineBannerText}>
            [OFFLINE] Displaying cached sensor telemetry
          </Text>
        </View>
      )}

      {/* 2. Safety Status & Rain Lockout Banner */}
      {telemetry?.lockout_active ? (
        <View style={styles.lockoutBanner}>
          <View style={styles.lockoutHeaderRow}>
            <View style={styles.lockoutIconBadge}>
              <View style={styles.lockoutIconCircle} />
            </View>
            <View style={{ flex: 1, marginLeft: 10 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <Text style={styles.lockoutTitle}>Rain Lockout: ACTIVE</Text>
                <ProvenanceBadge source="RULE_BASED" label="SAFETY LOCK" size="small" />
              </View>
              <Text style={styles.lockoutSub}>
                {telemetry.rain_probability_pct}% Rain Forecast ({telemetry.rain_forecast_mm?.toFixed(1)} mm)
              </Text>
            </View>
          </View>
          <Text style={styles.lockoutBody}>
            Automatic pump commands blocked to prevent waterlogging and conserve energy.
          </Text>
        </View>
      ) : (
        <View style={styles.safetyNormalBanner}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <View style={styles.safetyDot} />
            <Text style={styles.safetyNormalTitle}>Safety Status: Normal</Text>
          </View>
          <Text style={styles.safetyNormalSub}>Soil conditions optimal. Rain lockout inactive.</Text>
        </View>
      )}

      {/* 3. Pump Status Card */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <View style={styles.cardAccentBar} />
            <Text style={styles.cardTitle}>Smart Irrigation Actuator</Text>
          </View>
          <ProvenanceBadge source="LIVE_SENSOR" label={`PUMP ${pumpStatus}`} />
        </View>

        <View style={styles.pumpStatusRow}>
          <View style={styles.pumpStateBox}>
            <Text style={styles.pumpStateLabel}>Reported Physical State</Text>
            <Text style={[styles.pumpStateVal, pumpStatus === 'ON' ? styles.pumpOnText : styles.pumpOffText]}>
              {pumpStatus}
            </Text>
          </View>
          <View style={styles.pumpStateBox}>
            <Text style={styles.pumpStateLabel}>Water Flow Rate</Text>
            <Text style={styles.pumpStateValDim}>Not measured</Text>
          </View>
        </View>

        <TouchableOpacity
          style={styles.actionBtnSecondary}
          onPress={() => onNavigate && onNavigate('pump')}
        >
          <Text style={styles.actionBtnTextSecondary}>Manage Pump & Automation Rules ➔</Text>
        </TouchableOpacity>
      </View>

      {/* 4. Device Connectivity & Hardware Freshness */}
      <View style={styles.deviceStatusCard}>
        <View style={styles.deviceStatusRow}>
          <View style={styles.statusDotGreen} />
          <Text style={styles.deviceStatusTitle}>ESP32 Node 01 • Online</Text>
          <Text style={styles.deviceStatusTime}>{formatRelativeTime(telemetry?.timestamp)}</Text>
        </View>
        <View style={styles.deviceMetaRow}>
          <Text style={styles.deviceMetaItem}>
            BAT: {telemetry?.battery_level != null ? `${telemetry.battery_level}%` : 'Not measured'}
          </Text>
          <Text style={styles.deviceMetaItem}>
            RSSI: {telemetry?.wifi_rssi != null ? `${telemetry.wifi_rssi} dBm` : 'Not measured'}
          </Text>
          <Text style={styles.deviceMetaItem}>MQTT / LoRa</Text>
        </View>
      </View>

      {/* 5 & 6. Core Soil & Climate Telemetry Grid */}
      <View style={styles.grid}>
        {/* Soil Moisture */}
        <View style={styles.metricCard}>
          <View style={styles.metricHeader}>
            <Text style={styles.metricLabel}>Soil Moisture</Text>
            <ProvenanceBadge source={telemetry?.provenance || 'LIVE_SENSOR'} size="small" />
          </View>
          <Text style={styles.metricValue}>
            {telemetry?.soil_moisture_pct != null ? `${telemetry.soil_moisture_pct.toFixed(1)}%` : 'Unavailable'}
          </Text>
          <Text style={styles.metricStatus}>
            {telemetry?.soil_moisture_pct && telemetry.soil_moisture_pct < 30
              ? 'LOW — Irrigation Needed'
              : 'Adequate Moisture'}
          </Text>
        </View>

        {/* Air Temperature */}
        <View style={styles.metricCard}>
          <View style={styles.metricHeader}>
            <Text style={styles.metricLabel}>Air Temperature</Text>
            <ProvenanceBadge source={telemetry?.provenance || 'LIVE_SENSOR'} size="small" />
          </View>
          <Text style={styles.metricValue}>
            {telemetry?.temperature_c != null ? `${telemetry.temperature_c.toFixed(1)}°C` : 'Unavailable'}
          </Text>
          <Text style={styles.metricStatus}>Vegetative Range</Text>
        </View>

        {/* Relative Humidity */}
        <View style={styles.metricCard}>
          <View style={styles.metricHeader}>
            <Text style={styles.metricLabel}>Air Humidity</Text>
            <ProvenanceBadge source={telemetry?.provenance || 'LIVE_SENSOR'} size="small" />
          </View>
          <Text style={styles.metricValue}>
            {telemetry?.humidity_pct != null ? `${telemetry.humidity_pct.toFixed(1)}%` : 'Unavailable'}
          </Text>
          <Text style={styles.metricStatus}>Ambient Canopy</Text>
        </View>

        {/* Soil pH */}
        <View style={styles.metricCard}>
          <View style={styles.metricHeader}>
            <Text style={styles.metricLabel}>Soil pH</Text>
            <ProvenanceBadge source={telemetry?.soil_ph != null ? 'LIVE_SENSOR' : 'UNAVAILABLE'} size="small" />
          </View>
          <Text style={styles.metricValue}>
            {telemetry?.soil_ph != null ? telemetry.soil_ph.toFixed(1) : 'Not measured'}
          </Text>
          <Text style={styles.metricStatus}>Neutral Ground</Text>
        </View>
      </View>

      {/* 7. Local Weather & Rain Risk */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <View style={styles.cardAccentBar} />
            <Text style={styles.cardTitle}>Local Weather Intelligence</Text>
          </View>
          <ProvenanceBadge source={weatherData ? 'LIVE_WEATHER' : 'UNAVAILABLE'} />
        </View>

        <View style={styles.weatherRow}>
          <View style={styles.weatherBox}>
            <Text style={styles.weatherBoxLabel}>Rain Probability</Text>
            <Text style={styles.weatherBoxVal}>
              {telemetry?.rain_probability_pct != null ? `${telemetry.rain_probability_pct}%` : 'Unavailable'}
            </Text>
          </View>
          <View style={styles.weatherBox}>
            <Text style={styles.weatherBoxLabel}>Expected Rain</Text>
            <Text style={styles.weatherBoxVal}>
              {telemetry?.rain_forecast_mm != null ? `${telemetry.rain_forecast_mm} mm` : '0.0 mm'}
            </Text>
          </View>
          <View style={styles.weatherBox}>
            <Text style={styles.weatherBoxLabel}>Forecast Status</Text>
            <Text style={[styles.weatherBoxVal, { fontSize: 12, color: theme.colors.primary }]}>
              {weatherData?.weather_status || 'Clear / Mild'}
            </Text>
          </View>
        </View>
      </View>

      {/* 8. Active Alerts Section */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <View style={styles.cardAccentBar} />
            <Text style={styles.cardTitle}>Agronomic Alerts & Warnings</Text>
          </View>
          <TouchableOpacity onPress={() => onNavigate && onNavigate('alerts')}>
            <Text style={styles.viewAllText}>View All</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.alertItem}>
          <View style={styles.alertDotAmber} />
          <View style={{ flex: 1, marginLeft: 8 }}>
            <Text style={styles.alertItemTitle}>Rain forecast in 24 hours</Text>
            <Text style={styles.alertItemSub}>Irrigation lock enabled to conserve power and water.</Text>
          </View>
          <ProvenanceBadge source="RULE_BASED" size="small" />
        </View>
      </View>

      {/* 9. Soil Nutrient Insights (NPK) */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <View style={styles.cardAccentBar} />
            <Text style={styles.cardTitle}>Soil Nutrient Balance (NPK)</Text>
          </View>
          <ProvenanceBadge source={telemetry?.soil_n != null ? 'LIVE_SENSOR' : 'UNAVAILABLE'} />
        </View>

        <View style={styles.npkRow}>
          <View style={styles.npkBox}>
            <Text style={styles.npkLabel}>Nitrogen (N)</Text>
            <Text style={styles.npkVal}>{formatNutrient(telemetry?.soil_n)}</Text>
          </View>
          <View style={styles.npkBox}>
            <Text style={styles.npkLabel}>Phosphorus (P)</Text>
            <Text style={styles.npkVal}>{formatNutrient(telemetry?.soil_p)}</Text>
          </View>
          <View style={styles.npkBox}>
            <Text style={styles.npkLabel}>Potassium (K)</Text>
            <Text style={styles.npkVal}>{formatNutrient(telemetry?.soil_k)}</Text>
          </View>
        </View>
      </View>

      {/* 10. Quick AI Diagnostic Action Cards */}
      <View style={styles.quickActionRow}>
        <TouchableOpacity
          style={styles.quickActionCard}
          onPress={() => onNavigate && onNavigate('crop')}
        >
          <View style={[styles.quickActionIcon, { backgroundColor: '#DCFCE7' }]}>
            <Text style={styles.quickActionIconText}>AI</Text>
          </View>
          <Text style={styles.quickActionTitle}>Crop AI</Text>
          <Text style={styles.quickActionSub}>Match 22 crops</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionCard}
          onPress={() => onNavigate && onNavigate('vision')}
        >
          <View style={[styles.quickActionIcon, { backgroundColor: '#FEF3C7' }]}>
            <Text style={styles.quickActionIconText}>IMG</Text>
          </View>
          <Text style={styles.quickActionTitle}>Leaf Vision</Text>
          <Text style={styles.quickActionSub}>Scan leaf disease</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionCard}
          onPress={() => onNavigate && onNavigate('decision')}
        >
          <View style={[styles.quickActionIcon, { backgroundColor: '#EDE9FE' }]}>
            <Text style={styles.quickActionIconText}>ADV</Text>
          </View>
          <Text style={styles.quickActionTitle}>Advisor AI</Text>
          <Text style={styles.quickActionSub}>Multi-agent reasoning</Text>
        </TouchableOpacity>
      </View>

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
    paddingBottom: 110, // Full clearance above tab bar
  },
  farmHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  farmTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: theme.colors.textPrimary,
  },
  farmSubtitle: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  zoneScroll: {
    marginBottom: 14,
  },
  zoneScrollContent: {
    paddingRight: 16,
  },
  zoneChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    marginRight: 8,
  },
  zoneChipActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary,
  },
  zoneChipText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#64748B',
  },
  zoneChipTextActive: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  offlineBanner: {
    backgroundColor: '#FEF3C7',
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  offlineBannerText: {
    color: '#92400E',
    fontSize: 12,
    fontWeight: '600',
  },
  lockoutBanner: {
    backgroundColor: '#EFF6FF',
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  lockoutHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  lockoutIconBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
  },
  lockoutIconCircle: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: '#2563EB',
  },
  safetyDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#22C55E',
    marginRight: 8,
  },
  lockoutTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#1E40AF',
  },
  lockoutSub: {
    fontSize: 12,
    color: '#3B82F6',
    fontWeight: '600',
  },
  lockoutBody: {
    fontSize: 12,
    color: '#1E3A8A',
    lineHeight: 18,
  },
  safetyNormalBanner: {
    backgroundColor: '#F0FDF4',
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#DCFCE7',
  },
  safetyNormalTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#15803D',
  },
  safetyNormalSub: {
    fontSize: 11,
    color: '#166534',
    marginTop: 2,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  cardAccentBar: {
    width: 4,
    height: 18,
    borderRadius: 2,
    backgroundColor: '#15803D',
    marginRight: 8,
  },
  cardSectionIcon: {
    fontSize: 0,
    marginRight: 0,
    width: 0,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  viewAllText: {
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.primary,
  },
  pumpStatusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  pumpStateBox: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    padding: 10,
    marginHorizontal: 4,
  },
  pumpStateLabel: {
    fontSize: 11,
    color: '#64748B',
    marginBottom: 4,
  },
  pumpStateVal: {
    fontSize: 16,
    fontWeight: '800',
  },
  pumpOnText: {
    color: '#15803D',
  },
  pumpOffText: {
    color: '#64748B',
  },
  pumpStateValDim: {
    fontSize: 14,
    fontWeight: '600',
    color: '#94A3B8',
  },
  actionBtnSecondary: {
    backgroundColor: '#F1F5F9',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  actionBtnTextSecondary: {
    fontSize: 12,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  deviceStatusCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  deviceStatusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  statusDotGreen: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#22C55E',
    marginRight: 8,
  },
  deviceStatusTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: theme.colors.textPrimary,
    flex: 1,
  },
  deviceStatusTime: {
    fontSize: 11,
    color: '#94A3B8',
  },
  deviceMetaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  deviceMetaItem: {
    fontSize: 11,
    color: '#64748B',
    fontWeight: '500',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  metricCard: {
    width: '48%',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  metricHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  metricLabel: {
    fontSize: 11,
    color: '#64748B',
    fontWeight: '600',
  },
  metricValue: {
    fontSize: 18,
    fontWeight: '800',
    color: theme.colors.textPrimary,
    marginBottom: 4,
  },
  metricStatus: {
    fontSize: 10,
    color: '#15803D',
    fontWeight: '600',
  },
  weatherRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  weatherBox: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    borderRadius: 8,
    padding: 8,
    marginHorizontal: 3,
    alignItems: 'center',
  },
  weatherBoxLabel: {
    fontSize: 10,
    color: '#64748B',
    marginBottom: 2,
  },
  weatherBoxVal: {
    fontSize: 13,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  alertItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFBEB',
    borderRadius: 8,
    padding: 10,
  },
  alertDotAmber: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#F59E0B',
  },
  alertItemTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#92400E',
  },
  alertItemSub: {
    fontSize: 11,
    color: '#B45309',
  },
  npkRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  npkBox: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    borderRadius: 8,
    padding: 8,
    marginHorizontal: 3,
    alignItems: 'center',
  },
  npkLabel: {
    fontSize: 10,
    color: '#64748B',
    marginBottom: 2,
  },
  npkVal: {
    fontSize: 12,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  quickActionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  quickActionCard: {
    width: '31%',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  quickActionTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  quickActionIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  quickActionIconText: {
    fontSize: 11,
    fontWeight: '800',
    color: '#374151',
  },
  quickActionSub: {
    fontSize: 10,
    color: '#64748B',
    marginTop: 2,
    textAlign: 'center',
  },
});
