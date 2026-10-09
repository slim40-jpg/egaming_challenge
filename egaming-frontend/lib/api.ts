// frontend/lib/api.ts

import axios from 'axios';

export const CLOUD_URL = process.env.NEXT_PUBLIC_CLOUD_API_URL!;
export const LOCAL_URL = process.env.NEXT_PUBLIC_LOCAL_API_URL!;

// ─── Token helper ────────────────────────────────────────
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return (
    localStorage.getItem('access_token') ||
    localStorage.getItem('cloud_access_token') ||
    localStorage.getItem('token')
  );
}

// ─── Cloud client (public, ngrok) ────────────────────────
export const cloudApi = axios.create({ baseURL: CLOUD_URL });

cloudApi.interceptors.request.use((config) => {
  const t = getAuthToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  // Bypass ngrok's warning page
  config.headers['ngrok-skip-browser-warning'] = 'true';
  return config;
});

// ─── Local client (LAN only) ─────────────────────────────
export const localApi = axios.create({ baseURL: LOCAL_URL });

localApi.interceptors.request.use((config) => {
  const t = getAuthToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// ─── Cloud calls ─────────────────────────────────────────
export const cloud = {
  login: (username: string, password: string) =>
    cloudApi.post('/api/auth/login', { username, password }),

  register: (data: {
    username: string;
    password: string;
    email?: string;
    full_name?: string;
    phone?: string;
    role?: string;
  }) => cloudApi.post('/api/auth/register', data),

  listPCs: (centerId = 'main') =>
    cloudApi.get('/api/pcs', { params: { center_id: centerId } }),

  availability: (pcId: string, start: string, end: string) =>
    cloudApi.get('/api/pcs/availability', {
      params: { pc_id: pcId, start, end },
    }),

  myReservations: () => cloudApi.get('/api/reservations/my'),

  createReservation: (pcId: string, start: string, end: string) =>
    cloudApi.post('/api/reservations/create', {
      pc_id: pcId,
      start_time: start,
      end_time: end,
    }),

  cancelReservation: (id: number) =>
    cloudApi.post(`/api/reservations/${id}/cancel`),

  // 👇 NEW: Cloud Wallet Endpoints (Player-facing)
  getWallet: () => cloudApi.get('/api/wallet'),
  
  rechargeWallet: (amount: number) => 
    cloudApi.post('/api/wallet/recharge', { amount }),
  
  getTransactions: () => cloudApi.get('/api/wallet/transactions'),
};

// ─── Local calls (admin only) ────────────────────────────
export const local = {
  pcDetail: (pcId: string) => localApi.get(`/api/pc/${pcId}`),
  pcGames: (pcId: string) => localApi.get(`/api/pc/${pcId}/games`),
  wallet: () => localApi.get('/api/wallet'),
  topup: (amount: number) => localApi.post('/api/wallet/topup', { amount }),

  startSession: (pcId: string, userName: string) =>
    localApi.post('/api/session/start', {
      pc_id: pcId,
      user_name: userName,
    }),

  endSession: (pcId: string) => localApi.post('/api/session/end', { pc_id: pcId }),

  command: (pcId: string, command: string) =>
    localApi.post('/api/command', { pc_id: pcId, command }),

  launchGame: (pcId: string, game: any) =>
    localApi.post('/api/games/launch-installed', {
      pc_id: pcId,
      game_name: game.name,
      executable: game.executable_path,
      shortcut: game.shortcut_path,
    }),
};