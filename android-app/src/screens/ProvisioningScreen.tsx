import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  SafeAreaView
} from 'react-native';
import { ApiClient } from '../services/ApiClient';

export function ProvisioningScreen() {
  const [deviceId, setDeviceId] = useState('ESP32-002');
  const [deviceName, setDeviceName] = useState('Field 2 Sensor Node');
  const [farmId, setFarmId] = useState('farm-punjab-01');
  const [fieldId, setFieldId] = useState('field-rice-02');
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleRegister = async () => {
    setLoading(true);
    setStatusMessage(null);

    try {
      const res = await ApiClient.device.registerDevice({
        deviceId,
        deviceName,
        farmId,
        fieldId,
        firmwareVersion: 'v1.4.2',
        communicationType: 'MQTT/Wi-Fi'
      });

      if (res && res.status === 'success') {
        setStatusMessage(`✅ Device ${deviceId} provisioned and assigned to ${fieldId}!`);
      } else {
        setStatusMessage('⚠️ Device provisioning completed with warning.');
      }
    } catch (err: any) {
      setStatusMessage(`❌ Provisioning error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>📡 ESP32 Device Provisioning</Text>
        <Text style={styles.subtitle}>
          Scan and configure new ESP32 sensor nodes over Bluetooth/Wi-Fi and link them to your field.
        </Text>

        <View style={styles.scanBox}>
          <Text style={styles.scanIcon}>🔍</Text>
          <Text style={styles.scanText}>Scanning for nearby BLE / Wi-Fi ESP32 nodes...</Text>
          <Text style={styles.scanSub}>Found: ESP32-002 (Signal -62 dBm)</Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.label}>Device Unique Identifier (MAC/ID):</Text>
          <TextInput
            style={styles.input}
            value={deviceId}
            onChangeText={setDeviceId}
            placeholder="e.g. ESP32-002"
          />

          <Text style={styles.label}>Device Display Name:</Text>
          <TextInput
            style={styles.input}
            value={deviceName}
            onChangeText={setDeviceName}
            placeholder="e.g. Rice Field Sensor Node 2"
          />

          <Text style={styles.label}>Assigned Farm ID:</Text>
          <TextInput
            style={styles.input}
            value={farmId}
            onChangeText={setFarmId}
            placeholder="e.g. farm-punjab-01"
          />

          <Text style={styles.label}>Assigned Field ID:</Text>
          <TextInput
            style={styles.input}
            value={fieldId}
            onChangeText={setFieldId}
            placeholder="e.g. field-rice-02"
          />

          <TouchableOpacity style={styles.registerBtn} onPress={handleRegister} disabled={loading}>
            {loading ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={styles.registerBtnText}>Provision & Register Device ➔</Text>
            )}
          </TouchableOpacity>
        </View>

        {statusMessage && (
          <View style={styles.statusBox}>
            <Text style={styles.statusMsgText}>{statusMessage}</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  content: { padding: 16 },
  title: { fontSize: 20, fontWeight: 'bold', color: '#166534' },
  subtitle: { fontSize: 13, color: '#4B5563', marginVertical: 6 },
  scanBox: { backgroundColor: '#DCFCE7', padding: 16, borderRadius: 12, borderWidth: 1, borderColor: '#86EFAC', marginVertical: 12, alignItems: 'center' },
  scanIcon: { fontSize: 28 },
  scanText: { fontSize: 14, fontWeight: 'bold', color: '#14532D', marginTop: 4 },
  scanSub: { fontSize: 12, color: '#166534', marginTop: 2 },
  formCard: { backgroundColor: '#FFF', padding: 16, borderRadius: 12, borderWidth: 1, borderColor: '#E5E7EB' },
  label: { fontSize: 12, fontWeight: 'bold', color: '#374151', marginTop: 10, marginBottom: 4 },
  input: { height: 44, borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 8, paddingHorizontal: 12, fontSize: 14, backgroundColor: '#F9FAFB' },
  registerBtn: { backgroundColor: '#15803D', height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  registerBtnText: { color: '#FFF', fontSize: 14, fontWeight: 'bold' },
  statusBox: { backgroundColor: '#EFF6FF', padding: 12, borderRadius: 8, marginTop: 12, borderWidth: 1, borderColor: '#BFDBFE' },
  statusMsgText: { color: '#1E40AF', fontSize: 13, fontWeight: '500' }
});
