// Use the transport that supports Expo File objects, regardless of fetch env flags.
import { fetch } from 'expo/fetch';

// Expo replaces this static reference with the value from frontend/.env.
export const API_URL = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');

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
    const response = await fetch(API_URL + path, { ...options, signal: controller.signal });
    if (!response.ok) {
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
