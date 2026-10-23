import { useState } from 'react';
import { Button, KeyboardAvoidingView, Platform, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { ChangeOrderForm } from '@/features/change-orders/change-order-form';
import { API_URL, checkBackendHealth } from '@/lib/api';

export default function HomeScreen() {
  const [status, setStatus] = useState('Not checked');
  const [loading, setLoading] = useState(false);

  async function checkBackend() {
    setLoading(true);
    setStatus('Connecting...');
    try {
      const result = await checkBackendHealth();
      setStatus('Backend: ' + result.status);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Connection failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView style={styles.scroll} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView style={styles.scroll} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
            <ThemedView style={styles.heroSection}>
              <ThemedText type="title" style={styles.title}>
                Change Order
              </ThemedText>
            </ThemedView>

            <ChangeOrderForm />

            <ThemedView type="backgroundElement" style={styles.stepContainer}>
              <ThemedText type="smallBold">Backend connection</ThemedText>
              <ThemedText type="code">{API_URL ?? 'Configure frontend/.env'}</ThemedText>
              <Button
                title={loading ? 'Checking...' : 'Check backend'}
                onPress={checkBackend}
                disabled={loading}
              />
              <ThemedText>{status}</ThemedText>
            </ThemedView>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    flexDirection: 'row',
  },
  safeArea: {
    flex: 1,
    paddingHorizontal: Spacing.four,
    maxWidth: MaxContentWidth,
  },
  scroll: {
    flex: 1,
    alignSelf: 'stretch',
  },
  content: {
    alignItems: 'center',
    gap: Spacing.three,
    paddingBottom: BottomTabInset + Spacing.three,
  },
  heroSection: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.four,
    paddingHorizontal: Spacing.four,
    gap: Spacing.four,
  },
  title: {
    textAlign: 'center',
    fontSize: 36,
    lineHeight: 44,
  },
  stepContainer: {
    gap: Spacing.three,
    alignSelf: 'stretch',
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.four,
    borderRadius: Spacing.four,
  },
});
