import React, { useState, useRef } from 'react';
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



import { ProvenanceBadge } from '../components/ProvenanceBadge';

export interface CitationItem {
  chunk_id: string;
  title: string;
  source: string;
  section?: string;
  page?: number;
  relevance_score?: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
  provenance?: string;
  modelName?: string;
  modelStatus?: string;
  retrievedChunks?: number;
  citations?: CitationItem[];
  sensorContext?: any;
  weatherContext?: any;
  warnings?: string[];
  isError?: boolean;
}

import { useAdvisoryChat } from '../hooks/useAdvisoryChat';

export function ChatScreen() {
  const {
    messages,
    loading,
    selectedLanguage,
    setSelectedLanguage,
    isOffline,
    modelStatus,
    handleSend: hookHandleSend,
    clearHistory
  } = useAdvisoryChat();

  const [input, setInput] = useState('');
  const scrollViewRef = useRef<ScrollView>(null);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input.trim();
    if (!textToSend) return;
    await hookHandleSend(textToSend);
    if (!queryText) setInput('');
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header Info Bar */}
      <View style={styles.headerBar}>
        <View style={styles.modelTagContainer}>
          <Text style={styles.headerTitle}>AgriSaathi AI Assistant</Text>
          <View style={styles.statusRow}>
            <View style={[styles.statusDot, modelStatus === 'AVAILABLE' ? styles.dotGreen : styles.dotOrange]} />
            <Text style={styles.modelStatusText}>
              Model: qwen2.5:7b-instruct ({modelStatus})
            </Text>
          </View>
        </View>

        {/* Language Switcher */}
        <View style={styles.langSelector}>
          {(['en', 'hi', 'te'] as const).map((lang) => (
            <TouchableOpacity
              key={lang}
              style={[styles.langChip, selectedLanguage === lang && styles.langChipActive]}
              onPress={() => setSelectedLanguage(lang)}
            >
              <Text style={[styles.langText, selectedLanguage === lang && styles.langTextActive]}>
                {lang === 'en' ? 'EN' : lang === 'hi' ? 'Ã Â¤Â¹Ã Â¤Â¿Ã Â¤â€šÃ Â¤Â¦Ã Â¥â‚¬' : 'Ã Â°Â¤Ã Â±â€ Ã Â°Â²Ã Â±ÂÃ Â°â€”Ã Â±Â'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {isOffline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineText}>[OFFLINE] Actions Queued &amp; Using Local Cache</Text>
        </View>
      )}

      {/* Messages Scroll Area */}
      <ScrollView
        ref={scrollViewRef}
        style={styles.chatArea}
        contentContainerStyle={{ padding: 12, paddingBottom: 110 }}
      >
        {messages.map((m) => (
          <View
            key={m.id}
            style={[
              styles.messageBubble,
              m.sender === 'user' ? styles.userBubble : styles.botBubble,
              m.isError && styles.errorBubble
            ]}
          >
            {/* Sender and Provenance Header */}
            {m.sender === 'bot' && (
              <View style={styles.bubbleHeader}>
                <ProvenanceBadge source={m.provenance || 'SOURCE_BACKED_KNOWLEDGE'} size="small" />
                {m.retrievedChunks !== undefined && m.retrievedChunks > 0 && (
                  <Text style={styles.chunksTag}>{m.retrievedChunks} Sources Cited</Text>
                )}
              </View>
            )}

            <Text style={m.sender === 'user' ? styles.userText : styles.botText}>{m.text}</Text>

            {/* Citations Box */}
            {m.citations && m.citations.length > 0 && (
              <View style={styles.citationsContainer}>
                <Text style={styles.citationsHeading}>Verified Extension Citations:</Text>
                {m.citations.map((c, idx) => (
                  <View key={c.chunk_id || idx} style={styles.citationCard}>
                    <Text style={styles.citationTitle}>{c.title}</Text>
                    <Text style={styles.citationSource}>
                      {c.source} {c.section ? `Ã¢â‚¬Â¢ Sec: ${c.section}` : ''} {c.page ? `Ã¢â‚¬Â¢ p.${c.page}` : ''}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {/* Warnings Tag */}
            {m.warnings && m.warnings.length > 0 && (
              <View style={styles.warningBox}>
                {m.warnings.map((w, i) => (
                  <Text key={i} style={styles.warningText}>Note: {w}</Text>
                ))}
              </View>
            )}

            {/* Retry Button if Error */}
            {m.isError && (
              <TouchableOpacity style={styles.retryBtn} onPress={() => handleSend(messages[messages.length - 2]?.text)}>
                <Text style={styles.retryText}>Retry Query</Text>
              </TouchableOpacity>
            )}

            <Text style={styles.timestamp}>{m.timestamp}</Text>
          </View>
        ))}

        {loading && (
          <View style={[styles.messageBubble, styles.botBubble, styles.loadingBubble]}>
            <ActivityIndicator size="small" color="#166534" />
            <Text style={styles.loadingText}>
              Retrieving verified extension docs & reasoning with qwen2.5:7b-instruct...
            </Text>
          </View>
        )}
      </ScrollView>

      {/* Suggested Quick Prompts */}
      <View style={styles.bottomFixedContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipBar}>
          <TouchableOpacity
            style={styles.chip}
            onPress={() => handleSend(selectedLanguage === 'hi' ? 'Ã Â¤Â§Ã Â¤Â¾Ã Â¤Â¨ Ã Â¤â€¢Ã Â¥â‚¬ Ã Â¤â€¢Ã Â¤Å¸Ã Â¤Â¾Ã Â¤Ë† Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤ÂªÃ Â¤Â¹Ã Â¤Â²Ã Â¥â€¡ Ã Â¤Â¸Ã Â¤Â¿Ã Â¤â€šÃ Â¤Å¡Ã Â¤Â¾Ã Â¤Ë† Ã Â¤â€¢Ã Â¤Â¬ Ã Â¤Â°Ã Â¥â€¹Ã Â¤â€¢Ã Â¥â€¡Ã Â¤â€š?' : selectedLanguage === 'te' ? 'Ã Â°ÂµÃ Â°Â°Ã Â°Â¿ Ã Â°ÂªÃ Â°â€šÃ Â°Å¸ Ã Â°â€¢Ã Â±â€¹Ã Â°Â¤Ã Â°â€¢Ã Â±Â Ã Â°Å½Ã Â°Â¨Ã Â±ÂÃ Â°Â¨Ã Â°Â¿ Ã Â°Â°Ã Â±â€¹Ã Â°Å“Ã Â±ÂÃ Â°Â² Ã Â°Â®Ã Â±ÂÃ Â°â€šÃ Â°Â¦Ã Â±Â Ã Â°Â¨Ã Â±â‚¬Ã Â°Â°Ã Â±Â Ã Â°â€ Ã Â°ÂªÃ Â°Â¾Ã Â°Â²Ã Â°Â¿?' : 'When should irrigation be stopped before paddy harvest?')}
          >
            <Text style={styles.chipText}>Paddy Irrigation Stop</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.chip}
            onPress={() => handleSend(selectedLanguage === 'hi' ? 'Ã Â¤â€¦Ã Â¤Â®Ã Â¥ÂÃ Â¤Â²Ã Â¥â‚¬Ã Â¤Â¯ Ã Â¤Â®Ã Â¤Â¿Ã Â¤Å¸Ã Â¥ÂÃ Â¤Å¸Ã Â¥â‚¬ (pH 5.2) Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€“Ã Â¤Â¾Ã Â¤Â¦ Ã Â¤â€¢Ã Â¥Ë†Ã Â¤Â¸Ã Â¥â€¡ Ã Â¤Â¡Ã Â¤Â¾Ã Â¤Â²Ã Â¥â€¡Ã Â¤â€š?' : selectedLanguage === 'te' ? 'Ã Â°â€ Ã Â°Â®Ã Â±ÂÃ Â°Â² Ã Â°Â¨Ã Â±â€¡Ã Â°Â²Ã Â°Â²Ã Â±â€¹ Ã Â°Å½Ã Â°Â°Ã Â±ÂÃ Â°ÂµÃ Â±ÂÃ Â°Â² Ã Â°Â¯Ã Â°Â¾Ã Â°Å“Ã Â°Â®Ã Â°Â¾Ã Â°Â¨Ã Â±ÂÃ Â°Â¯Ã Â°â€š Ã Â°Å½Ã Â°Â²Ã Â°Â¾ Ã Â°Å¡Ã Â±â€¡Ã Â°Â¯Ã Â°Â¾Ã Â°Â²Ã Â°Â¿?' : 'How to manage fertilizer in acidic soil (pH 5.2)?')}
          >
            <Text style={styles.chipText}>Acidic Soil pH (5.2)</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.chip}
            onPress={() => handleSend('How does rain lockout protect fertilizer from leaching?')}
          >
            <Text style={styles.chipText}>Rain Lockout Protocol</Text>
          </TouchableOpacity>
        </ScrollView>

        {/* Input Bar */}
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder={
              selectedLanguage === 'hi'
                ? 'Ã Â¤Â¹Ã Â¤Â¿Ã Â¤â€šÃ Â¤Â¦Ã Â¥â‚¬ Ã Â¤Â®Ã Â¥â€¡Ã Â¤â€š Ã Â¤â€¢Ã Â¥Æ’Ã Â¤Â·Ã Â¤Â¿ Ã Â¤Â¸Ã Â¤Â²Ã Â¤Â¾Ã Â¤Â¹ Ã Â¤ÂªÃ Â¥â€šÃ Â¤â€ºÃ Â¥â€¡Ã Â¤â€š...'
                : selectedLanguage === 'te'
                ? 'Ã Â°ÂµÃ Â±ÂÃ Â°Â¯Ã Â°ÂµÃ Â°Â¸Ã Â°Â¾Ã Â°Â¯ Ã Â°Â¸Ã Â°Â²Ã Â°Â¹Ã Â°Â¾ Ã Â°â€¦Ã Â°Â¡Ã Â°â€”Ã Â°â€šÃ Â°Â¡Ã Â°Â¿...'
                : 'Ask AgriSaathi in English, Hindi, Telugu...'
            }
            placeholderTextColor="#888"
            value={input}
            onChangeText={setInput}
            onSubmitEditing={() => handleSend()}
          />

          <TouchableOpacity style={styles.sendButton} onPress={() => handleSend()}>
            <Text style={styles.sendIcon}>Ã¢Å¾â€</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F4FBF4' },
  headerBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB'
  },
  modelTagContainer: { flex: 1 },
  headerTitle: { fontSize: 16, fontWeight: '700', color: '#14532D' },
  statusRow: { flexDirection: 'row', alignItems: 'center', marginTop: 2 },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  dotGreen: { backgroundColor: '#16A34A' },
  dotOrange: { backgroundColor: '#EA580C' },
  modelStatusText: { fontSize: 11, color: '#4B5563', fontWeight: '500' },
  langSelector: { flexDirection: 'row', backgroundColor: '#F3F4F6', borderRadius: 8, padding: 2 },
  langChip: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  langChipActive: { backgroundColor: '#15803D' },
  langText: { fontSize: 11, fontWeight: '600', color: '#4B5563' },
  langTextActive: { color: '#FFFFFF' },
  offlineBanner: { backgroundColor: '#FEF3C7', padding: 8, alignItems: 'center' },
  offlineText: { color: '#92400E', fontSize: 12, fontWeight: 'bold' },
  chatArea: { flex: 1 },
  messageBubble: { padding: 12, borderRadius: 16, marginVertical: 6, maxWidth: '88%' },
  userBubble: { alignSelf: 'flex-end', backgroundColor: '#15803D' },
  botBubble: { alignSelf: 'flex-start', backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E5E7EB' },
  errorBubble: { borderColor: '#FCA5A5', backgroundColor: '#FEF2F2' },
  bubbleHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  chunksTag: { fontSize: 10, color: '#0F766E', fontWeight: '600', backgroundColor: '#F0FDFA', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  userText: { color: '#FFFFFF', fontSize: 15, lineHeight: 22 },
  botText: { color: '#111827', fontSize: 14, lineHeight: 22 },
  loadingBubble: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  loadingText: { color: '#4B5563', fontSize: 12, flex: 1 },
  timestamp: { fontSize: 10, color: '#9CA3AF', marginTop: 6, alignSelf: 'flex-end' },
  citationsContainer: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#F3F4F6' },
  citationsHeading: { fontSize: 11, fontWeight: '700', color: '#0F766E', marginBottom: 4 },
  citationCard: { backgroundColor: '#F8FAFC', padding: 6, borderRadius: 6, marginVertical: 2, borderWidth: 1, borderColor: '#E2E8F0' },
  citationTitle: { fontSize: 11, fontWeight: '600', color: '#1E293B' },
  citationSource: { fontSize: 10, color: '#64748B', marginTop: 1 },
  warningBox: { marginTop: 6, backgroundColor: '#FFFBEB', padding: 6, borderRadius: 6 },
  warningText: { fontSize: 11, color: '#B45309' },
  retryBtn: { marginTop: 8, alignSelf: 'flex-start', backgroundColor: '#FEE2E2', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6 },
  retryText: { fontSize: 11, color: '#B91C1C', fontWeight: '600' },
  bottomFixedContainer: {
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingBottom: 8
  },
  chipBar: { maxHeight: 40, paddingHorizontal: 8, marginVertical: 6 },
  chip: { backgroundColor: '#DCFCE7', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, marginRight: 8, height: 32, justifyContent: 'center' },
  chipText: { color: '#14532D', fontSize: 12, fontWeight: '600' },
  inputContainer: { flexDirection: 'row', paddingHorizontal: 8, alignItems: 'center' },
  input: { flex: 1, height: 44, backgroundColor: '#F9FAFB', borderRadius: 22, paddingHorizontal: 16, fontSize: 14, color: '#111827', borderWidth: 1, borderColor: '#E5E7EB' },
  sendButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#15803D', justifyContent: 'center', alignItems: 'center', marginLeft: 8 },
  sendIcon: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' }
});

