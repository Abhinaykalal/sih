import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop, Line, Circle } from 'react-native-svg';
import { theme } from '../styles/theme';
import { ApiClient } from '../services/ApiClient';
import { ProvenanceBadge } from '../components/ProvenanceBadge';
import { getFarmContextSync } from '../services/FarmContext';

const SCREEN_WIDTH = Dimensions.get('window').width - 32;

export function TelemetryScreen() {
  const [timeRange, setTimeRange] = useState<'1D' | '7D' | '30D'>('1D');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    loadTelemetry();
  }, [timeRange]);

  const loadTelemetry = async () => {
    setLoading(true);
    try {
      const deviceId = getFarmContextSync().primary_device_id || 'ESP32_NODE_01';
      const res = await ApiClient.sensor.getTelemetry(deviceId, 20);
      if (res && res.history && Array.isArray(res.history)) {
        setHistory([...res.history].reverse());
      } else {
        setHistory([]);
      }
    } catch (e: any) {
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  // Build SVG Path for moisture line
  const chartHeight = 130;
  const chartWidth = SCREEN_WIDTH - 32;
  const points = history.map((item, index) => {
    const x = (index / (Math.max(history.length - 1, 1))) * chartWidth;
    const val = item.soil_moisture_pct !== null && item.soil_moisture_pct !== undefined ? item.soil_moisture_pct : 40;
    // Map 30% - 60% moisture to chart height
    const normalized = Math.max(0, Math.min(1, (val - 30) / 30));
    const y = chartHeight - normalized * (chartHeight - 20) - 10;
    return { x, y, val };
  });

  const pathD = points.reduce((acc, curr, idx) => {
    return idx === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`;
  }, '');

  const areaD = points.length > 0
    ? `${pathD} L ${points[points.length - 1].x} ${chartHeight} L ${points[0].x} ${chartHeight} Z`
    : '';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer} showsVerticalScrollIndicator={false}>
      {/* Header */}
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.screenTitle}>Telemetry Trends & History</Text>
          <Text style={styles.screenSub}>Continuous time-series telemetry charts</Text>
        </View>
        <ProvenanceBadge source="HISTORICAL_DATABASE" label="TIME-SERIES" />
      </View>

      {/* Time Range Chips */}
      <View style={styles.filterRow}>
        {(['1D', '7D', '30D'] as const).map((range) => (
          <TouchableOpacity
            key={range}
            style={[styles.filterChip, timeRange === range && styles.filterChipActive]}
            onPress={() => setTimeRange(range)}
          >
            <Text style={[styles.filterChipText, timeRange === range && styles.filterChipTextActive]}>
              {range}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Chart Card */}
      <View style={styles.chartCard}>
        <View style={styles.chartHeader}>
          <View>
            <Text style={styles.chartTitle}>Soil Moisture Dynamics (%)</Text>
            <Text style={styles.chartLegend}>Agronomic Target: 40 - 50%</Text>
          </View>
          <ProvenanceBadge source="LIVE_SENSOR" size="small" />
        </View>

        {loading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="small" color={theme.colors.primary} />
          </View>
        ) : history.length === 0 ? (
          <View style={{ padding: 28, alignItems: 'center', justifyContent: 'center' }}>
            <Text style={{ fontSize: 13, color: '#64748B' }}>Awaiting time-series telemetry packets from node.</Text>
          </View>
        ) : (
          <View style={styles.svgContainer}>
            <Svg height={chartHeight} width={chartWidth}>
              <Defs>
                <LinearGradient id="moistureGradient" x1="0" y1="0" x2="0" y2="1">
                  <Stop offset="0" stopColor="#22C55E" stopOpacity="0.3" />
                  <Stop offset="1" stopColor="#22C55E" stopOpacity="0.0" />
                </LinearGradient>
              </Defs>

              {/* Target band guide lines */}
              <Line x1="0" y1="40" x2={chartWidth} y2="40" stroke="#CBD5E1" strokeDasharray="4, 4" strokeWidth="1" />
              <Line x1="0" y1="80" x2={chartWidth} y2="80" stroke="#CBD5E1" strokeDasharray="4, 4" strokeWidth="1" />

              {/* Area Fill */}
              {areaD ? <Path d={areaD} fill="url(#moistureGradient)" /> : null}

              {/* Moisture Line */}
              {pathD ? <Path d={pathD} fill="none" stroke="#16A34A" strokeWidth="3" /> : null}

              {/* Points */}
              {points.map((pt, pIdx) => (
                <Circle key={pIdx} cx={pt.x} cy={pt.y} r="4" fill="#15803D" stroke="#FFFFFF" strokeWidth="2" />
              ))}
            </Svg>

            {/* Time Labels */}
            <View style={styles.timeLabelRow}>
              {history.map((h, i) => (
                <Text key={i} style={styles.timeLabelText}>
                  {h.received_at || `${i * 4}h`}
                </Text>
              ))}
            </View>
          </View>
        )}
      </View>

      {/* Raw Telemetry Records Table */}
      <View style={styles.tableCard}>
        <Text style={styles.tableTitle}>Inbound Uplink Packets</Text>
        <Text style={styles.tableSub}>Last 20 verified MQTT telemetry records</Text>

        <View style={styles.tableHeaderRow}>
          <Text style={[styles.colHeader, { flex: 1.2 }]}>Time</Text>
          <Text style={[styles.colHeader, { flex: 1 }]}>Moist</Text>
          <Text style={[styles.colHeader, { flex: 1 }]}>Temp</Text>
          <Text style={[styles.colHeader, { flex: 1 }]}>Humid</Text>
          <Text style={[styles.colHeader, { flex: 1.5 }]}>Source</Text>
        </View>

        {history.map((record, idx) => (
          <View key={idx} style={styles.tableRow}>
            <Text style={[styles.tableCell, { flex: 1.2 }]}>{record.received_at || '14:00'}</Text>
            <Text style={[styles.tableCellBold, { flex: 1 }]}>
              {record.soil_moisture_pct != null ? `${record.soil_moisture_pct}%` : 'N/A'}
            </Text>
            <Text style={[styles.tableCell, { flex: 1 }]}>
              {record.temperature_c != null ? `${record.temperature_c}°C` : 'N/A'}
            </Text>
            <Text style={[styles.tableCell, { flex: 1 }]}>
              {record.humidity_pct != null ? `${record.humidity_pct}%` : 'N/A'}
            </Text>
            <View style={{ flex: 1.5 }}>
              <ProvenanceBadge source={record.provenance || record.data_source || 'SIMULATED'} size="small" />
            </View>
          </View>
        ))}
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
    paddingBottom: 110,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  screenTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: theme.colors.textPrimary,
  },
  screenSub: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  filterRow: {
    flexDirection: 'row',
    marginBottom: 14,
  },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    marginRight: 8,
  },
  filterChipActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary,
  },
  filterChipText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#64748B',
  },
  filterChipTextActive: {
    color: '#FFFFFF',
  },
  chartCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  chartHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  chartTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  chartLegend: {
    fontSize: 11,
    color: '#64748B',
    marginTop: 2,
  },
  loadingBox: {
    height: 130,
    alignItems: 'center',
    justifyContent: 'center',
  },
  svgContainer: {
    alignItems: 'center',
  },
  timeLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    marginTop: 6,
  },
  timeLabelText: {
    fontSize: 10,
    color: '#94A3B8',
  },
  tableCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  tableTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  tableSub: {
    fontSize: 11,
    color: theme.colors.textSecondary,
    marginTop: 2,
    marginBottom: 12,
  },
  tableHeaderRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
    paddingBottom: 6,
    marginBottom: 6,
  },
  colHeader: {
    fontSize: 10,
    fontWeight: '800',
    color: '#64748B',
  },
  tableRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F8FAFC',
  },
  tableCell: {
    fontSize: 11,
    color: '#475569',
  },
  tableCellBold: {
    fontSize: 11,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
});
