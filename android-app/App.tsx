import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { theme } from './src/styles/theme';
import { SensorScreen } from './src/screens/SensorScreen';
import { CropRecommendationScreen } from './src/screens/CropRecommendationScreen';
import { VisionScreen } from './src/screens/VisionScreen';
import { AlertsScreen } from './src/screens/AlertsScreen';
import { SettingsScreen } from './src/screens/SettingsScreen';
import { TelemetryScreen } from './src/screens/TelemetryScreen';
import { DecisionScreen } from './src/screens/DecisionScreen';
import { PumpControlScreen } from './src/screens/PumpControlScreen';
import { ChatScreen } from './src/screens/ChatScreen';

export type ScreenType =
  | 'sensors'
  | 'crop'
  | 'vision'
  | 'pump'
  | 'alerts'
  | 'telemetry'
  | 'decision'
  | 'chat'
  | 'settings';

export default function App() {
  const [activeScreen, setActiveScreen] = useState<ScreenType>('sensors');

  const renderScreen = () => {
    switch (activeScreen) {
      case 'sensors':
        return <SensorScreen onNavigate={(screen) => setActiveScreen(screen as ScreenType)} />;
      case 'crop':
        return <CropRecommendationScreen />;
      case 'vision':
        return <VisionScreen />;
      case 'pump':
        return <PumpControlScreen />;
      case 'alerts':
        return <AlertsScreen />;
      case 'telemetry':
        return <TelemetryScreen />;
      case 'decision':
        return <DecisionScreen />;
      case 'chat':
        return <ChatScreen />;
      case 'settings':
        return <SettingsScreen />;
      default:
        return <SensorScreen onNavigate={(screen) => setActiveScreen(screen as ScreenType)} />;
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />

      {/* Top Application Header */}
      <View style={styles.header}>
        <View style={styles.headerTitleRow}>
          <Text style={styles.headerLogo}>🌱</Text>
          <View>
            <Text style={styles.headerTitle}>AgriSaathi AI</Text>
            <Text style={styles.headerSubtitle}>Smart Precision Agriculture • SIH26180</Text>
          </View>
        </View>

        <View style={styles.headerRightActions}>
          <TouchableOpacity
            style={[styles.headerIconBtn, activeScreen === 'chat' && styles.headerIconBtnActive]}
            onPress={() => setActiveScreen('chat')}
          >
            <Text style={styles.headerIconText}>💬</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.headerIconBtn, activeScreen === 'decision' && styles.headerIconBtnActive]}
            onPress={() => setActiveScreen('decision')}
          >
            <Text style={styles.headerIconText}>🧠</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.headerIconBtn, activeScreen === 'settings' && styles.headerIconBtnActive]}
            onPress={() => setActiveScreen('settings')}
          >
            <Text style={styles.headerIconText}>⚙️</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Main Screen Body */}
      <View style={styles.screenContainer}>{renderScreen()}</View>

      {/* Bottom Navigation Bar matching Design Reference */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tabItem, activeScreen === 'sensors' && styles.tabItemActive]}
          onPress={() => setActiveScreen('sensors')}
        >
          <Text style={styles.tabIcon}>📡</Text>
          <Text style={[styles.tabLabel, activeScreen === 'sensors' && styles.tabLabelActive]}>
            Home
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabItem, activeScreen === 'crop' && styles.tabItemActive]}
          onPress={() => setActiveScreen('crop')}
        >
          <Text style={styles.tabIcon}>🌱</Text>
          <Text style={[styles.tabLabel, activeScreen === 'crop' && styles.tabLabelActive]}>
            Crops
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabItem, activeScreen === 'vision' && styles.tabItemActive]}
          onPress={() => setActiveScreen('vision')}
        >
          <Text style={styles.tabIcon}>📷</Text>
          <Text style={[styles.tabLabel, activeScreen === 'vision' && styles.tabLabelActive]}>
            Leaf AI
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabItem, activeScreen === 'pump' && styles.tabItemActive]}
          onPress={() => setActiveScreen('pump')}
        >
          <Text style={styles.tabIcon}>⚡</Text>
          <Text style={[styles.tabLabel, activeScreen === 'pump' && styles.tabLabelActive]}>
            Pump
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabItem, activeScreen === 'alerts' && styles.tabItemActive]}
          onPress={() => setActiveScreen('alerts')}
        >
          <Text style={styles.tabIcon}>🔔</Text>
          <Text style={[styles.tabLabel, activeScreen === 'alerts' && styles.tabLabelActive]}>
            Alerts
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  header: {
    height: 58,
    backgroundColor: '#FFFFFF',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.cardBorder,
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerLogo: {
    fontSize: 24,
    marginRight: 10,
  },
  headerTitle: {
    color: theme.colors.darkGreen,
    fontSize: 17,
    fontWeight: '800',
  },
  headerSubtitle: {
    color: theme.colors.textSecondary,
    fontSize: 10,
    fontWeight: '500',
  },
  headerRightActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerIconBtn: {
    padding: 6,
    marginLeft: 6,
    borderRadius: 8,
    backgroundColor: '#F5FBF1',
  },
  headerIconBtnActive: {
    backgroundColor: theme.colors.primaryGreenLight,
  },
  headerIconText: {
    fontSize: 18,
  },
  screenContainer: {
    flex: 1,
    backgroundColor: theme.colors.bgLight,
  },
  tabBar: {
    height: 62,
    backgroundColor: '#FFFFFF',
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: theme.colors.cardBorder,
    paddingBottom: 4,
  },
  tabItem: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 6,
  },
  tabItemActive: {
    borderTopWidth: 3,
    borderTopColor: theme.colors.primaryGreen,
    backgroundColor: '#F7FCF5',
  },
  tabIcon: {
    fontSize: 18,
  },
  tabLabel: {
    fontSize: 10,
    color: theme.colors.textSecondary,
    marginTop: 2,
    fontWeight: '600',
  },
  tabLabelActive: {
    color: theme.colors.primaryGreen,
    fontWeight: '800',
  },
});
