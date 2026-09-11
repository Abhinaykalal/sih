// AgriSaathi AI Mobile Theme — Soft Light-Green Design System
// Standardized tokens for color palette, outdoor typography, 4–32dp spacing scale, elevation, and badges.

export const theme = {
  colors: {
    // Primary Brand Palette
    primary: '#15803D',
    primaryGreen: '#15803D',
    primaryGreenLight: '#DCFCE7',
    primaryGreenDark: '#14532D',
    
    // Backgrounds & Surfaces
    bgLight: '#F8FAF8',
    bgCard: '#FFFFFF',
    cardBorder: '#E2E8F0',
    borderLight: '#F1F5F9',
    
    // Typography
    textPrimary: '#0F172A',
    darkGreen: '#0F172A',
    textSecondary: '#475569',
    textMuted: '#94A3B8',

    // Accents
    sunYellow: '#F59E0B',
    sunYellowLight: '#FEF3C7',
    aiViolet: '#7C3AED',
    aiVioletLight: '#EDE9FE',
    
    // Safety & Diagnostics
    danger: '#DC2626',
    dangerLight: '#FEE2E2',
    warning: '#D97706',
    warningLight: '#FEF3C7',
    info: '#0284C7',
    infoLight: '#E0F2FE',
    
    // Badge Backgrounds
    badgeBgGreen: '#DCFCE7',
    badgeBgViolet: '#EDE9FE',
    badgeBgYellow: '#FEF3C7',
    badgeBgRed: '#FEE2E2',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    base: 16,
    lg: 20,
    xl: 24,
    xxl: 32,
  },
  borderRadius: {
    xs: 6,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    full: 9999,
  },
  shadow: {
    elevation: 2,
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
  },
  typography: {
    title: {
      fontSize: 20,
      fontWeight: '800' as const,
      color: '#0F172A',
    },
    h2: {
      fontSize: 16,
      fontWeight: '700' as const,
      color: '#0F172A',
    },
    h3: {
      fontSize: 14,
      fontWeight: '600' as const,
      color: '#0F172A',
    },
    body: {
      fontSize: 13,
      fontWeight: '400' as const,
      color: '#475569',
    },
    caption: {
      fontSize: 11,
      fontWeight: '500' as const,
      color: '#94A3B8',
    },
  },
};
