'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { cloud, getAuthToken } from '@/lib/api';
import toast from 'react-hot-toast';

export default function MyReservations() {
  const router = useRouter();
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAuthToken()) {
      router.push('/login');
      return;
    }
    load();
  }, []);

  const load = async () => {
    try {
      const r = await cloud.myReservations();
      setRows(r.data.reservations || []);
    } catch (e: any) {
      toast.error('Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  const cancel = async (id: number) => {
    if (!confirm('Annuler cette réservation ?')) return;
    try {
      await cloud.cancelReservation(id);
      toast.success('Annulée');
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  if (loading) return <div className="min-h-screen bg-[#0a0a1a] p-6 text-gray-400">Chargement…</div>;

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-6">📅 Mes réservations</h1>
        {rows.length === 0 ? (
          <div className="text-gray-500 text-center py-12">
            Aucune réservation
          </div>
        ) : (
          <div className="space-y-3">
            {rows.map((r) => (
              <div
                key={r.id}
                className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-xl p-4 flex justify-between items-center"
              >
                <div>
                  <div className="text-white font-bold">{r.pc_id}</div>
                  <div className="text-sm text-gray-400">
                    {new Date(r.start_time).toLocaleString()} →{' '}
                    {new Date(r.end_time).toLocaleString()}
                  </div>
                  <div
                    className={`text-xs mt-1 ${
                      r.status === 'accepted'
                        ? 'text-green-400'
                        : r.status === 'cancelled'
                        ? 'text-red-400'
                        : 'text-gray-400'
                    }`}
                  >
                    {r.status}
                  </div>
                </div>
                {r.status === 'accepted' && (
                  <button
                    onClick={() => cancel(r.id)}
                    className="text-red-400 hover:underline text-sm"
                  >
                    Annuler
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}