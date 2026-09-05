// frontend/lib/api.ts

import axios from 'axios';

// ============================================================
// API CONFIGURATION
// ============================================================

const CLOUD_API_URL = (process.env.NEXT_PUBLIC_CLOUD_API_URL || 'https://premium-mayflower-precut.ngrok-free.dev').replace(/\/+$/, '');
const LOCAL_API_URL = (process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003').replace(/\/+$/, '');

console.log('📡 Cloud API:', CLOUD_API_URL);
console.log('📡 Local API:', LOCAL_API_URL);

// ============================================================
// CLOUD API CLIENT
// ============================================================

const cloudApi = axios.create({
  baseURL: CLOUD_API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  timeout: 30000,
  withCredentials: false,
});

// Request interceptor - Add token to EVERY request
cloudApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('cloud_access_token');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('🔑 Token added to request:', config.url);
    } else {
      console.warn('⚠️ No token found for request:', config.url);
    }
    
    console.log('📤 Request:', config.method?.toUpperCase(), config.url);
    
    return config;
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
cloudApi.interceptors.response.use(
  (response) => {
    console.log('📥 Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('❌ Response Error:', error.message);
    if (error.response) {
      console.error('   Status:', error.response.status);
      console.error('   Data:', error.response.data);
      
      if (error.response.status === 401) {
        localStorage.removeItem('cloud_access_token');
        localStorage.removeItem('cloud_user');
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// ============================================================
// CLOUD AUTH ENDPOINTS
// ============================================================

export const cloudRegister = async (data: any) => {
  try {
    const response = await cloudApi.post('/api/auth/register', data);
    return response.data;
  } catch (error: any) {
    console.error('Register error:', error.response?.data || error.message);
    throw error;
  }
};

export const cloudLogin = async (username: string, password: string) => {
  try {
    const response = await cloudApi.post('/api/auth/login', { username, password });
    
    if (response.data.status === 'ok' && response.data.access_token) {
      localStorage.setItem('cloud_access_token', response.data.access_token);
      localStorage.setItem('cloud_user', JSON.stringify(response.data.user));
      console.log('✅ Token stored successfully');
    }
    
    return response.data;
  } catch (error: any) {
    console.error('Login error:', error.response?.data || error.message);
    throw error;
  }
};

export const cloudLogout = () => {
  localStorage.removeItem('cloud_access_token');
  localStorage.removeItem('cloud_user');
};

// ============================================================
// CLOUD RESERVATION ENDPOINTS
// ============================================================

export const cloudGetPCs = async () => {
  try {
    const token = localStorage.getItem('cloud_access_token');
    console.log('🔑 Token before request:', token ? 'Present' : 'Missing');
    
    const response = await cloudApi.get('/api/pcs');
    return response.data.pcs || [];
  } catch (error: any) {
    console.error('Get PCs error:', error.response?.data || error.message);
    return [];
  }
};

export const cloudGetMyReservations = async () => {
  try {
    const response = await cloudApi.get('/api/reservations/my');
    return response.data.reservations || [];
  } catch (error: any) {
    console.error('Get reservations error:', error.response?.data || error.message);
    return [];
  }
};

export const cloudCreateReservation = async (data: any) => {
  try {
    const response = await cloudApi.post('/api/reservations/create', data);
    return response.data;
  } catch (error: any) {
    console.error('Create reservation error:', error.response?.data || error.message);
    throw error;
  }
};

export const cloudCancelReservation = async (reservationId: string) => {
  try {
    const response = await cloudApi.post(`/api/reservations/${reservationId}/cancel`);
    return response.data;
  } catch (error: any) {
    console.error('Cancel reservation error:', error.response?.data || error.message);
    throw error;
  }
};

// ✅ ADD THIS MISSING EXPORT
export const cloudCheckAvailability = async (pcId: string, startTime: string, endTime: string) => {
  try {
    const response = await cloudApi.get('/api/pcs/availability', {
      params: { pc_id: pcId, start_time: startTime, end_time: endTime }
    });
    return response.data;
  } catch (error: any) {
    console.error('Check availability error:', error.response?.data || error.message);
    throw error;
  }
};

// ============================================================
// LOCAL API CLIENT (PC Management - Admin only)
// ============================================================

const localApi = axios.create({
  baseURL: LOCAL_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

localApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ============================================================
// LOCAL API ENDPOINTS
// ============================================================

export const localLogin = async (username: string, password: string) => {
  try {
    const response = await localApi.post('/api/auth/login', { username, password });
    return response.data;
  } catch (error: any) {
    console.error('Local login error:', error.response?.data || error.message);
    throw error;
  }
};

export const getPCs = async () => {
  try {
    const response = await localApi.get('/api/pcs');
    return response.data.pcs || [];
  } catch (error: any) {
    console.error('Get PCs error:', error.response?.data || error.message);
    return [];
  }
};

export const getPC = async (pcId: string) => {
  try {
    const response = await localApi.get(`/api/pc/${pcId}`);
    return response.data;
  } catch (error: any) {
    console.error('Get PC error:', error.response?.data || error.message);
    throw error;
  }
};

export const getPCGames = async (pcId: string) => {
  try {
    const response = await localApi.get(`/api/pc/${pcId}/games`);
    return response.data.games || [];
  } catch (error: any) {
    console.error('Get PC games error:', error.response?.data || error.message);
    return [];
  }
};

export const sendCommand = async (pcId: string, command: string) => {
  try {
    const response = await localApi.post('/api/command', { pc_id: pcId, command });
    return response.data;
  } catch (error: any) {
    console.error('Send command error:', error.response?.data || error.message);
    throw error;
  }
};

export const startSession = async (pcId: string, userName: string) => {
  try {
    const response = await localApi.post('/api/session/start', { pc_id: pcId, user_name: userName });
    return response.data;
  } catch (error: any) {
    console.error('Start session error:', error.response?.data || error.message);
    throw error;
  }
};

export const endSession = async (pcId: string) => {
  try {
    const response = await localApi.post('/api/session/end', { pc_id: pcId });
    return response.data;
  } catch (error: any) {
    console.error('End session error:', error.response?.data || error.message);
    throw error;
  }
};

export const getWallet = async () => {
  try {
    const response = await localApi.get('/api/wallet');
    return response.data;
  } catch (error: any) {
    console.error('Get wallet error:', error.response?.data || error.message);
    throw error;
  }
};

export const topupWallet = async (amount: number) => {
  try {
    const response = await localApi.post('/api/wallet/topup', { amount });
    return response.data;
  } catch (error: any) {
    console.error('Topup wallet error:', error.response?.data || error.message);
    throw error;
  }
};

export const getReservations = async () => {
  try {
    const response = await localApi.get('/api/reservations');
    return response.data.reservations || [];
  } catch (error: any) {
    console.error('Get reservations error:', error.response?.data || error.message);
    return [];
  }
};

export const cancelReservationLocal = async (reservationId: string) => {
  try {
    const response = await localApi.post(`/api/reservations/${reservationId}/cancel`);
    return response.data;
  } catch (error: any) {
    console.error('Cancel reservation error:', error.response?.data || error.message);
    throw error;
  }
};

export const launchInstalledGame = async (pcId: string, gameName: string, executable: string, shortcut?: string) => {
  try {
    const response = await localApi.post('/api/games/launch-installed', {
      pc_id: pcId,
      game_name: gameName,
      executable: executable,
      shortcut: shortcut || ''
    });
    return response.data;
  } catch (error: any) {
    console.error('Launch game error:', error.response?.data || error.message);
    throw error;
  }
};

// ============================================================
// HEALTH CHECK
// ============================================================

export const cloudHealthCheck = async () => {
  try {
    const response = await cloudApi.get('/api/health');
    return response.data;
  } catch (error: any) {
    console.error('Health check error:', error.message);
    return null;
  }
};