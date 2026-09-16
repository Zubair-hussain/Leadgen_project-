'use client';

import axios from 'axios';
import { auth } from '../firebase';

const baseURL = process.env.NEXT_PUBLIC_API_URL;
if (!baseURL) {
  throw new Error('NEXT_PUBLIC_API_URL is required');
}

const ACCESS_KEY = 'leadgen_jwt_access';
const REFRESH_KEY = 'leadgen_jwt_refresh';

// --- Django SimpleJWT token store (per-viewer, best-effort) ------------------
export const getAccessToken = () => {
  try {
    return localStorage.getItem(ACCESS_KEY);
  } catch {
    return null;
  }
};

export const getRefreshToken = () => {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
};

export const setTokens = ({ access, refresh } = {}) => {
  try {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  } catch {
    /* storage unavailable — fall back to Firebase tokens */
  }
};

export const clearTokens = () => {
  try {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  } catch {
    /* ignore */
  }
};

const api = axios.create({
  baseURL: baseURL.endsWith('/') ? baseURL : baseURL + '/',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach a bearer token: prefer the Django-issued JWT, else the Firebase token.
api.interceptors.request.use(async (config) => {
  const jwt = getAccessToken();
  if (jwt) {
    config.headers.Authorization = `Bearer ${jwt}`;
    return config;
  }
  const user = auth.currentUser;
  if (user) {
    const token = await user.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On a 401, try a one-shot refresh of the Django JWT and replay the request.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const refresh = getRefreshToken();

    if (status === 401 && refresh && original && !original._retried) {
      original._retried = true;
      try {
        const { data } = await axios.post(`${api.defaults.baseURL}token/refresh/`, { refresh });
        setTokens({ access: data.access, refresh: data.refresh });
        original.headers = { ...original.headers, Authorization: `Bearer ${data.access}` };
        return api(original);
      } catch (refreshError) {
        clearTokens();
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

// Exchange a signed-in Firebase user for a Django SimpleJWT pair and store it.
export const exchangeFirebaseToken = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error('No signed-in Firebase user to exchange');
  const idToken = await user.getIdToken();
  const { data } = await axios.post(
    `${api.defaults.baseURL}token/firebase/`,
    {},
    { headers: { Authorization: `Bearer ${idToken}` } },
  );
  setTokens({ access: data.access, refresh: data.refresh });
  return data;
};

// Health check to verify backend connection
export const checkBackendHealth = async () => {
  try {
    const response = await api.get('health/');
    return { connected: true, data: response.data };
  } catch (error) {
    return { connected: false, error: error.message };
  }
};

export default api;
