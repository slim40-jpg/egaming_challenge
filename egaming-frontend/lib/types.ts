// lib/types.ts

export interface Hardware {
  cpu: string;
  gpu: string;
  ram: string;
}

export interface Session {
  user: string;
  start_time: string;
  game: string;
  game_type: string;
  status: string;
  price_per_minute: number;
  duration?: number;
  cost?: number;
}

export interface Game {
  name: string;
  executable_path: string;
  shortcut_path: string;
  platform: string;
  is_running: boolean;
}

export interface PC {
  id: string;
  mac_address: string;
  hostname: string;
  online: boolean;
  in_session: boolean;
  game: string;
  session: Session | null;
  session_type: string;
  status: string;
  cpu: number;
  ram: number;
  gpu: number;
  cpu_temp: number;
  gpu_temp: number;
  ip_address: string;
  hardware: Hardware;
  wallet_balance: number;
  installed_games: Game[];
  branch: string;
}

export interface ApiResponse<T> {
  status: string;
  data?: T;
  message?: string;
}

export interface MembershipPlan {
  id: string;
  name: string;
  price: number;
  hours: number;
  color: string;
}

export interface Reservation {
  id: number;
  pc_id: string;
  user_name: string;
  start_time: string;
  end_time: string;
  status: string;
}