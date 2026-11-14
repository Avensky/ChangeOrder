// Use the transport that supports Expo File objects, regardless of fetch env flags.
import { fetch } from 'expo/fetch';
import { Platform } from 'react-native';

// Expo replaces this static reference with the value from frontend/.env.
const configuredApiUrl = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');

// A LAN web page must not send the phone to its own localhost. Preserve the
// configured API port; remote API hosts and native builds stay explicit.
function webApiUrl() {
  if (Platform.OS !== 'web' || typeof window === 'undefined' || !configuredApiUrl) return configuredApiUrl;
  try {
    const url = new URL(configuredApiUrl);
    const localHosts = ['localhost', '127.0.0.1', '[::1]'];
    if (localHosts.includes(url.hostname) && !localHosts.includes(window.location.hostname)) {
      url.hostname = window.location.hostname;
    }
    return url.toString().replace(/\/+$/, '');
  } catch {
    return configuredApiUrl;
  }
}
export const API_URL = webApiUrl();

let accessToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;
export function setAccessToken(value: string | null) { accessToken = value; }
export function setUnauthorizedHandler(value: (() => void) | null) { unauthorizedHandler = value; }

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 8000,
): Promise<T> {
  if (!API_URL || API_URL.toLowerCase().includes('your_pc_ip')) {
    throw new Error('Set EXPO_PUBLIC_API_URL in frontend/.env to your PC address, then reload Expo.');
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const headers = new Headers(options.headers);
    const token = accessToken;
    const publicRequest = path.startsWith('/api/v1/approval-session') || path === '/health';
    if (token && !publicRequest && !headers.has('Authorization')) headers.set('Authorization', 'Bearer ' + token);
    const response = await fetch(API_URL + path, { ...options, headers, signal: controller.signal });
    if (!response.ok) {
      if (response.status === 401 && token && token === accessToken && !publicRequest) {
        setAccessToken(null);
        unauthorizedHandler?.();
      }
      const body = await response.json().catch(() => null);
      const detail = body?.detail;
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item: { msg: string }) => item.msg).join('; ')
          : 'Backend returned HTTP ' + response.status;
      throw new Error(message);
    }
    return await response.json() as T;
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error('Connection timed out. Check the PC address, Wi-Fi, and running backend.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function checkBackendHealth(): Promise<{ status: 'ok' }> {
  const data = await requestJson<unknown>('/health');
  if (typeof data !== 'object' || data === null || !('status' in data) || data.status !== 'ok') {
    throw new Error('The server did not return the expected health response.');
  }
  return { status: 'ok' };
}
