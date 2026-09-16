import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { theme } from '../styles/theme';
import { getBackendBaseUrl, setBackendBaseUrl } from '../services/ApiClient';
import { OfflineStore } from '../services/OfflineStore';
import { loadFarmContext, getFarmContextSync, FarmProfile, FarmDevice } from '../services/FarmContext';

export function SettingsScreen() {
  const [farmProfile, setFarmProfile] = useState<FarmProfile>(getFarmContextSync());
  const [apiUrl, setApiUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [connStatus, setConnStatus] = useState<string | null>(null);
  const [queuedCount, setQueuedCount] = useState(0);
  const [selectedLang, setSelectedLang] = useState('en');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    const url = await getBackendBaseUrl();
    setApiUrl(url);
    const actions = await OfflineStore.getQueuedActions();
    setQueuedCount(actions.length);
    try {
      const profile = await loadFarmContext();
      setFarmProfile(profile);
    } catch {}
  };

  const handleSaveAndTest = async () => {
    setTesting(true);
    setConnStatus(null);
    try {
      await setBackendBaseUrl(apiUrl);
      const testRes = await fetch(`${apiUrl.trim().replace(/\/+$/, '')}/health`, { method: 'GET' });
      if (testRes.ok) {
        setConnStatus('Connected to AgriSaathi Backend (HTTP 200)');
      } else {
        setConnStatus(`Backend responded with HTTP ${testRes.status}`);
      }
    } catch (e: any) {
      setConnStatus(`Connection error: ${e.message}`);
    } finally {
      setTesting(false);
    }
  };

  const handleSyncOffline = async () => {
    setTesting(true);
    try {
      const res = await OfflineStore.syncOfflineQueue();
      setConnStatus(`Synchronized ${res.synced} offline actions!`);
      const remaining = await OfflineStore.getQueuedActions();
      setQueuedCount(remaining.length);
    } catch (e: any) {
      setConnStatus(`Sync error: ${e.message}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Header */}
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.screenTitle}>Settings & Profile</Text>
          <Text style={styles.screenSub}>Edge connectivity, language & offline sync</Text>
        </View>
      </View>

      {/* Farmer Profile Card */}
      <View style={styles.profileCard}>
        <View style={styles.profileAvatar}>
          <Text style={styles.avatarText}>
            {(farmProfile.owner_name || 'U').substring(0, 2).toUpperCase()}
          </Text>
        </View>
        <View style={{ flex: 1, marginLeft: 14 }}>
          <Text style={styles.profileName}>{farmProfile.owner_name || 'Not configured'}</Text>
          <Text style={styles.profileFarm}>
            {farmProfile.farm_name}{farmProfile.location_name && farmProfile.location_name !== 'Location not configured' ? ` • ${farmProfile.location_name}` : ''}
          </Text>
          <Text style={styles.profileRole}>
            {farmProfile.owner_role || 'Operator'}
            {farmProfile.area_acres ? ` • ${farmProfile.area_acres} Acres` : ''}
          </Text>
        </View>
        <View style={styles.activeTag}>
          <Text style={styles.activeTagText}>{farmProfile.farm_id ? 'CONNECTED' : 'OFFLINE'}</Text>
        </View>
      </View>

      {/* Language Switcher Card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Application Language</Text>
        <Text style={styles.cardSub}>Multilingual translation supported locally</Text>
        <View style={styles.langRow}>
          {[
            { code: 'en', label: 'English' },
            { code: 'hi', label: 'हिंदी (Hindi)' },
            { code: 'pa', label: 'ਪੰਜਾਬੀ (Punjabi)' },
            { code: 'te', label: 'తెలుగు (Telugu)' },
          ].map((l) => (
            <TouchableOpacity
              key={l.code}
              style={[styles.langChip, selectedLang === l.code && styles.langChipActive]}
              onPress={() => setSelectedLang(l.code)}
            >
              <Text style={[styles.langChipText, selectedLang === l.code && styles.langChipTextActive]}>
                {l.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Offline Sync Center */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <View>
            <Text style={styles.cardTitle}>Offline Data Engine</Text>
            <Text style={styles.cardSub}>Local SQLite & AsyncStorage queue</Text>
          </View>
          <View style={styles.queueBadge}>
            <Text style={styles.queueBadgeText}>{queuedCount} Pending</Text>
          </View>
        </View>

        <Text style={styles.syncExplainer}>
          Actions made while in low-connectivity fields are stored with unique client action IDs. When connection resumes, they are idempotently written to the backend with zero duplicates.
        </Text>

        <TouchableOpacity style={styles.syncBtn} onPress={handleSyncOffline} disabled={testing}>
          <Text style={styles.syncBtnText}>🔄 Synchronize Offline Queue</Text>
        </TouchableOpacity>
      </View>

      {/* Backend API Configuration */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Backend Server URL</Text>
        <Text style={styles.cardSub}>Configures FastAPI host IP on local LAN or cloud</Text>

        <TextInput
          style={styles.textInput}
          value={apiUrl}
          onChangeText={setApiUrl}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="http://10.0.2.2:8000"
        />

        <TouchableOpacity style={styles.saveBtn} onPress={handleSaveAndTest} disabled={testing}>
          {testing ? (
            <ActivityIndicator color="#FFFFFF" size="small" />
          ) : (
            <Text style={styles.saveBtnText}>Save & Test Connection</Text>
          )}
        </TouchableOpacity>

        {connStatus && (
          <View style={styles.statusBox}>
            <Text style={styles.statusText}>{connStatus}</Text>
          </View>
        )}
      </View>

      {/* Hardware Nodes Overview */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Connected Hardware Nodes</Text>
        {farmProfile.devices.length > 0 ? (
          farmProfile.devices.map((device: FarmDevice, idx: number) => (
            <View key={device.device_id || idx} style={[styles.nodeItem, idx === farmProfile.devices.length - 1 && { borderBottomWidth: 0 }]}>
              <View style={styles.statusDotGreen} />
              <View style={{ flex: 1, marginLeft: 8 }}>
                <Text style={styles.nodeTitle}>{device.device_name || device.device_id}</Text>
                <Text style={styles.nodeMeta}>
                  {device.firmware_version ? `Firmware ${device.firmware_version}` : 'Firmware N/A'}
                  {device.communication_type ? ` • ${device.communication_type}` : ''}
                </Text>
              </View>
              <Text style={styles.nodeStatusText}>{(device.status || 'UNKNOWN').toUpperCase()}</Text>
            </View>
          ))
        ) : (
          <View style={styles.nodeItem}>
            <View style={[styles.statusDotGreen, { backgroundColor: '#94A3B8' }]} />
            <View style={{ flex: 1, marginLeft: 8 }}>
              <Text style={styles.nodeTitle}>No devices registered</Text>
              <Text style={styles.nodeMeta}>Connect a device or register one via the provisioning screen.</Text>
            </View>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.bgLight,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 36,
  },
  headerRow: {
    marginBottom: 14,
  },
  screenTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: theme.colors.darkGreen,
  },
  screenSub: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  profileCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
    borderWidth: 1,
    borderColor: theme.colors.cardBorder,
    ...theme.shadow,
  },
  profileAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: theme.colors.primaryGreen,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 16,
  },
  profileName: {
    fontSize: 15,
    fontWeight: '800',
    color: theme.colors.darkGreen,
  },
  profileFarm: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 1,
  },
  profileRole: {
    fontSize: 11,
    color: theme.colors.textMuted,
  },
  activeTag: {
    backgroundColor: theme.colors.primaryGreenLight,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  activeTagText: {
    fontSize: 9,
    fontWeight: '800',
    color: theme.colors.primaryGreen,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: theme.borderRadius.lg,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: theme.colors.cardBorder,
    ...theme.shadow,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: theme.colors.darkGreen,
  },
  cardSub: {
    fontSize: 11,
    color: theme.colors.textSecondary,
    marginTop: 2,
    marginBottom: 10,
  },
  langRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 6,
  },
  langChip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 16,
    backgroundColor: '#F7FAF5',
    borderWidth: 1,
    borderColor: theme.colors.cardBorder,
    marginRight: 8,
    marginBottom: 8,
  },
  langChipActive: {
    backgroundColor: theme.colors.primaryGreen,
    borderColor: theme.colors.primaryGreen,
  },
  langChipText: {
    fontSize: 11,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  langChipTextActive: {
    color: '#FFFFFF',
  },
  queueBadge: {
    backgroundColor: theme.colors.primaryGreenLight,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  queueBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: theme.colors.primaryGreen,
  },
  syncExplainer: {
    fontSize: 11,
    color: theme.colors.textSecondary,
    lineHeight: 16,
    marginBottom: 12,
  },
  syncBtn: {
    backgroundColor: '#F0F7EE',
    borderRadius: theme.borderRadius.md,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#D8E8D5',
  },
  syncBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: theme.colors.primaryGreen,
  },
  textInput: {
    backgroundColor: '#F8FAF6',
    borderWidth: 1,
    borderColor: theme.colors.cardBorder,
    borderRadius: theme.borderRadius.md,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 13,
    color: theme.colors.darkGreen,
    marginBottom: 10,
  },
  saveBtn: {
    backgroundColor: theme.colors.primaryGreen,
    borderRadius: theme.borderRadius.md,
    paddingVertical: 11,
    alignItems: 'center',
  },
  saveBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 12,
  },
  statusBox: {
    backgroundColor: '#F4F9F2',
    borderRadius: 8,
    padding: 8,
    marginTop: 10,
  },
  statusText: {
    fontSize: 11,
    color: theme.colors.textSecondary,
    textAlign: 'center',
  },
  nodeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F5EE',
  },
  statusDotGreen: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.primaryGreen,
  },
  nodeTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: theme.colors.darkGreen,
  },
  nodeMeta: {
    fontSize: 10,
    color: theme.colors.textMuted,
    marginTop: 1,
  },
  nodeStatusText: {
    fontSize: 10,
    fontWeight: '800',
    color: theme.colors.primaryGreen,
  },
});
