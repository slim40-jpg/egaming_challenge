// frontend/app/reservations/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import Link from 'next/link';

interface PC {
  id: string;
  hostname: string;
  online: boolean;
  in_session: boolean;
}

interface Reservation {
  id: string;
  pc_id: string;
  user_name: string;
  start_time: string;
  end_time: string;
  status: string;
}

export default function ReservationsPage() {
  const router = useRouter();
  const [pcs, setPCs] = useState<PC[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  
  // Reservation form
  const [selectedPC, setSelectedPC] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [userName, setUserName] = useState('');

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Check role - only players can access this page
    const role = localStorage.getItem('role') || 'player';
    if (role === 'admin' || role === 'staff') {
      router.push('/dashboard');
      return;
    }

    // Get user info
    const userData = localStorage.getItem('user');
    if (userData) {
      const parsed = JSON.parse(userData);
      setUser(parsed);
      setUserName(parsed.full_name || parsed.username || '');
    }

    fetchPCs();
    fetchReservations();
    const interval = setInterval(() => {
      fetchPCs();
      fetchReservations();
    }, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchPCs = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/pcs`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const data = await response.json();
      if (data.status === 'ok') {
        setPCs(data.pcs || []);
      }
    } catch (error) {
      console.error('Failed to fetch PCs:', error);
    }
  };

  const fetchReservations = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/reservations`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const data = await response.json();
      if (data.status === 'ok') {
        setReservations(data.reservations || []);
      }
    } catch (error) {
      console.error('Failed to fetch reservations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateReservation = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedPC || !startTime || !endTime) {
      toast.error('Veuillez remplir tous les champs');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/reservations/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          pc_id: selectedPC,
          start_time: startTime,
          end_time: endTime,
          user_name: userName || 'Player',
        }),
      });
      
      const data = await response.json();
      if (data.status === 'ok') {
        toast.success('Réservation créée avec succès!');
        fetchReservations();
        setSelectedPC('');
        setStartTime('');
        setEndTime('');
      } else {
        toast.error(data.message || 'Erreur');
      }
    } catch (error) {
      toast.error('Erreur lors de la création');
    }
  };

  const handleCancelReservation = async (reservationId: string) => {
    if (!confirm('Annuler cette réservation ?')) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/reservations/${reservationId}/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      const data = await response.json();
      if (data.status === 'ok') {
        toast.success('Réservation annulée');
        fetchReservations();
      } else {
        toast.error(data.message || 'Erreur');
      }
    } catch (error) {
      toast.error('Erreur lors de l\'annulation');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    localStorage.removeItem('role');
    document.cookie = 'access_token=; path=/; max-age=0';
    document.cookie = 'role=; path=/; max-age=0';
    toast.success('Déconnecté');
    router.push('/login');
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
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#1a1a2e] to-[#16213e] rounded-2xl p-6 mb-8 border border-[#2a2a4a]">
          <div className="flex flex-wrap justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-[#e94560]">
                🎮 Réservations
              </h1>
              <p className="text-gray-400 mt-1">
                {user?.full_name || user?.username || 'Player'}
              </p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => router.push('/dashboard')}
                className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-white hover:bg-[#2a2a4a] transition"
              >
                📊 Voir les PCs
              </button>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition"
              >
                Déconnexion
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Create Reservation */}
          <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
            <h2 className="text-lg font-semibold text-[#e94560] mb-4">📅 Nouvelle Réservation</h2>
            <form onSubmit={handleCreateReservation} className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm font-medium mb-1">
                  PC
                </label>
                <select
                  value={selectedPC}
                  onChange={(e) => setSelectedPC(e.target.value)}
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                  required
                >
                  <option value="">Sélectionner un PC</option>
                  {pcs.map((pc) => (
                    <option key={pc.id} value={pc.id}>
                      {pc.hostname} {pc.in_session ? '(Occupé)' : pc.online ? '(🟢)' : '(🔴)'}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-gray-400 text-sm font-medium mb-1">
                  Nom du joueur
                </label>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none transition"
                  placeholder="Votre nom"
                  required
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm font-medium mb-1">
                  Début
                </label>
                <input
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                  required
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm font-medium mb-1">
                  Fin
                </label>
                <input
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full bg-[#e94560] text-white py-3 rounded-lg font-semibold hover:bg-[#c73652] transition"
              >
                Réserver
              </button>
            </form>
          </div>

          {/* My Reservations */}
          <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
            <h2 className="text-lg font-semibold text-[#e94560] mb-4">📋 Mes Réservations</h2>
            {reservations.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">📅</div>
                <p>Aucune réservation</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                {reservations.map((res) => {
                  const pc = pcs.find(p => p.id === res.pc_id);
                  const isPast = new Date(res.end_time) < new Date();
                  const isActive = new Date(res.start_time) <= new Date() && new Date(res.end_time) >= new Date();
                  
                  return (
                    <div
                      key={res.id}
                      className={`bg-[#0f0f23] rounded-lg p-4 border-l-4 ${
                        res.status === 'cancelled' ? 'border-gray-500 opacity-50' :
                        isPast ? 'border-gray-500' :
                        isActive ? 'border-green-500' :
                        'border-yellow-500'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-semibold text-white">
                            {pc?.hostname || 'PC Inconnu'}
                          </div>
                          <div className="text-sm text-gray-400">
                            {res.user_name}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {new Date(res.start_time).toLocaleString()} - {new Date(res.end_time).toLocaleString()}
                          </div>
                          <div className="text-xs mt-1">
                            {res.status === 'cancelled' ? (
                              <span className="text-gray-500">❌ Annulée</span>
                            ) : isPast ? (
                              <span className="text-gray-400">✅ Terminée</span>
                            ) : isActive ? (
                              <span className="text-green-400">🟢 En cours</span>
                            ) : (
                              <span className="text-yellow-400">⏳ En attente</span>
                            )}
                          </div>
                        </div>
                        {res.status !== 'cancelled' && !isPast && (
                          <button
                            onClick={() => handleCancelReservation(res.id)}
                            className="text-red-400 hover:text-red-300 text-sm"
                          >
                            Annuler
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Available PCs Status */}
        <div className="mt-6 bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
          <h2 className="text-lg font-semibold text-[#e94560] mb-4">🖥️ Statut des PCs</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {pcs.map((pc) => (
              <div
                key={pc.id}
                className={`bg-[#0f0f23] rounded-lg p-3 text-center border-2 ${
                  !pc.online ? 'border-red-500/30 opacity-50' :
                  pc.in_session ? 'border-yellow-500' :
                  'border-green-500/50'
                }`}
              >
                <div className="text-xs font-mono text-gray-500">{pc.id.substring(0, 6)}</div>
                <div className="text-sm font-semibold text-white truncate">{pc.hostname}</div>
                <div className="text-xs mt-1">
                  {!pc.online ? '🔴' : pc.in_session ? '🟡' : '🟢'}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {!pc.online ? 'Hors ligne' : pc.in_session ? 'Occupé' : 'Disponible'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}