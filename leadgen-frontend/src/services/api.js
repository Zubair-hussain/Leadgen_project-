import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL;
const api = axios.create({
  baseURL: baseURL?.endsWith('/') ? baseURL : baseURL + '/',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health check to verify backend connection
export const checkBackendHealth = async () => {
  try {
    const response = await api.get('health/');
    return { connected: true, data: response.data };
  } catch (error) {
    return { connected: false, error: error.message };
  }
};

// Optional: add token/interceptors later
// api.interceptors.request.use(config => { ... })

export default api;