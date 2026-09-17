import React from 'react';
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



import { ProvenanceBadge } from '../components/ProvenanceBadge';

import { useNavigation } from '@react-navigation/native';
import { useFarmTelemetry } from '../hooks/useFarmTelemetry';

export function SensorScreen() {
  const navigation = useNavigation();
  const {
    farmProfile,
    selectedZone,
    setSelectedZone,
    telemetry,
    weatherData,
    pumpStatus,
    loading,
    refreshing,
    isOffline,
    lastSyncTime,
    liveAlerts,
    refresh,
  } = useFarmTelemetry();

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
        <RefreshControl refreshing={refreshing} onRefresh={refresh} colors={[theme.colors.primary]} />
      }
    >
      {/* 1. Farm & Zone Selector (Horizontal Scroll with no clipping) */}
      <View style={styles.farmHeader}>
        <View>
          <Text style={styles.farmTitle}>{farmProfile.farm_name || 'AgriSaathi Farm'}</Text>
          <Text style={styles.farmSubtitle}>{farmProfile.location_name || 'Connect to backend to load farm info'}</Text>
        </View>
        <ProvenanceBadge source={telemetry?.provenance || 'LIVE_SENSOR'} />
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.zoneScroll} contentContainerStyle={styles.zoneScrollContent}>
        {(farmProfile.zones.length > 0 ? farmProfile.zones.map(z => z.name) : ['All Zones']).map((zone) => (
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

      {/* AI Chatbot Assistant Dashboard Banner */}
      <TouchableOpacity
        style={styles.aiChatBanner}
        onPress={() => navigation.navigate('Chat' as never)}
        activeOpacity={0.85}
      >
        <View style={styles.aiChatIconContainer}>
          <Text style={styles.aiChatIconEmoji}>ðŸ¤–</Text>
        </View>
        <View style={{ flex: 1, marginLeft: 12 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text style={styles.aiChatTitle}>Ask AgriSaathi AI</Text>
            <View style={styles.aiChatBadge}>
              <Text style={styles.aiChatBadgeText}>24/7 ADVISOR</Text>
            </View>
          </View>
          <Text style={styles.aiChatSub}>
            Ask questions about soil NPK, crop diseases, fertilizer, or irrigation
          </Text>
        </View>
        <View style={styles.aiChatArrowBtn}>
          <Text style={styles.aiChatArrowText}>ðŸ’¬</Text>
        </View>
      </TouchableOpacity>

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
          onPress={() => navigation.navigate('Pump' as never)}
        >
          <Text style={styles.actionBtnTextSecondary}>Manage Pump & Automation Rules âž”</Text>
        </TouchableOpacity>
      </View>

      {/* 4. Device Connectivity & Hardware Freshness */}
      <View style={styles.deviceStatusCard}>
        <View style={styles.deviceStatusRow}>
          <View style={styles.statusDotGreen} />
          <Text style={styles.deviceStatusTitle}>ESP32 Node 01 â€¢ Online</Text>
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
              ? 'LOW â€” Irrigation Needed'
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
            {telemetry?.temperature_c != null ? `${telemetry.temperature_c.toFixed(1)}Â°C` : 'Unavailable'}
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
          <TouchableOpacity onPress={() => navigation.navigate('Alerts' as never)}>
            <Text style={styles.viewAllText}>View All</Text>
          </TouchableOpacity>
        </View>

        {liveAlerts.length > 0 ? (
          liveAlerts.map((alert: any, idx: number) => (
            <View key={alert.id || idx} style={[styles.alertItem, idx > 0 && { marginTop: 8 }]}>
              <View style={styles.alertDotAmber} />
              <View style={{ flex: 1, marginLeft: 8 }}>
                <Text style={styles.alertItemTitle}>{alert.title || 'Alert'}</Text>
                <Text style={styles.alertItemSub}>{alert.message || ''}</Text>
              </View>
              <ProvenanceBadge source={alert.provenance || 'RULE_BASED'} size="small" />
            </View>
          ))
        ) : (
          <View style={styles.alertItem}>
            <View style={[styles.alertDotAmber, { backgroundColor: '#22C55E' }]} />
            <View style={{ flex: 1, marginLeft: 8 }}>
              <Text style={styles.alertItemTitle}>No active alerts</Text>
              <Text style={styles.alertItemSub}>All systems operating normally.</Text>
            </View>
          </View>
        )}
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
          onPress={() => navigation.navigate('CropRecommendation' as never)}
        >
          <View style={[styles.quickActionIcon, { backgroundColor: '#DCFCE7' }]}>
            <Text style={styles.quickActionIconText}>AI</Text>
          </View>
          <Text style={styles.quickActionTitle}>Crop AI</Text>
          <Text style={styles.quickActionSub}>Match 22 crops</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionCard}
          onPress={() => navigation.navigate('Vision' as never)}
        >
          <View style={[styles.quickActionIcon, { backgroundColor: '#FEF3C7' }]}>
            <Text style={styles.quickActionIconText}>IMG</Text>
          </View>
          <Text style={styles.quickActionTitle}>Leaf Vision</Text>
          <Text style={styles.quickActionSub}>Scan leaf disease</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionCard}
          onPress={() => navigation.navigate('Decision' as never)}
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
  aiChatBanner: {
    backgroundColor: '#F0FDF4',
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#BBF7D0',
    shadowColor: '#16A34A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  aiChatIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#DCFCE7',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#86EFAC',
  },
  aiChatIconEmoji: {
    fontSize: 22,
  },
  aiChatTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#15803D',
  },
  aiChatBadge: {
    backgroundColor: '#16A34A',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  aiChatBadgeText: {
    color: '#FFFFFF',
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  aiChatSub: {
    fontSize: 11,
    color: '#4B5563',
    marginTop: 2,
    lineHeight: 15,
  },
  aiChatArrowBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#DCFCE7',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  aiChatArrowText: {
    fontSize: 16,
    color: '#15803D',
  },
});
