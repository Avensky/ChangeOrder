// Expo replaces this static reference with the value from frontend/.env.
export const API_URL = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');

export async function checkBackendHealth(): Promise<{ status: 'ok' }> {
  if (!API_URL || API_URL.toLowerCase().includes('your_pc_ip')) {
    throw new Error('Set EXPO_PUBLIC_API_URL in frontend/.env to your PC address, then reload Expo.');
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const response = await fetch(API_URL + '/health', { signal: controller.signal });
    if (!response.ok) throw new Error('Backend returned HTTP ' + response.status);

    const data: unknown = await response.json();
    if (typeof data !== 'object' || data === null || !('status' in data) || data.status !== 'ok') {
      throw new Error('The server did not return the expected health response.');
    }
    return { status: 'ok' };
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error('Connection timed out. Check the PC address, Wi-Fi, and running backend.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
