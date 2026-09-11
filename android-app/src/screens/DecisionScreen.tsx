import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { theme } from '../styles/theme';
import { ProvenanceBadge } from '../components/ProvenanceBadge';

export function DecisionScreen() {
  const [reEvaluating, setReEvaluating] = useState(false);

  const pipelineStages = [
    {
      title: '1. Inbound Sensor Grounding',
      source: 'LIVE_SENSOR',
      details: [
        'Soil Moisture: 42.5% (Target: 40 - 50%)',
        'Soil / Air Temp: 27.2°C (Optimal)',
        'NPK Nutrient Status: 42 : 18 : 34 mg/kg',
      ],
      icon: '📡',
    },
    {
      title: '2. FAO-56 Evapotranspiration Model',
      source: 'RULE_BASED',
      details: [
        'Crop: Rice (PR-126) • Stage: Vegetative',
        'Crop Coefficient (Kc): 1.05',
        'Daily ET0: 4.1 mm/day • Depletion: 1.8 mm',
      ],
      icon: '📐',
    },
    {
      title: '3. Safety & Weather Interlock',
      source: 'LIVE_WEATHER',
      details: [
        'Precipitation Forecast: 12.0 mm',
        'Rainfall Probability: 85% (Safety Threshold: 50%)',
        'Safety Lockout: Automatic Interlock Engaged',
      ],
      icon: '🌧️',
    },
    {
      title: '4. Multi-Agent Decision Advisory',
      source: 'SOURCE_BACKED_KNOWLEDGE',
      details: [
        'Action: HOLD IRRIGATION PUMP (STANDBY)',
        'Reason: Impending rainfall will replenish root zone.',
        'Grounding: ICAR Package of Practices for Kharif Rice',
      ],
      icon: '🛡️',
    },
  ];

  const handleReEvaluate = () => {
    setReEvaluating(true);
    setTimeout(() => {
      setReEvaluating(false);
    }, 600);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer} showsVerticalScrollIndicator={false}>
      {/* Header */}
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.screenTitle}>Decision Intelligence Engine</Text>
          <Text style={styles.screenSub}>Multi-agent reasoning with verifiable telemetry grounding</Text>
        </View>
        <ProvenanceBadge source="RULE_BASED" label="HYBRID AI" />
      </View>

      {/* Summary Decision Banner */}
      <View style={styles.decisionBanner}>
        <View style={styles.decisionBannerHeader}>
          <Text style={{ fontSize: 26 }}>🛑</Text>
          <View style={{ flex: 1, marginLeft: 12 }}>
            <Text style={styles.decisionLabel}>PRIMARY DETERMINATION</Text>
            <Text style={styles.decisionValue}>HOLD PUMP (DO NOT IRRIGATE)</Text>
          </View>
          <ProvenanceBadge source="RULE_BASED" size="small" />
        </View>
        <Text style={styles.decisionExplanation}>
          Soil moisture is currently at 42.5% (adequate), and an 85% rain probability (12.0 mm) will provide natural root-zone hydration. Pump activation is held to prevent waterlogging.
        </Text>
      </View>

      {/* Pipeline Stage Cards */}
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.sectionHeader}>Verification & Inference Pipeline</Text>
        <TouchableOpacity onPress={handleReEvaluate} disabled={reEvaluating}>
          <Text style={styles.reEvalText}>{reEvaluating ? 'Evaluating...' : 'Re-Evaluate ↻'}</Text>
        </TouchableOpacity>
      </View>

      {pipelineStages.map((stage, idx) => (
        <View key={idx} style={styles.stageCard}>
          <View style={styles.stageHeader}>
            <Text style={styles.stageIcon}>{stage.icon}</Text>
            <View style={{ flex: 1, marginLeft: 10 }}>
              <Text style={styles.stageTitle}>{stage.title}</Text>
            </View>
            <ProvenanceBadge source={stage.source} size="small" />
          </View>

          <View style={styles.detailsBox}>
            {stage.details.map((detail, dIdx) => (
              <View key={dIdx} style={styles.detailRow}>
                <Text style={styles.bulletDot}>•</Text>
                <Text style={styles.detailText}>{detail}</Text>
              </View>
            ))}
          </View>
        </View>
      ))}

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
  decisionBanner: {
    backgroundColor: '#EFF6FF',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  decisionBannerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  decisionLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: '#1E40AF',
    letterSpacing: 0.5,
  },
  decisionValue: {
    fontSize: 15,
    fontWeight: '800',
    color: '#1E3A8A',
  },
  decisionExplanation: {
    fontSize: 12,
    color: '#1E3A8A',
    lineHeight: 18,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  sectionHeader: {
    fontSize: 14,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  reEvalText: {
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.primary,
  },
  stageCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  stageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  stageIcon: {
    fontSize: 20,
  },
  stageTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: theme.colors.textPrimary,
  },
  detailsBox: {
    backgroundColor: '#F8FAFC',
    borderRadius: 8,
    padding: 10,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 4,
  },
  bulletDot: {
    fontSize: 12,
    color: theme.colors.primary,
    marginRight: 6,
  },
  detailText: {
    fontSize: 12,
    color: '#475569',
    flex: 1,
  },
});
