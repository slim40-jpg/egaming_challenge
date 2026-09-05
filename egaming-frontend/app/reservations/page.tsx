// frontend/app/reservations/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import Link from 'next/link';
import { cloudGetMyReservations, cloudCancelReservation, cloudLogout } from '@/lib/api';

export default function ReservationsPage() {
  const router = useRouter();
  const [reservations, setReservations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    // Check cloud auth
    const token = localStorage.getItem('cloud_access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    const userData = localStorage.getItem('cloud_user');
    if (userData) {
      setUser(JSON.parse(userData));
    }

    fetchReservations();
    const interval = setInterval(fetchReservations, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchReservations = async () => {
    try {
      const data = await cloudGetMyReservations();
      setReservations(data);
    } catch (error) {
      console.error('Failed to fetch reservations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (reservationId: string) => {
    if (!confirm('Annuler cette réservation ?')) return;
    
    try {
      const result = await cloudCancelReservation(reservationId);
      if (result.status === 'ok') {
        toast.success('Réservation annulée');
        fetchReservations();
      } else {
        toast.error(result.message || 'Erreur');
      }
    } catch (error) {
      toast.error('Erreur lors de l\'annulation');
    }
  };

  const handleLogout = () => {
    cloudLogout();
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
              <h1 className="text-3xl font-bold text-[#e94560]">📋 Mes réservations</h1>
              <p className="text-gray-400 mt-1">
                {user?.full_name || user?.username || 'Player'}
              </p>
            </div>
            <div className="flex gap-4">
              <Link
                href="/dashboard"
                className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-white hover:bg-[#2a2a4a] transition"
              >
                ← Retour
              </Link>
              <Link
                href="/reservations/new"
                className="px-4 py-2 bg-[#e94560] text-white rounded-lg hover:bg-[#c73652] transition"
              >
                + Nouvelle réservation
              </Link>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition"
              >
                Déconnexion
              </button>
            </div>
          </div>
        </div>

        {/* Reservations List */}
        {reservations.length === 0 ? (
          <div className="bg-[#1a1a2e] rounded-xl p-12 text-center border border-[#2a2a4a]">
            <div className="text-6xl mb-4">📅</div>
            <h2 className="text-2xl text-gray-400">Aucune réservation</h2>
            <p className="text-gray-500 mt-2">Vous n'avez pas encore de réservations</p>
            <Link
              href="/reservations/new"
              className="inline-block mt-4 px-6 py-3 bg-[#e94560] text-white rounded-lg hover:bg-[#c73652] transition"
            >
              Réserver maintenant
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {reservations.map((res) => {
              const isPast = new Date(res.end_time) < new Date();
              const isActive = new Date(res.start_time) <= new Date() && new Date(res.end_time) >= new Date();
              
              return (
                <div
                  key={res.id}
                  className={`bg-[#1a1a2e] rounded-xl p-6 border-l-4 ${
                    res.status === 'cancelled' ? 'border-gray-500 opacity-50' :
                    isPast ? 'border-gray-500' :
                    isActive ? 'border-green-500' :
                    'border-yellow-500'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-sm text-gray-500">PC {res.pc_id}</div>
                      <div className="text-lg font-semibold text-white">{res.user_name}</div>
                      <div className="text-sm text-gray-400">
                        {new Date(res.start_time).toLocaleString('fr-FR')} - {new Date(res.end_time).toLocaleString('fr-FR')}
                      </div>
                      <div className="mt-1">
                        {res.status === 'cancelled' ? (
                          <span className="text-xs text-gray-500">❌ Annulée</span>
                        ) : isPast ? (
                          <span className="text-xs text-gray-400">✅ Terminée</span>
                        ) : isActive ? (
                          <span className="text-xs text-green-400">🟢 En cours</span>
                        ) : (
                          <span className="text-xs text-yellow-400">⏳ En attente</span>
                        )}
                      </div>
                    </div>
                    {res.status !== 'cancelled' && !isPast && (
                      <button
                        onClick={() => handleCancel(res.id)}
                        className="text-red-400 hover:text-red-300 text-sm font-medium"
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
  );
}