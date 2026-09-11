import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export type ProvenanceType =
  | 'LIVE_SENSOR'
  | 'LIVE_WEATHER'
  | 'SOURCE_BACKED_KNOWLEDGE'
  | 'HISTORICAL_DATABASE'
  | 'RULE_BASED'
  | 'MODEL_PREDICTION'
  | 'EXPERIMENTAL'
  | 'SIMULATED'
  | 'UNAVAILABLE'
  | 'STALE'
  | string;

interface ProvenanceBadgeProps {
  source?: ProvenanceType;
  label?: string;
  size?: 'small' | 'medium';
}

export function ProvenanceBadge({ source = 'UNAVAILABLE', label, size = 'small' }: ProvenanceBadgeProps) {
  const getBadgeConfig = () => {
    switch (source) {
      case 'LIVE_SENSOR':
        return {
          text: label || 'LIVE SENSOR',
          bg: '#DCFCE7',
          color: '#15803D',
          dot: '#16A34A',
        };
      case 'LIVE_WEATHER':
        return {
          text: label || 'LIVE WEATHER',
          bg: '#E0F2FE',
          color: '#0369A1',
          dot: '#0284C7',
        };
      case 'SOURCE_BACKED_KNOWLEDGE':
        return {
          text: label || 'SOURCE-BACKED',
          bg: '#CCFBF1',
          color: '#0F766E',
          dot: '#14B8A6',
        };
      case 'HISTORICAL_DATABASE':
        return {
          text: label || 'CACHED / DB',
          bg: '#F1F5F9',
          color: '#475569',
          dot: '#64748B',
        };
      case 'RULE_BASED':
        return {
          text: label || 'RULE-BASED',
          bg: '#E0E7FF',
          color: '#4338CA',
          dot: '#6366F1',
        };
      case 'MODEL_PREDICTION':
        return {
          text: label || 'AI PREDICTION',
          bg: '#F5F3FF',
          color: '#6D28D9',
          dot: '#8B5CF6',
        };
      case 'EXPERIMENTAL':
        return {
          text: label || 'EXPERIMENTAL',
          bg: '#FCE7F3',
          color: '#BE185D',
          dot: '#EC4899',
        };
      case 'SIMULATED':
        return {
          text: label || 'SIMULATED DATA',
          bg: '#FEF3C7',
          color: '#B45309',
          dot: '#F59E0B',
        };
      case 'STALE':
        return {
          text: label || 'STALE DATA',
          bg: '#F3F4F6',
          color: '#6B7280',
          dot: '#9CA3AF',
        };
      case 'UNAVAILABLE':
      default:
        return {
          text: label || 'UNAVAILABLE',
          bg: '#FEE2E2',
          color: '#B91C1C',
          dot: '#EF4444',
        };
    }
  };

  const config = getBadgeConfig();
  const isSmall = size === 'small';

  return (
    <View style={[styles.badge, { backgroundColor: config.bg }, isSmall && styles.badgeSmall]}>
      <View style={[styles.dot, { backgroundColor: config.dot }]} />
      <Text style={[styles.text, { color: config.color }, isSmall && styles.textSmall]}>
        {config.text}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  badgeSmall: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 4,
  },
  text: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  textSmall: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
});
