import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

const currentUser = { getIdToken: vi.fn(async () => 'firebase-token') };
const authState = { currentUser };

vi.mock('../firebase', () => ({
  auth: authState,
}));

describe('api service', () => {
  beforeEach(() => {
    vi.resetModules();
    authState.currentUser = currentUser;
    currentUser.getIdToken.mockClear();
    try {
      localStorage.clear();
    } catch {
      /* ignore */
    }
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('attaches the Firebase token when no Django JWT is stored', async () => {
    const { default: api } = await import('./api');
    const interceptor = api.interceptors.request.handlers[0].fulfilled;
    const config = await interceptor({ headers: {} });
    expect(config.headers.Authorization).toBe('Bearer firebase-token');
  });

  it('prefers a stored Django JWT over the Firebase token', async () => {
    const mod = await import('./api');
    mod.setTokens({ access: 'django-access', refresh: 'django-refresh' });
    const interceptor = mod.default.interceptors.request.handlers[0].fulfilled;
    const config = await interceptor({ headers: {} });
    expect(config.headers.Authorization).toBe('Bearer django-access');
    expect(currentUser.getIdToken).not.toHaveBeenCalled();
  });

  it('leaves headers untouched when no user and no JWT', async () => {
    authState.currentUser = null;
    const { default: api } = await import('./api');
    const interceptor = api.interceptors.request.handlers[0].fulfilled;
    const config = await interceptor({ headers: {} });
    expect(config.headers.Authorization).toBeUndefined();
  });

  it('stores and clears tokens', async () => {
    const mod = await import('./api');
    mod.setTokens({ access: 'a', refresh: 'r' });
    expect(mod.getAccessToken()).toBe('a');
    expect(mod.getRefreshToken()).toBe('r');
    mod.clearTokens();
    expect(mod.getAccessToken()).toBeNull();
  });

  it('exchanges a Firebase user for a Django JWT pair', async () => {
    const mod = await import('./api');
    const axios = (await import('axios')).default;
    const post = vi.spyOn(axios, 'post').mockResolvedValue({ data: { access: 'x', refresh: 'y' } });
    const result = await mod.exchangeFirebaseToken();
    expect(post).toHaveBeenCalledWith(
      expect.stringContaining('token/firebase/'),
      {},
      expect.objectContaining({ headers: { Authorization: 'Bearer firebase-token' } }),
    );
    expect(result).toEqual({ access: 'x', refresh: 'y' });
    expect(mod.getAccessToken()).toBe('x');
  });

  it('throws when exchanging without a signed-in user', async () => {
    authState.currentUser = null;
    const mod = await import('./api');
    await expect(mod.exchangeFirebaseToken()).rejects.toThrow(/No signed-in Firebase user/);
  });

  it('normalises the base URL to a trailing slash', async () => {
    const { default: api } = await import('./api');
    expect(api.defaults.baseURL.endsWith('/')).toBe(true);
  });

  it('reports connected on a healthy backend', async () => {
    const mod = await import('./api');
    vi.spyOn(mod.default, 'get').mockResolvedValue({ data: { status: 'ok' } });
    const result = await mod.checkBackendHealth();
    expect(result).toEqual({ connected: true, data: { status: 'ok' } });
  });

  it('reports disconnected when the health check throws', async () => {
    const mod = await import('./api');
    vi.spyOn(mod.default, 'get').mockRejectedValue(new Error('network down'));
    const result = await mod.checkBackendHealth();
    expect(result).toEqual({ connected: false, error: 'network down' });
  });

  it('refreshes the JWT and replays the request on a 401', async () => {
    const mod = await import('./api');
    const axios = (await import('axios')).default;
    mod.setTokens({ access: 'old', refresh: 'refresh-1' });
    const responseInterceptor = mod.default.interceptors.response.handlers[0].rejected;

    vi.spyOn(axios, 'post').mockResolvedValue({ data: { access: 'new', refresh: 'refresh-2' } });
    // Stub adapter so the replayed request resolves without touching the network.
    const origConfig = {
      headers: {},
      _retried: false,
      adapter: async (config) => ({ data: 'replayed', status: 200, statusText: 'OK', headers: {}, config }),
    };

    const result = await responseInterceptor({ config: origConfig, response: { status: 401 } });

    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('token/refresh/'),
      { refresh: 'refresh-1' },
    );
    expect(mod.getAccessToken()).toBe('new');
    expect(result.data).toBe('replayed');
    expect(result.config.headers.Authorization).toBe('Bearer new');
  });

  it('clears tokens when the refresh itself fails', async () => {
    const mod = await import('./api');
    const axios = (await import('axios')).default;
    mod.setTokens({ access: 'old', refresh: 'refresh-1' });
    const responseInterceptor = mod.default.interceptors.response.handlers[0].rejected;
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('refresh dead'));

    await expect(
      responseInterceptor({ config: { headers: {} }, response: { status: 401 } }),
    ).rejects.toThrow('refresh dead');
    expect(mod.getAccessToken()).toBeNull();
  });
});
