// src/lib/api.ts

import axios from 'axios';
import { PC, Game, MembershipPlan, Reservation } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================
// PC Endpoints
// ============================================================

export const getPCs = async (): Promise<PC[]> => {
  const response = await api.get('/api/pcs');
  return response.data.pcs || [];
};

export const getPC = async (pcId: string): Promise<PC> => {
  const response = await api.get(`/api/pc/${pcId}`);
  return response.data;
};

export const getPCGames = async (pcId: string): Promise<Game[]> => {
  const response = await api.get(`/api/pc/${pcId}/games`);
  return response.data.games || [];
};

// ============================================================
// Session Endpoints
// ============================================================

export const startSession = async (pcId: string, userName: string): Promise<any> => {
  const response = await api.post('/api/session/start', {
    pc_id: pcId,
    user_name: userName,
    session_type: 'time',
  });
  return response.data;
};

export const endSession = async (pcId: string): Promise<any> => {
  const response = await api.post('/api/session/end', {
    pc_id: pcId,
  });
  return response.data;
};

// ============================================================
// Command Endpoints
// ============================================================

export const sendCommand = async (pcId: string, command: string): Promise<any> => {
  const response = await api.post('/api/command', {
    pc_id: pcId,
    command: command,
  });
  return response.data;
};

// ============================================================
// Game Endpoints
// ============================================================

export const launchGame = async (pcId: string, gameName: string, executable: string, shortcut?: string): Promise<any> => {
  const response = await api.post('/api/games/launch-installed', {
    pc_id: pcId,
    game_name: gameName,
    executable: executable,
    shortcut: shortcut || '',
  });
  return response.data;
};

// ============================================================
// Wallet Endpoints
// ============================================================

export const getWallet = async (pcId: string): Promise<any> => {
  const response = await api.get(`/api/wallet/${pcId}`);
  return response.data;
};

export const topupWallet = async (pcId: string, amount: number): Promise<any> => {
  const response = await api.post('/api/wallet/topup', {
    pc_id: pcId,
    amount: amount,
  });
  return response.data;
};

// ============================================================
// Membership Endpoints
// ============================================================

export const getMembershipPlans = async (): Promise<MembershipPlan[]> => {
  const response = await api.get('/api/membership/plans');
  return response.data.plans || [];
};

export const buyMembership = async (pcId: string, plan: string): Promise<any> => {
  const response = await api.post('/api/membership/buy', {
    pc_id: pcId,
    plan: plan,
  });
  return response.data;
};

// ============================================================
// Reservation Endpoints
// ============================================================

export const getReservations = async (): Promise<Reservation[]> => {
  const response = await api.get('/api/reservations');
  return response.data.reservations || [];
};

export const createReservation = async (reservation: Omit<Reservation, 'id' | 'status' | 'created_at'>): Promise<any> => {
  const response = await api.post('/api/reservations/create', reservation);
  return response.data;
};

export const cancelReservation = async (reservationId: number): Promise<any> => {
  const response = await api.post(`/api/reservations/${reservationId}/cancel`);
  return response.data;
};