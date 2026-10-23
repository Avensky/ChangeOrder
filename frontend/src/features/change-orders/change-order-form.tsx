import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { useRef, useState } from 'react';
import { ActivityIndicator, Button, Platform, StyleSheet, TextInput, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { API_URL } from '@/lib/api';

import { submitChange } from './api';
import type { ChangeOrder, Severity } from './types';

export function ChangeOrderForm() {
  const theme = useTheme();
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<Severity>('normal');
  const [photo, setPhoto] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [picking, setPicking] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState<ChangeOrder | null>(null);
  const submitting = useRef(false);
  const busy = picking || sending;

  async function pickPhoto(source: 'camera' | 'library') {
    setError('');
    setPicking(true);
    try {
      if (source === 'camera' && Platform.OS !== 'web') {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) {
          throw new Error('Allow camera access in Settings, or choose an existing photo.');
        }
      }
      const options: ImagePicker.ImagePickerOptions = {
        mediaTypes: ['images'],
        quality: 0.7,
        allowsEditing: false,
      };
      const result = await (source === 'camera'
        ? ImagePicker.launchCameraAsync(options)
        : ImagePicker.launchImageLibraryAsync(options));
      if (!result.canceled) {
        const selected = result.assets[0];
        if (selected.fileSize && selected.fileSize > 10 * 1024 * 1024) {
          throw new Error('Choose an image that is 10 MB or smaller.');
        }
        setPhoto(selected);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not open the photo picker.');
    } finally {
      setPicking(false);
    }
  }

  async function send() {
    if (submitting.current) return;
    setError('');
    setSubmitted(null);
    if (!description.trim() || !photo) {
      setError('Add a short description and one photo before sending.');
      return;
    }
    submitting.current = true;
    setSending(true);
    try {
      const change = await submitChange(description, severity, photo);
      setSubmitted(change);
      setDescription('');
      setSeverity('normal');
      setPhoto(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The change could not be sent.');
    } finally {
      submitting.current = false;
      setSending(false);
    }
  }

  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <ThemedText type="smallBold">New work order change</ThemedText>
      <ThemedText>Describe what needs to change and attach a photo for the office.</ThemedText>

      <ThemedText type="smallBold">Priority</ThemedText>
      <View style={styles.buttons}>
        {(['normal', 'high'] as const).map((value) => (
          <View key={value} style={styles.button}>
            <Button
              title={(severity === value ? '✓ ' : '') + (value === 'high' ? 'High' : 'Normal')}
              onPress={() => setSeverity(value)}
              disabled={busy}
              accessibilityLabel={value + ' priority'}
              accessibilityState={{ selected: severity === value }}
            />
          </View>
        ))}
      </View>

      <ThemedText type="smallBold">What changed?</ThemedText>
      <TextInput
        accessibilityLabel="Change description"
        placeholder="Example: Move the outlet 12 inches left to clear the cabinet."
        placeholderTextColor={theme.textSecondary}
        value={description}
        onChangeText={setDescription}
        maxLength={500}
        multiline
        editable={!busy}
        style={[styles.input, { color: theme.text, borderColor: theme.textSecondary }]}
      />
      <ThemedText type="small" themeColor="textSecondary">{description.length}/500 characters</ThemedText>

      <View style={styles.buttons}>
        <View style={styles.button}>
          <Button title="Take photo" onPress={() => pickPhoto('camera')} disabled={busy} />
        </View>
        <View style={styles.button}>
          <Button title="Choose photo" onPress={() => pickPhoto('library')} disabled={busy} />
        </View>
      </View>
      {picking && <ActivityIndicator accessibilityLabel="Opening photo picker" />}
      {photo && (
        <>
          <Image source={{ uri: photo.uri }} style={styles.photo} contentFit="contain" accessibilityLabel="Selected photo" />
          <Button title="Remove photo" onPress={() => setPhoto(null)} disabled={busy} />
        </>
      )}
      {!!error && <ThemedText accessibilityRole="alert">{error}</ThemedText>}
      <Button
        title={sending ? 'Sending...' : 'Send to office'}
        onPress={send}
        disabled={busy || !photo || !description.trim()}
      />
      {sending && <ActivityIndicator accessibilityLabel="Uploading change" />}

      {submitted && (
        <View style={styles.receipt} accessibilityLiveRegion="polite">
          <ThemedText type="smallBold">Submitted to office</ThemedText>
          <ThemedText>{submitted.description}</ThemedText>
          <ThemedText>Priority: {submitted.severity === 'high' ? 'High' : 'Normal'}</ThemedText>
          <ThemedText>Status: {submitted.status}</ThemedText>
          <ThemedText type="code">Reference: {submitted.id}</ThemedText>
          {submitted.photo_key && (
            <Image
              source={{ uri: API_URL + '/uploads/' + submitted.photo_key }}
              style={styles.photo}
              contentFit="contain"
              accessibilityLabel="Uploaded photo from backend"
            />
          )}
        </View>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: Spacing.three,
    alignSelf: 'stretch',
    padding: Spacing.three,
    borderRadius: Spacing.four,
  },
  buttons: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  button: { flexGrow: 1 },
  input: {
    borderWidth: 1,
    borderRadius: Spacing.two,
    padding: Spacing.three,
    minHeight: 110,
    textAlignVertical: 'top',
    fontSize: 16,
  },
  photo: { width: '100%', height: 220, borderRadius: Spacing.two },
  receipt: { gap: Spacing.two, paddingTop: Spacing.three },
});
