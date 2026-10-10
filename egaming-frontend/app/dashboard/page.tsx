'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cloud, getAuthToken } from '@/lib/api';

type PCMirror = {
  pc_id: string;
  name: string;
  online: boolean;
  state: 'available' | 'reserved' | 'in_session' | 'offline' | 'maintenance';
  installed_games: string[];
  last_sync: string | null;
};

const stateColor = {
  available: 'text-green-400',
  reserved: 'text-yellow-400',
  in_session: 'text-blue-400',
  offline: 'text-gray-500',
  maintenance: 'text-red-400',
};

const stateEmoji = {
  available: '🟢',
  reserved: '🟡',
  in_session: '🔵',
  offline: '⚫',
  maintenance: '🔧',
};

// Defensive: cloud may have stored objects; normalize to strings for rendering
const toGameName = (g: any): string =>
  typeof g === 'string' ? g : (g?.name ?? '');

export default function Dashboard() {
  const router = useRouter();
  const [pcs, setPcs] = useState<PCMirror[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push('/login');
      return;
    }

    const raw = localStorage.getItem('cloud_user') || localStorage.getItem('user');
    if (raw) {
      try {
        const u = JSON.parse(raw);
        setUser(u);
        setIsAdmin(u?.role === 'admin');
      } catch {
        // ignore bad JSON
      }
    }

    loadPCs();
    const interval = setInterval(loadPCs, 8000);
    return () => clearInterval(interval);
  }, []);

  const loadPCs = async () => {
    try {
      const r = await cloud.listPCs('main');
      setPcs(r.data.pcs || []);
    } catch (e: any) {
      console.error('Failed to load PCs:', e?.message);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.clear();
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
          <h1 className="text-3xl font-bold text-white">
            🎮 Ninety Gaming House
          </h1>
          
          <div className="flex items-center gap-3 flex-wrap">
            {/* User Info & Admin Badge */}
            <div className="flex items-center gap-2 mr-2">
              <span className="text-gray-400 text-sm">
                👤 {user?.username}
              </span>
              {isAdmin && (
                <span className="text-[10px] bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full font-bold">
                  ADMIN
                </span>
              )}
            </div>

            {/* Navigation Links */}
            <Link 
              href="/profil" 
              className="px-3 py-1.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-sm text-white hover:border-[#e94560] transition"
            >
              👤 Mon Profil
            </Link>
                        {/* Admin: Users Management */}
            {isAdmin && (
              <Link
                href="/admin/users"
                className="px-3 py-1.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-sm text-white hover:border-[#e94560] transition"
              >
                👥 Gestion des utilisateurs
              </Link>
            )}
            <Link 
              href="/reservations" 
              className="px-3 py-1.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-sm text-white hover:border-[#e94560] transition"
            >
              📅 Mes réservations
            </Link>

            <button
              onClick={logout}
              className="px-3 py-1.5 bg-[#2a2a4a] rounded-lg text-white hover:bg-[#3a3a5a] text-sm transition"
            >
              Déconnexion
            </button>
          </div>
        </div>

        {/* Admin hint banner */}
        {isAdmin && (
          <div className="mb-6 bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3 text-xs text-yellow-300">
            🛠️ Mode admin : les boutons <b>⚙️ Admin</b> ouvrent la console de
            contrôle locale (LAN uniquement). Assurez-vous d'être sur le réseau
            du centre.
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-500">Chargement…</div>
        ) : pcs.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            Aucun PC synchronisé pour le moment
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {pcs.map((pc) => (
              <div
                key={pc.pc_id}
                className="bg-[#1a1a2e] rounded-xl p-4 border border-[#2a2a4a] flex flex-col"
              >
                <div className="flex justify-between items-center mb-2">
                  <h2 className="text-lg font-bold text-white">{pc.name}</h2>
                  <span className={`text-sm ${stateColor[pc.state]}`}>
                    {stateEmoji[pc.state]} {pc.state}
                  </span>
                </div>

                <div className="text-xs text-gray-500 mb-3">
                  {pc.installed_games.length} jeu(x) installé(s)
                </div>

                <div className="flex flex-wrap gap-1 mb-3 max-h-20 overflow-y-auto">
                  {pc.installed_games.slice(0, 6).map((g, i) => (
                    <span
                      key={i}
                      className="text-xs bg-[#0f0f23] text-gray-300 px-2 py-1 rounded"
                    >
                      {toGameName(g)}
                    </span>
                  ))}
                  {pc.installed_games.length > 6 && (
                    <span className="text-xs text-gray-500">
                      +{pc.installed_games.length - 6}
                    </span>
                  )}
                </div>

                {/* Player action */}
                <Link
                  href={`/reservations/new?pc_id=${encodeURIComponent(pc.pc_id)}`}
                  className={`block text-center py-2 rounded-lg font-semibold transition ${
                    pc.state === 'available'
                      ? 'bg-[#e94560] text-white hover:bg-[#c73652]'
                      : 'bg-[#2a2a4a] text-gray-500 cursor-not-allowed'
                  }`}
                  onClick={(e) => pc.state !== 'available' && e.preventDefault()}
                >
                  {pc.state === 'available' ? 'Réserver' : 'Indisponible'}
                </Link>

                {/* Admin action */}
                {isAdmin && (
                  <Link
                    href={`/admin/pc/${encodeURIComponent(pc.pc_id)}`}
                    className="mt-2 block text-center py-1.5 rounded-lg text-xs font-semibold
                               bg-[#2a2a4a] text-yellow-400 hover:bg-[#3a3a5a] transition"
                  >
                    ⚙️ Admin
                  </Link>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}