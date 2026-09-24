// app/pc/[id]/page.tsx

'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import Link from 'next/link';
import type { PC, Game } from '@/lib/types';
import React from 'react';

export default function PCDetail({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  
  // ✅ Déballer params avec React.use()
  const { id: pcId } = React.use(params);
  
  const [pc, setPC] = useState<PC | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [playerName, setPlayerName] = useState('Joueur');
  const [sessionTime, setSessionTime] = useState('00:00');
  const [sessionCost, setSessionCost] = useState(0);
  const [walletBalance, setWalletBalance] = useState(0);
  const [topupAmount, setTopupAmount] = useState(5);
  const [isAdmin, setIsAdmin] = useState(false);
  const [refreshingGames, setRefreshingGames] = useState(false);
  const timerInterval = useRef<NodeJS.Timeout | null>(null);
  const refreshInterval = useRef<NodeJS.Timeout | null>(null);

  // app/pc/[id]/page.tsx - Modifier le useEffect

  useEffect(() => {
    console.log('🔍 Params:', params);
    console.log('🔍 PC ID:', pcId);
  
    if (!pcId || pcId === 'undefined') {
       console.error('❌ Invalid PC ID');
       toast.error('ID du PC invalide');
       router.push('/dashboard');
       return;
    }

    const localToken = localStorage.getItem('access_token');
    const cloudToken = localStorage.getItem('cloud_access_token');
  
    if (!localToken && !cloudToken) {
      console.log('❌ No token found, redirecting to login');
      router.push('/login');
      return;
    }

  // ✅ VÉRIFIER LE USERNAME (admin OU cloud_username)
    const user = localStorage.getItem('username') || 
                   localStorage.getItem('cloud_user') || '';
    const cloud_user_json = JSON.parse(localStorage.getItem('cloud_user') || '{}');
    const isAdminUser = cloud_user_json.username === 'admin';
    console.log('🔑 Username:', cloud_user_json.username);
 
    if (!isAdminUser) {
      console.log('❌ User is not admin:', cloud_user_json.username);
      toast.error('Accès non autorisé. Cette page est réservée à l\'administrateur.');
      router.push('/dashboard');
      return;
    }
  
    setIsAdmin(true);
    console.log('✅ Admin access granted');

    fetchPCData();
    fetchGames();
    fetchWallet();
  
    refreshInterval.current = setInterval(() => {
      fetchPCData();
      fetchGamesSilently();
      fetchWallet();
    }, 5000);
  
    return () => {
      if (refreshInterval.current) clearInterval(refreshInterval.current);
      if (timerInterval.current) clearInterval(timerInterval.current);
    };
  }, [pcId]);

  const fetchPCData = async () => {
    if (!pcId || pcId === 'undefined') {
      console.error('❌ Cannot fetch PC data: invalid ID');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/pc/${pcId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        localStorage.removeItem('role');
        localStorage.removeItem('username');
        router.push('/login');
        return;
      }

      if (response.status === 404) {
        toast.error('PC non trouvé');
        router.push('/dashboard');
        return;
      }

      const data = await response.json();
      console.log('✅ PC Data received:', data);
      setPC(data);
      
      if (data.in_session && data.session) {
        const start = new Date(data.session.start_time);
        const now = new Date();
        const diff = Math.floor((now.getTime() - start.getTime()) / 1000);
        const mins = String(Math.floor(diff / 60)).padStart(2, '0');
        const secs = String(diff % 60).padStart(2, '0');
        setSessionTime(`${mins}:${secs}`);
        
        const cost = (diff / 60) * (data.session.price_per_minute || 0.10);
        setSessionCost(cost);
        
        if (!timerInterval.current) {
          timerInterval.current = setInterval(() => {
            setSessionTime(prev => {
              const parts = prev.split(':');
              let mins = parseInt(parts[0]);
              let secs = parseInt(parts[1]);
              secs++;
              if (secs >= 60) {
                secs = 0;
                mins++;
              }
              const newCost = ((mins * 60 + secs) / 60) * (pc?.session?.price_per_minute || 0.10);
              setSessionCost(newCost);
              return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            });
          }, 1000);
        }
      } else {
        if (timerInterval.current) {
          clearInterval(timerInterval.current);
          timerInterval.current = null;
        }
        setSessionTime('00:00');
        setSessionCost(0);
      }
    } catch (error) {
      console.error('Failed to fetch PC:', error);
      toast.error('Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  const fetchGames = async () => {
    if (!pcId || pcId === 'undefined') {
      console.error('❌ Cannot fetch games: invalid ID');
      return;
    }

    setRefreshingGames(true);
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/pc/${pcId}/games`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const data = await response.json();
      
      if (data.status === 'ok') {
        const gamesWithPaths = (data.games || []).map((game: any) => ({
          ...game,
          executable_path: game.executable_path || game.executable || '',
          shortcut_path: game.shortcut_path || game.shortcut || '',
        }));
        setGames(gamesWithPaths);
        console.log('🎮 Games loaded:', gamesWithPaths.length);
      }
    } catch (error) {
      console.error('Failed to fetch games:', error);
    } finally {
      setRefreshingGames(false);
    }
  };

  const fetchGamesSilently = async () => {
    if (!pcId || pcId === 'undefined') return;

    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/pc/${pcId}/games`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const data = await response.json();
      
      if (data.status === 'ok') {
        const gamesWithPaths = (data.games || []).map((game: any) => ({
          ...game,
          executable_path: game.executable_path || game.executable || '',
          shortcut_path: game.shortcut_path || game.shortcut || '',
        }));
        setGames(gamesWithPaths);
      }
    } catch (error) {
      // Silently fail for background refresh
    }
  };

  const fetchWallet = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/wallet`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (data.status === 'ok') {
        setWalletBalance(data.wallet?.balance || 0);
      }
    } catch (error) {
      console.error('Failed to fetch wallet:', error);
    }
  };

  const handleStartSession = async () => {
    if (!pcId || pcId === 'undefined') {
      toast.error('ID du PC invalide');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/session/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          pc_id: pcId,
          user_name: playerName,
        }),
      });
      
      const data = await response.json();
      if (data.status === 'ok') {
        toast.success(`Session démarrée pour ${playerName}`);
        fetchPCData();
        fetchWallet();
      } else {
        toast.error(data.message || 'Erreur');
      }
    } catch (error) {
      toast.error('Erreur lors du démarrage');
    }
  };

  const handleEndSession = async () => {
    if (!pcId || pcId === 'undefined') {
      toast.error('ID du PC invalide');
      return;
    }

    if (!confirm('Terminer la session ?')) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/session/end`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ pc_id: pcId }),
      });
      
      const data = await response.json();
      if (data.status === 'ok') {
        toast.success(`Session terminée - ${data.session.duration_minutes}m, ${data.session.cost.toFixed(2)}€`);
        if (timerInterval.current) {
          clearInterval(timerInterval.current);
          timerInterval.current = null;
        }
        fetchPCData();
        fetchWallet();
      } else {
        toast.error(data.message || 'Erreur');
      }
    } catch (error) {
      toast.error('Erreur lors de la fin');
    }
  };

  const handleCommand = async (command: string) => {
    if (!pcId || pcId === 'undefined') {
      toast.error('ID du PC invalide');
      return;
    }

    if (command === 'SHUTDOWN' && !confirm('⚠️ Éteindre ce PC ?')) return;
    if (command === 'RESTART' && !confirm('⚠️ Redémarrer ce PC ?')) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/command`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ pc_id: pcId, command: command }),
      });
      
      const data = await response.json();
      if (data.status === 'ok') {
        toast.success(`Commande "${command}" envoyée`);
      } else {
        toast.error(data.message || 'Erreur');
      }
    } catch (error) {
      toast.error('Erreur lors de l\'envoi');
    }
  };

  const handleTopup = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/wallet/topup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ amount: topupAmount }),
      });
      
      const data = await response.json();
      if (data.status === 'ok') {
        toast.success(`Wallet rechargé de ${topupAmount}€`);
        fetchWallet();
      } else {
        toast.error(data.message || 'Erreur');
      }
    } catch (error) {
      toast.error('Erreur lors du rechargement');
    }
  };

  const handleLaunchGame = async (game: Game) => {
    console.log('🎮 Launching game:', game);
    
    const executablePath = game.executable_path;
    
    if (!executablePath || executablePath === '' || executablePath === 'NO_PATH') {
      toast.error(`Chemin d'exécution manquant pour "${game.name}"`);
      return;
    }
    
    if (!executablePath.toLowerCase().includes('.exe')) {
      if (!confirm(`Le chemin "${executablePath}" ne semble pas être un fichier exe. Continuer quand même ?`)) {
        return;
      }
    }
    
    if (!confirm(`Lancer "${game.name}" ?`)) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8003';
      const response = await fetch(`${apiUrl}/api/games/launch-installed`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          pc_id: pcId,
          game_name: game.name,
          executable: executablePath,
          shortcut: game.shortcut_path || '',
        }),
      });
      
      const data = await response.json();
      
      if (data.status === 'ok') {
        toast.success(`Lancement de ${game.name}`);
        setTimeout(fetchGames, 3000);
      } else {
        toast.error(data.message || 'Erreur lors du lancement');
      }
    } catch (error) {
      console.error('❌ Launch error:', error);
      toast.error('Erreur lors du lancement');
    }
  };

  const getGameIcon = (gameName: string) => {
    const nameLower = gameName.toLowerCase();
    if (nameLower.includes('counter-strike') || nameLower.includes('csgo') || nameLower.includes('cs2')) return '🎯';
    if (nameLower.includes('valorant')) return '🔫';
    if (nameLower.includes('fortnite')) return '🎮';
    if (nameLower.includes('call of duty') || nameLower.includes('cod')) return '🔫';
    if (nameLower.includes('battlefield')) return '⚔️';
    if (nameLower.includes('overwatch')) return '🎯';
    if (nameLower.includes('apex')) return '🔫';
    if (nameLower.includes('destiny')) return '🌟';
    if (nameLower.includes('league of legends') || nameLower.includes('lol')) return '🏆';
    if (nameLower.includes('dota')) return '⚔️';
    if (nameLower.includes('fifa')) return '⚽';
    if (nameLower.includes('rocket league')) return '🚗';
    if (nameLower.includes('gta') || nameLower.includes('grand theft auto')) return '🚗';
    if (nameLower.includes('dragon ball') || nameLower.includes('dbz')) return '🐉';
    if (nameLower.includes('naruto')) return '🍥';
    if (nameLower.includes('mugen')) return '👊';
    if (nameLower.includes('unity')) return '🎮';
    if (nameLower.includes('minecraft')) return '⛏️';
    return '🎮';
  };

  if (loading || !pc) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0a0a1a]">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-t-[#e94560] border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin mx-auto"></div>
          <p className="mt-4 text-gray-400">Chargement...</p>
        </div>
      </div>
    );
  }

  const isOnline = pc.online;
  const isInSession = pc.in_session;
  const gameName = pc.game && pc.game !== 'none' ? pc.game : 'Aucun jeu';

  const gamesWithPaths = games.filter(g => g.executable_path && g.executable_path !== '');
  const gamesWithoutPaths = games.filter(g => !g.executable_path || g.executable_path === '');

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#1a1a2e] to-[#16213e] rounded-2xl p-6 mb-6 border border-[#2a2a4a]">
          <div className="flex flex-wrap justify-between items-center">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="p-2 hover:bg-[#2a2a4a] rounded-lg transition">
                ← Retour
              </Link>
              <div>
                <h1 className="text-2xl font-bold">
                  🖥️ <span className="text-white">{pc.hostname || 'Inconnu'}</span>
                </h1>
                <div className="flex gap-4 mt-1 text-sm">
                  <span className={isOnline ? 'text-green-400' : 'text-red-400'}>
                    ● {isOnline ? 'En ligne' : 'Hors ligne'}
                  </span>
                  {isInSession && <span className="text-yellow-400">🟡 En session</span>}
                  <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full text-xs">
                    🔐 ADMIN
                  </span>
                </div>
              </div>
            </div>
            <div className="flex gap-4 text-sm">
              <div>
                <span className="text-gray-500">Jeux: </span>
                <span className="text-white font-bold">{games.length}</span>
              </div>
              <div>
                <span className="text-gray-500">Wallet: </span>
                <span className="text-yellow-400 font-bold">{walletBalance || 0}€</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: PC Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Info Grid */}
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
              <h2 className="text-lg font-semibold text-[#e94560] mb-4">📊 Informations PC</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">Hostname</div>
                  <div className="text-sm text-white font-bold">{pc.hostname || '-'}</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">MAC</div>
                  <div className="text-sm text-white font-mono">{pc.mac_address || '-'}</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">IP</div>
                  <div className="text-sm text-white">{pc.ip_address || '-'}</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">🎮 Jeu</div>
                  <div className="text-sm text-[#e94560] font-bold">{gameName}</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">👤 Joueur</div>
                  <div className="text-sm text-white">
                    {isInSession && pc.session ? pc.session.user : 'Pas de session'}
                  </div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">⏱️ Session</div>
                  <div className="text-sm text-blue-400 font-bold">{sessionTime}</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">💻 CPU</div>
                  <div className="text-sm text-white">{pc.cpu}%</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">🧠 RAM</div>
                  <div className="text-sm text-white">{pc.ram}%</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">🎮 GPU</div>
                  <div className="text-sm text-white">{pc.gpu}%</div>
                </div>
              </div>
            </div>

            {/* Hardware */}
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
              <h2 className="text-lg font-semibold text-[#e94560] mb-4">🖥️ Matériel</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">Modèle CPU</div>
                  <div className="text-sm text-white truncate">{pc.hardware?.cpu || '-'}</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">Modèle GPU</div>
                  <div className="text-sm text-white truncate">{pc.hardware?.gpu || '-'}</div>
                </div>
                <div className="bg-[#0f0f23] p-3 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase">RAM</div>
                  <div className="text-sm text-white">{pc.hardware?.ram || '-'}</div>
                </div>
              </div>
            </div>

            {/* Games */}
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-[#e94560]">🎮 Jeux installés</h2>
                <button
                  onClick={fetchGames}
                  disabled={refreshingGames}
                  className="p-2 hover:bg-[#2a2a4a] rounded-lg transition disabled:opacity-50"
                >
                  {refreshingGames ? '⏳' : '🔄'}
                </button>
              </div>
              
              {games.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-2">🎮</div>
                  <p>Aucun jeu détecté</p>
                  <button
                    onClick={fetchGames}
                    className="mt-4 px-4 py-2 bg-[#e94560] text-white rounded-lg hover:bg-[#c73652] transition"
                  >
                    🔄 Scanner les jeux
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 max-h-[400px] overflow-y-auto pr-2">
                  {games.map((game, index) => {
                    const hasPath = !!(game.executable_path && game.executable_path !== '');
                    const icon = getGameIcon(game.name);
                    
                    return (
                      <div
                        key={index}
                        onClick={() => hasPath ? handleLaunchGame(game) : toast.error('Chemin d\'exécution manquant')}
                        className={`bg-[#0f0f23] rounded-xl p-4 text-center transition-all hover:transform hover:-translate-y-1 border-2 ${
                          game.is_running ? 'border-green-500' : 
                          hasPath ? 'border-[#2a2a4a] hover:border-[#e94560] cursor-pointer' : 
                          'border-red-500/50 opacity-60 cursor-not-allowed'
                        }`}
                      >
                        <div className="text-3xl mb-1">{icon}</div>
                        <div className="text-sm font-semibold text-white truncate" title={game.name}>
                          {game.name}
                        </div>
                        <div className="text-xs text-gray-500">{game.platform || 'standalone'}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right: Controls */}
          <div className="space-y-6">
            {/* Wallet */}
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
              <h2 className="text-lg font-semibold text-[#e94560] mb-4">💰 Portefeuille</h2>
              <div className="text-center mb-4">
                <div className="text-3xl font-bold text-yellow-400">{walletBalance || 0}€</div>
                <div className="text-xs text-gray-500">Solde disponible</div>
              </div>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={topupAmount}
                  onChange={(e) => setTopupAmount(parseInt(e.target.value) || 0)}
                  className="flex-1 bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-3 py-2 text-white focus:border-[#e94560] focus:outline-none"
                  min="1"
                />
                <button
                  onClick={handleTopup}
                  className="bg-[#e94560] text-white px-4 py-2 rounded-lg hover:bg-[#c73652] transition"
                >
                  + Recharger
                </button>
              </div>
            </div>

            {/* Session Controls */}
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
              <h2 className="text-lg font-semibold text-[#e94560] mb-4">🎮 Session</h2>
              
              {isInSession ? (
                <>
                  <div className="bg-[#0f0f23] rounded-lg p-4 mb-4 border-l-2 border-yellow-500">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">🎮 Jeu</span>
                      <span className="text-white">{pc.session?.game || 'Inconnu'}</span>
                    </div>
                    <div className="flex justify-between text-sm mt-1">
                      <span className="text-gray-500">👤 Joueur</span>
                      <span className="text-white">{pc.session?.user || 'Inconnu'}</span>
                    </div>
                    <div className="flex justify-between text-sm mt-1">
                      <span className="text-gray-500">⏱️ Durée</span>
                      <span className="text-blue-400 font-bold">{sessionTime}</span>
                    </div>
                    <div className="flex justify-between text-sm mt-1">
                      <span className="text-gray-500">💵 Coût</span>
                      <span className="text-yellow-400 font-bold">{sessionCost.toFixed(2)}€</span>
                    </div>
                  </div>
                  <button
                    onClick={handleEndSession}
                    className="w-full bg-red-500 text-white py-2 rounded-lg hover:bg-red-600 transition font-semibold"
                  >
                    ⏹ Terminer la session
                  </button>
                </>
              ) : (
                <>
                  <div className="bg-[#0f0f23] rounded-lg p-4 mb-4 text-center">
                    <div className="text-yellow-400 text-sm font-semibold">
                      💰 0.10€ / minute
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Solde: {walletBalance || 0}€
                    </div>
                    {walletBalance < 1 && (
                      <div className="text-xs text-red-400 mt-1">
                        ⚠️ Solde insuffisant (min 1€)
                      </div>
                    )}
                  </div>
                  <input
                    type="text"
                    value={playerName}
                    onChange={(e) => setPlayerName(e.target.value)}
                    placeholder="Nom du joueur"
                    className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none mb-3"
                  />
                  <button
                    onClick={handleStartSession}
                    disabled={walletBalance < 1}
                    className="w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    ▶ Démarrer la session
                  </button>
                </>
              )}
            </div>

            {/* Remote Controls */}
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
              <h2 className="text-lg font-semibold text-[#e94560] mb-4">🔧 Contrôles Admin</h2>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleCommand('LOCK')}
                  className="bg-yellow-500 text-black py-2 rounded-lg hover:bg-yellow-600 transition font-semibold"
                >
                  🔒 Verrouiller
                </button>
                <button
                  onClick={() => handleCommand('RESTART')}
                  className="bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 transition font-semibold"
                >
                  🔄 Redémarrer
                </button>
                <button
                  onClick={() => handleCommand('SHUTDOWN')}
                  className="bg-red-500 text-white py-2 rounded-lg hover:bg-red-600 transition font-semibold col-span-2"
                >
                  ⏻ Éteindre
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}