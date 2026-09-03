// frontend/app/dashboard/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import Link from 'next/link';

interface PC {
  id: string;
  hostname: string;
  ip_address: string;
  online: boolean;
  in_session: boolean;
  game: string;
  cpu: number;
  ram: number;
  gpu: number;
  status: string;
  wallet_balance: number;
}

export default function Dashboard() {
  const router = useRouter();
  const [pcs, setPCs] = useState<PC[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [role, setRole] = useState<string>('player');
  const [stats, setStats] = useState({
    total: 0,
    online: 0,
    inSession: 0,
  });

  const isAdmin = role === 'admin' || role === 'staff';

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Get user info and role
    const userData = localStorage.getItem('user');
    const userRole = localStorage.getItem('role') || 'player';
    setRole(userRole);
    if (userData) {
      setUser(JSON.parse(userData));
    }

    fetchPCs();
    const interval = setInterval(fetchPCs, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchPCs = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/pcs`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        localStorage.removeItem('role');
        document.cookie = 'access_token=; path=/; max-age=0';
        document.cookie = 'role=; path=/; max-age=0';
        router.push('/login');
        return;
      }

      const data = await response.json();
      if (data.status === 'ok') {
        setPCs(data.pcs || []);
        const online = data.pcs.filter((p: PC) => p.online).length;
        const inSession = data.pcs.filter((p: PC) => p.in_session).length;
        setStats({
          total: data.pcs.length,
          online: online,
          inSession: inSession,
        });
      }
    } catch (error) {
      console.error('Failed to fetch PCs:', error);
      toast.error('Erreur de connexion au serveur');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    localStorage.removeItem('role');
    document.cookie = 'access_token=; path=/; max-age=0';
    document.cookie = 'role=; path=/; max-age=0';
    toast.success('Déconnecté avec succès');
    router.push('/login');
  };

  const getStatusColor = (pc: PC) => {
    if (!pc.online) return 'bg-red-500';
    if (pc.in_session) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStatusText = (pc: PC) => {
    if (!pc.online) return 'Hors ligne';
    if (pc.in_session) return 'En session';
    return 'Disponible';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0a0a1a]">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-t-[#e94560] border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin mx-auto"></div>
          <p className="mt-4 text-gray-400">Chargement...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#1a1a2e] to-[#16213e] rounded-2xl p-6 mb-8 border border-[#2a2a4a]">
          <div className="flex flex-wrap justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-[#e94560]">
                {isAdmin ? '🏢 Ninety Gaming House' : '🎮 Gaming Center'}
              </h1>
              <p className="text-gray-400 mt-1">
                {user?.full_name || user?.username || 'Player'}
                {isAdmin && ' (Admin)'}
              </p>
            </div>
            <div className="flex items-center gap-6">
              <div className="flex gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">{stats.total}</div>
                  <div className="text-xs text-gray-500">PCs</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">{stats.online}</div>
                  <div className="text-xs text-gray-500">En ligne</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-400">{stats.inSession}</div>
                  <div className="text-xs text-gray-500">Occupés</div>
                </div>
              </div>
              {!isAdmin && (
                <button
                  onClick={() => router.push('/reservations')}
                  className="px-4 py-2 bg-[#e94560] text-white rounded-lg hover:bg-[#c73652] transition"
                >
                  📅 Réservations
                </button>
              )}
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition"
              >
                Déconnexion
              </button>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-4 mb-6">
          <button
            onClick={fetchPCs}
            className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-white hover:bg-[#2a2a4a] transition"
          >
            🔄 Rafraîchir
          </button>
          <span className="text-gray-500 text-sm ml-auto flex items-center">
            {isAdmin ? '💡 Clique sur un PC pour les détails' : '💡 Statut des PCs en temps réel'}
          </span>
        </div>

        {/* PC Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {pcs.length === 0 ? (
            <div className="col-span-full text-center py-20 text-gray-500">
              <div className="text-6xl mb-4">🖥️</div>
              <h2 className="text-2xl">Aucun PC connecté</h2>
              <p className="mt-2">En attente des agents...</p>
            </div>
          ) : (
            pcs.map((pc) => {
              const isClickable = isAdmin;
              
              const cardContent = (
                <div
                  className={`bg-gradient-to-br from-[#1a1a2e] to-[#0f0f23] rounded-xl p-5 border-2 transition-all duration-300 ${
                    !pc.online ? 'border-red-500/50 opacity-50' :
                    pc.in_session ? 'border-yellow-500' :
                    'border-green-500/50'
                  } ${isClickable ? 'hover:transform hover:-translate-y-1 hover:shadow-lg hover:shadow-[#e94560]/10 cursor-pointer' : ''}`}
                >
                  <div className="flex justify-between items-start">
                    <span className={`w-3 h-3 rounded-full ${getStatusColor(pc)} inline-block`}></span>
                    <span className="text-xs text-gray-500 font-mono">
                      {pc.id?.substring(0, 8) || 'N/A'}
                    </span>
                  </div>
                  
                  <div className="mt-3">
                    <div className="text-lg font-semibold text-white truncate">
                      {pc.hostname || 'Unknown'}
                    </div>
                    <div className="text-sm text-yellow-400 truncate">
                      {pc.game && pc.game !== 'none' && isAdmin ? pc.game : '💤 IDLE'}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {getStatusText(pc)}
                      {pc.in_session && ' 🟡 SESSION'}
                    </div>
                  </div>
                  
                  {isAdmin ? (
                    <>
                      <div className="mt-3 pt-3 border-t border-[#1a1a2e] flex justify-between text-xs text-gray-400">
                        <span>CPU <span className="text-white">{pc.cpu || 0}%</span></span>
                        <span>RAM <span className="text-white">{pc.ram || 0}%</span></span>
                        <span>GPU <span className="text-white">{pc.gpu || 0}%</span></span>
                      </div>
                      <div className="text-xs text-gray-600 mt-2 flex justify-between">
                        <span>{pc.ip_address || 'N/A'}</span>
                        <span className="text-yellow-400">{pc.wallet_balance || 0}€</span>
                      </div>
                    </>
                  ) : (
                    <div className="mt-3 pt-3 border-t border-[#1a1a2e] text-center">
                      <span className={`text-xs font-semibold ${pc.in_session ? 'text-red-400' : 'text-green-400'}`}>
                        {pc.in_session ? '❌ Occupé' : '✅ Disponible'}
                      </span>
                    </div>
                  )}
                </div>
              );

              if (isClickable) {
                return (
                  <Link key={pc.id} href={`/pc/${pc.id}`}>
                    {cardContent}
                  </Link>
                );
              }
              
              return (
                <div key={pc.id}>
                  {cardContent}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}