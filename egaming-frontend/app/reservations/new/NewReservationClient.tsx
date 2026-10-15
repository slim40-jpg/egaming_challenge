// app/reservations/new/NewReservationClient.tsx

'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cloud, getAuthToken } from '@/lib/api';

type PCMirror = {
  pc_id: string;
  name: string;
  online: boolean;
  state: 'available' | 'reserved' | 'in_session' | 'offline' | 'maintenance';
  installed_games: Array<string | { name: string }>;
};

const toGameName = (g: PCMirror['installed_games'][number]): string =>
  typeof g === 'string' ? g : (g?.name ?? '');

export default function NewReservationPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedPcId = searchParams.get('pc_id') || '';

  const [pcs, setPCs] = useState<PCMirror[]>([]);
  const [loading, setLoading] = useState(false);
  const [walletBalance, setWalletBalance] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    pc_id: preselectedPcId,
    start_time: '',
    end_time: '',
    center_id: 'main',
  });

  useEffect(() => {
    if (!getAuthToken()) {
      router.replace('/login');
      return;
    }
    fetchPCs();
    fetchWallet();
  }, [router]);

  const fetchPCs = async () => {
    try {
      const res = await cloud.listPCs('main');
      setPCs(res.data?.pcs || []);
    } catch (error: any) {
      console.error('Failed to fetch PCs:', error);
      toast.error('Erreur de chargement des PCs');
    }
  };

  const fetchWallet = async () => {
    try {
      const res = await cloud.getWallet();
      setWalletBalance(res.data?.wallet?.balance ?? 0);
    } catch (error: any) {
      console.error('Failed to fetch wallet:', error);
    }
  };

  // Compute duration in minutes for a live estimate
  const durationMinutes = (() => {
    if (!formData.start_time || !formData.end_time) return 0;
    const s = new Date(formData.start_time).getTime();
    const e = new Date(formData.end_time).getTime();
    if (isNaN(s) || isNaN(e) || e <= s) return 0;
    return Math.floor((e - s) / 60000);
  })();

  const estimatedCost = parseFloat((durationMinutes * 0.10).toFixed(2));
  const hasEnoughFunds =
    walletBalance !== null && walletBalance >= estimatedCost;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (!formData.pc_id) {
        toast.error('Sélectionnez un PC');
        setLoading(false);
        return;
      }
      if (durationMinutes < 30) {
        toast.error('Durée minimum : 30 minutes');
        setLoading(false);
        return;
      }

      if (!hasEnoughFunds) {
        toast.error(
          `Solde insuffisant : ${estimatedCost.toFixed(2)} TND requis, ${(
            walletBalance ?? 0
          ).toFixed(2)} TND disponibles`
        );
        setLoading(false);
        return;
      }

      // Book & pay in one atomic operation
      const res = await cloud.bookAndPay(
        formData.pc_id,
        formData.start_time,
        formData.end_time
      );

      if (res.data?.status === 'ok') {
        const pay = res.data.payment;
        toast.success(
          `✅ Réservation payée — ${pay.final_cost.toFixed(2)} TND débités. Nouveau solde : ${pay.new_balance.toFixed(2)} TND`
        );
        router.push('/reservations');
      } else {
        toast.error(res.data?.message || 'Erreur de création');
      }
    } catch (error: any) {
      console.error('Book-and-pay error:', error);
      const status = error?.response?.status;
      const data = error?.response?.data;
      if (status === 402) {
        toast.error(
          `Fonds insuffisants. Il manque ${data?.missing?.toFixed(2) ?? '?'} TND.`
        );
      } else if (status === 409) {
        toast.error('Ce créneau est déjà réservé.');
      } else {
        toast.error(
          data?.error || data?.message || 'Erreur lors de la réservation'
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#1a1a2e] to-[#16213e] rounded-2xl p-6 mb-8 border border-[#2a2a4a]">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-[#e94560]">
              📅 Nouvelle réservation
            </h1>
            <Link
              href="/dashboard"
              className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-white hover:bg-[#2a2a4a] transition"
            >
              ← Retour
            </Link>
          </div>
        </div>

        <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* PC selector */}
            <div>
              <label className="block text-gray-400 text-sm font-medium mb-1">
                PC *
              </label>
              <select
                value={formData.pc_id}
                onChange={(e) =>
                  setFormData({ ...formData, pc_id: e.target.value })
                }
                className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                required
              >
                <option value="">Sélectionner un PC</option>
                {pcs.map((pc) => {
                  const stateEmoji =
                    pc.state === 'available'
                      ? '🟢'
                      : pc.state === 'reserved'
                      ? '🟡'
                      : pc.state === 'in_session'
                      ? '🔴'
                      : pc.state === 'maintenance'
                      ? '🔧'
                      : '⚫';
                  return (
                    <option
                      key={pc.pc_id}
                      value={pc.pc_id}
                      disabled={pc.state !== 'available'}
                    >
                      {pc.name} {stateEmoji}
                      {pc.state !== 'available' ? ` (${pc.state})` : ''}
                    </option>
                  );
                })}
              </select>

              {/* Preview of games for selected PC */}
              {formData.pc_id && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {(
                    pcs.find((p) => p.pc_id === formData.pc_id)
                      ?.installed_games || []
                  )
                    .slice(0, 8)
                    .map((g, i) => (
                      <span
                        key={i}
                        className="text-xs bg-[#0f0f23] text-gray-400 px-2 py-0.5 rounded"
                      >
                        {toGameName(g)}
                      </span>
                    ))}
                </div>
              )}
            </div>

            {/* Start */}
            <div>
              <label className="block text-gray-400 text-sm font-medium mb-1">
                Début *
              </label>
              <input
                type="datetime-local"
                value={formData.start_time}
                onChange={(e) =>
                  setFormData({ ...formData, start_time: e.target.value })
                }
                className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                required
              />
            </div>

            {/* End */}
            <div>
              <label className="block text-gray-400 text-sm font-medium mb-1">
                Fin *
              </label>
              <input
                type="datetime-local"
                value={formData.end_time}
                onChange={(e) =>
                  setFormData({ ...formData, end_time: e.target.value })
                }
                className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                required
              />
            </div>

            {/* Estimate + wallet */}
            <div className="bg-[#0f0f23] rounded-lg p-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Tarif</span>
                <span className="text-yellow-400 font-bold">0.10 dt / min</span>
              </div>
              <div className="flex justify-between text-sm mt-1">
                <span className="text-gray-500">Durée</span>
                <span className="text-white font-bold">
                  {durationMinutes > 0 ? `${durationMinutes} min` : '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm mt-1">
                <span className="text-gray-500">Total à payer</span>
                <span className="text-[#e94560] font-bold">
                  {durationMinutes > 0 ? `${estimatedCost.toFixed(2)} TND` : '—'}
                </span>
              </div>
              <div className="flex justify-between text-sm mt-1 pt-2 border-t border-[#2a2a4a]">
                <span className="text-gray-500">Votre solde</span>
                <span
                  className={`font-bold ${
                    hasEnoughFunds ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {walletBalance !== null
                    ? `${walletBalance.toFixed(2)} TND`
                    : '…'}
                </span>
              </div>
              {walletBalance !== null &&
                durationMinutes > 0 &&
                walletBalance < estimatedCost && (
                  <div className="text-xs text-red-400 mt-2">
                    ⚠️ Solde insuffisant — rechargez votre portefeuille
                  </div>
                )}
              {durationMinutes > 0 && durationMinutes < 30 && (
                <div className="text-xs text-red-400 mt-2">
                  ⚠️ Durée minimum : 30 minutes
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={
                loading || durationMinutes < 30 || !hasEnoughFunds
              }
              className="w-full bg-[#e94560] text-white py-3 rounded-lg font-semibold hover:bg-[#c73652] transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading
                ? '⏳ Traitement…'
                : '🚀 Réserver et payer'}
            </button>

            {!hasEnoughFunds && walletBalance !== null && (
              <Link
                href="/profil"
                className="block text-center text-sm text-[#e94560] hover:underline"
              >
                Recharger mon portefeuille →
              </Link>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}