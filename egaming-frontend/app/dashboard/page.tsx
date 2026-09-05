
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import {
  cloudGetPCs,
  cloudGetMyReservations,
  cloudLogout,
} from '@/lib/api';

interface PC {
  id: string;
  hostname?: string;
  status?: string;
}

interface Reservation {
  id: string;
  pc_id?: string;
  pc_hostname?: string;
  start_time?: string;
  end_time?: string;
  status?: string;
}

export default function Dashboard() {
  const router = useRouter();

  const [pcs, setPCs] = useState<PC[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // ============================================================
  // AUTH + INITIAL LOAD
  // ============================================================

  useEffect(() => {
    const token = localStorage.getItem('cloud_access_token');

    console.log(
      '🔑 Token:',
      token ? `${token.substring(0, 30)}...` : 'No token'
    );

    if (!token) {
      router.push('/login');
      return;
    }

    // Load logged-in user
    const userData = localStorage.getItem('cloud_user');

    if (userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (error) {
        console.error('Invalid user data:', error);
      }
    }

    fetchData();

    // Refresh dashboard every 10 seconds
    const interval = setInterval(() => {
      fetchData(true);
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // ============================================================
  // FETCH DATA
  // ============================================================

  const fetchData = async (silent = false) => {
    try {
      if (silent) {
        setRefreshing(true);
      }

      const token = localStorage.getItem('cloud_access_token');

      if (!token) {
        router.push('/login');
        return;
      }

      console.log('🔄 Fetching dashboard data...');

      const [pcsData, reservationsData] = await Promise.all([
        cloudGetPCs(),
        cloudGetMyReservations(),
      ]);

      console.log('✅ PCs:', pcsData);
      console.log('✅ Reservations:', reservationsData);

      setPCs(Array.isArray(pcsData) ? pcsData : []);
      setReservations(
        Array.isArray(reservationsData) ? reservationsData : []
      );
    } catch (error: any) {
      console.error('❌ Dashboard error:', error);

      if (error?.response?.status === 401) {
        localStorage.removeItem('cloud_access_token');
        localStorage.removeItem('cloud_user');

        toast.error('Session expirée');

        router.push('/login');
        return;
      }

      if (!silent) {
        toast.error('Erreur de chargement des données');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // ============================================================
  // LOGOUT
  // ============================================================

  const handleLogout = async () => {
    try {
      await cloudLogout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('cloud_access_token');
      localStorage.removeItem('cloud_user');

      toast.success('Déconnecté');

      router.push('/login');
    }
  };

  // ============================================================
  // STATISTICS
  // ============================================================

  const onlinePCs = pcs.filter(
    (pc) => pc.status?.toLowerCase() === 'online'
  ).length;

  const offlinePCs = pcs.length - onlinePCs;

  const activeReservations = reservations.filter((reservation) => {
    const status = reservation.status?.toLowerCase();

    return (
      status === 'confirmed' ||
      status === 'accepted' ||
      status === 'pending' ||
      status === 'active'
    );
  }).length;

  // ============================================================
  // LOADING SCREEN
  // ============================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a1a] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#2a2a4a] border-t-[#e94560] rounded-full animate-spin mx-auto" />

          <p className="mt-5 text-gray-400">
            Chargement du Gaming Center...
          </p>
        </div>
      </div>
    );
  }

  // ============================================================
  // DASHBOARD
  // ============================================================

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">

        {/* =====================================================
            HEADER
        ===================================================== */}

        <header className="bg-gradient-to-r from-[#1a1a2e] to-[#16213e] rounded-2xl border border-[#2a2a4a] p-6 mb-8 shadow-xl">

          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">

            {/* Logo / User */}
            <div>
              <div className="flex items-center gap-3">
                <div className="text-4xl">
                  🎮
                </div>

                <div>
                  <h1 className="text-3xl font-bold text-[#e94560]">
                    Gaming Center
                  </h1>

                  <p className="text-gray-400 text-sm">
                    Bienvenue,{' '}
                    <span className="text-white font-medium">
                      {user?.full_name ||
                        user?.username ||
                        'Player'}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            {/* Header actions */}
            <div className="flex flex-wrap items-center gap-3">

              {/* Refresh */}
              <button
                onClick={() => fetchData(true)}
                disabled={refreshing}
                className="px-4 py-2 rounded-lg bg-white/5 border border-[#2a2a4a] hover:bg-white/10 transition disabled:opacity-50"
              >
                {refreshing ? '⟳ Actualisation...' : '🔄 Actualiser'}
              </button>

              {/* Reservations */}
              <Link
                href="/reservations"
                className="px-4 py-2 rounded-lg bg-[#e94560] hover:bg-[#c73652] transition font-medium"
              >
                📅 Mes réservations
              </Link>

              {/* Logout */}
              <button
                onClick={handleLogout}
                className="px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition"
              >
                Déconnexion
              </button>

            </div>
          </div>
        </header>

        {/* =====================================================
            STATISTICS
        ===================================================== */}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">

          {/* Total PCs */}
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">
                  Total PCs
                </p>

                <p className="text-3xl font-bold mt-1">
                  {pcs.length}
                </p>
              </div>

              <div className="text-3xl">
                🖥️
              </div>
            </div>
          </div>

          {/* Online PCs */}
          <div className="bg-[#1a1a2e] border border-green-500/20 rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">
                  PCs disponibles
                </p>

                <p className="text-3xl font-bold text-green-400 mt-1">
                  {onlinePCs}
                </p>
              </div>

              <div className="w-4 h-4 bg-green-500 rounded-full shadow-lg shadow-green-500/30" />
            </div>
          </div>

          {/* Offline PCs */}
          <div className="bg-[#1a1a2e] border border-red-500/20 rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">
                  PCs hors ligne
                </p>

                <p className="text-3xl font-bold text-red-400 mt-1">
                  {offlinePCs}
                </p>
              </div>

              <div className="w-4 h-4 bg-red-500 rounded-full" />
            </div>
          </div>

          {/* Reservations */}
          <div className="bg-[#1a1a2e] border border-yellow-500/20 rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">
                  Mes réservations
                </p>

                <p className="text-3xl font-bold text-yellow-400 mt-1">
                  {activeReservations}
                </p>
              </div>

              <div className="text-3xl">
                📅
              </div>
            </div>
          </div>

        </div>

        {/* =====================================================
            PC STATUS
        ===================================================== */}

        <section className="mb-8">

          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold">
                🖥️ État des PCs
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                Disponibilité en temps réel
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span
                className={`w-2 h-2 rounded-full ${
                  refreshing
                    ? 'bg-yellow-400 animate-pulse'
                    : 'bg-green-500'
                }`}
              />

              {refreshing
                ? 'Actualisation...'
                : 'Synchronisé'}
            </div>
          </div>

          {pcs.length === 0 ? (

            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-xl text-center py-20">

              <div className="text-6xl mb-5">
                🖥️
              </div>

              <h3 className="text-xl font-semibold">
                Aucun PC disponible
              </h3>

              <p className="text-gray-500 mt-2">
                Les PCs du Gaming Center apparaîtront ici.
              </p>

            </div>

          ) : (

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">

              {pcs.map((pc) => {

                const isOnline =
                  pc.status?.toLowerCase() === 'online';

                return (
                  <div
                    key={pc.id}
                    className={`relative overflow-hidden bg-gradient-to-br from-[#1a1a2e] to-[#0f0f23] rounded-xl p-5 border transition-all duration-200 ${
                      isOnline
                        ? 'border-green-500/30 hover:border-green-500/60'
                        : 'border-red-500/20 opacity-70'
                    }`}
                  >

                    {/* Status indicator */}
                    <div className="flex justify-between items-center">

                      <div className="flex items-center gap-2">

                        <span
                          className={`w-3 h-3 rounded-full ${
                            isOnline
                              ? 'bg-green-500 shadow-lg shadow-green-500/40'
                              : 'bg-red-500'
                          }`}
                        />

                        <span
                          className={`text-xs font-medium ${
                            isOnline
                              ? 'text-green-400'
                              : 'text-red-400'
                          }`}
                        >
                          {isOnline
                            ? 'ONLINE'
                            : 'OFFLINE'}
                        </span>

                      </div>

                      <span className="text-xs text-gray-600 font-mono">
                        {pc.id
                          ? pc.id.substring(0, 8)
                          : 'N/A'}
                      </span>

                    </div>

                    {/* PC */}
                    <div className="mt-5">

                      <div className="flex items-center gap-3">

                        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center text-2xl">
                          🖥️
                        </div>

                        <div className="min-w-0">

                          <h3 className="font-semibold text-white truncate">
                            {pc.hostname || 'Unknown PC'}
                          </h3>

                          <p className="text-sm text-gray-500 mt-1">
                            Gaming Station
                          </p>

                        </div>

                      </div>

                    </div>

                    {/* Availability */}
                    <div
                      className={`mt-5 rounded-lg px-3 py-2 text-sm ${
                        isOnline
                          ? 'bg-green-500/10 text-green-400'
                          : 'bg-red-500/10 text-red-400'
                      }`}
                    >
                      {isOnline
                        ? '🟢 Disponible pour réservation'
                        : '🔴 PC hors ligne'}
                    </div>

                  </div>
                );
              })}

            </div>
          )}

        </section>

        {/* =====================================================
            RESERVATIONS
        ===================================================== */}

        <section className="mb-8">

          <div className="flex items-center justify-between mb-4">

            <div>
              <h2 className="text-xl font-bold">
                📅 Mes réservations
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                Vos dernières réservations
              </p>
            </div>

            <Link
              href="/reservations"
              className="text-sm text-[#e94560] hover:text-[#ff6078] transition"
            >
              Voir toutes →
            </Link>

          </div>

          {reservations.length === 0 ? (

            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-xl p-8 text-center">

              <div className="text-4xl mb-3">
                📅
              </div>

              <h3 className="font-semibold">
                Aucune réservation
              </h3>

              <p className="text-gray-500 text-sm mt-2">
                Vous n'avez pas encore effectué de réservation.
              </p>

              <Link
                href="/reservations/new"
                className="inline-block mt-5 px-5 py-2.5 bg-[#e94560] hover:bg-[#c73652] rounded-lg transition font-medium"
              >
                + Nouvelle réservation
              </Link>

            </div>

          ) : (

            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-xl overflow-hidden">

              <div className="divide-y divide-[#2a2a4a]">

                {reservations.slice(0, 5).map((reservation) => (

                  <div
                    key={reservation.id}
                    className="p-5 hover:bg-white/[0.02] transition"
                  >

                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

                      {/* Reservation info */}
                      <div className="flex items-center gap-4">

                        <div className="w-11 h-11 rounded-lg bg-[#e94560]/10 flex items-center justify-center">
                          🖥️
                        </div>

                        <div>

                          <p className="font-semibold">
                            {reservation.pc_hostname ||
                              reservation.pc_id ||
                              'PC'}
                          </p>

                          <p className="text-sm text-gray-500 mt-1">

                            {reservation.start_time
                              ? new Date(
                                  reservation.start_time
                                ).toLocaleString('fr-FR')
                              : 'Date inconnue'}

                            {reservation.end_time && (
                              <>
                                {' → '}
                                {new Date(
                                  reservation.end_time
                                ).toLocaleString('fr-FR')}
                              </>
                            )}

                          </p>

                        </div>

                      </div>

                      {/* Status */}
                      <div>

                        <span
                          className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${
                            reservation.status?.toLowerCase() ===
                              'confirmed' ||
                            reservation.status?.toLowerCase() ===
                              'accepted'
                              ? 'bg-green-500/10 text-green-400'
                              : reservation.status?.toLowerCase() ===
                                'pending'
                              ? 'bg-yellow-500/10 text-yellow-400'
                              : reservation.status?.toLowerCase() ===
                                'cancelled'
                              ? 'bg-red-500/10 text-red-400'
                              : 'bg-gray-500/10 text-gray-400'
                          }`}
                        >
                          {reservation.status ||
                            'Inconnu'}
                        </span>

                      </div>

                    </div>

                  </div>

                ))}

              </div>

            </div>

          )}

        </section>

        {/* =====================================================
            QUICK ACTIONS
        ===================================================== */}

        <section className="bg-gradient-to-r from-[#1a1a2e] to-[#16213e] border border-[#2a2a4a] rounded-xl p-6">

          <h2 className="text-lg font-semibold text-[#e94560] mb-5">
            🚀 Actions rapides
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

            <Link
              href="/reservations/new"
              className="group p-5 rounded-xl bg-[#e94560] hover:bg-[#c73652] transition"
            >
              <div className="text-2xl mb-3">
                📅
              </div>

              <h3 className="font-semibold">
                Nouvelle réservation
              </h3>

              <p className="text-sm text-white/70 mt-1">
                Réserver un PC pour une session
              </p>
            </Link>

            <Link
              href="/reservations"
              className="group p-5 rounded-xl bg-white/5 border border-[#2a2a4a] hover:bg-white/10 transition"
            >
              <div className="text-2xl mb-3">
                📋
              </div>

              <h3 className="font-semibold">
                Mes réservations
              </h3>

              <p className="text-sm text-gray-500 mt-1">
                Consulter et gérer vos réservations
              </p>
            </Link>

            <button
              onClick={() => fetchData()}
              className="text-left group p-5 rounded-xl bg-white/5 border border-[#2a2a4a] hover:bg-white/10 transition"
            >
              <div className="text-2xl mb-3">
                🔄
              </div>

              <h3 className="font-semibold">
                Actualiser
              </h3>

              <p className="text-sm text-gray-500 mt-1">
                Mettre à jour l'état des PCs
              </p>
            </button>

          </div>

        </section>

        {/* Footer */}
        <footer className="text-center text-xs text-gray-600 py-8">
          Gaming Center • Dashboard
        </footer>

      </div>
    </div>
  );
}

