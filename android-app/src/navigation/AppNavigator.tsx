import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SensorScreen } from '../screens/SensorScreen';
import { PumpControlScreen } from '../screens/PumpControlScreen';
import { VisionScreen } from '../screens/VisionScreen';
import { DecisionScreen } from '../screens/DecisionScreen';
import { ChatScreen } from '../screens/ChatScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { CropRecommendationScreen } from '../screens/CropRecommendationScreen';
import { TelemetryScreen } from '../screens/TelemetryScreen';
import { AlertsScreen } from '../screens/AlertsScreen';
import { theme } from '../styles/theme';

export type RootStackParamList = {
  MainTabs: undefined;
  Chat: undefined;
  Settings: undefined;
  CropRecommendation: undefined;
  Telemetry: undefined;
  Alerts: undefined;
  Decision: undefined;
};

export type MainTabParamList = {
  Sensors: undefined;
  Pump: undefined;
  Vision: undefined;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Tab = createBottomTabNavigator<any>();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Stack = createNativeStackNavigator<any>();

function MainTabs() {
  return (
    <Tab.Navigator
      id="MainTabs"
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: '#94A3B8',
        tabBarStyle: {
          borderTopWidth: 1,
          borderTopColor: '#E2E8F0',
          backgroundColor: '#FFFFFF',
        },
      }}
    >
      <Tab.Screen
        name="Sensors"
        component={SensorScreen}
        options={{ tabBarLabel: 'Sensors' }}
      />
      <Tab.Screen
        name="Pump"
        component={PumpControlScreen}
        options={{ tabBarLabel: 'Control' }}
      />
      <Tab.Screen
        name="Vision"
        component={VisionScreen}
        options={{ tabBarLabel: 'Vision' }}
      />
    </Tab.Navigator>
  );
}

export function AppNavigator() {
  return (
    <Stack.Navigator id="RootStack" screenOptions={{ headerShown: false }}>
      <Stack.Screen name="MainTabs" component={MainTabs} />
      <Stack.Screen name="Chat" component={ChatScreen} />
      <Stack.Screen name="Decision" component={DecisionScreen} />
      <Stack.Screen name="Settings" component={SettingsScreen} />
      <Stack.Screen name="CropRecommendation" component={CropRecommendationScreen} />
      <Stack.Screen name="Telemetry" component={TelemetryScreen} />
      <Stack.Screen name="Alerts" component={AlertsScreen} />
    </Stack.Navigator>
  );
}
