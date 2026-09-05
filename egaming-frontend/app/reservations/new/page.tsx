// app/reservations/new/page.tsx

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cloudCreateReservation, cloudGetPCs, cloudCheckAvailability } from '@/lib/api';

export default function NewReservationPage() {
  const router = useRouter();
  const [pcs, setPCs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    pc_id: '',
    start_time: '',
    end_time: '',
    center_id: 'main'
  });

  useEffect(() => {
    // Check auth
    const token = localStorage.getItem('cloud_access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchPCs();
  }, []);

  const fetchPCs = async () => {
    try {
      const data = await cloudGetPCs();
      setPCs(data);
    } catch (error) {
      console.error('Failed to fetch PCs:', error);
      toast.error('Erreur de chargement des PCs');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Check availability first
      const availability = await cloudCheckAvailability(
        formData.pc_id,
        formData.start_time,
        formData.end_time
      );

      if (!availability.available) {
        toast.error('PC non disponible à cette heure');
        setLoading(false);
        return;
      }

      // Create reservation
      const result = await cloudCreateReservation(formData);
      
      if (result.status === 'ok') {
        toast.success('✅ Réservation créée avec succès!');
        router.push('/reservations');
      } else {
        toast.error(result.message || 'Erreur lors de la création');
      }
    } catch (error: any) {
      console.error('Create reservation error:', error);
      toast.error(error?.response?.data?.message || 'Erreur lors de la création');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-2xl mx-auto">
        <div className="bg-gradient-to-r from-[#1a1a2e] to-[#16213e] rounded-2xl p-6 mb-8 border border-[#2a2a4a]">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-[#e94560]">📅 Nouvelle réservation</h1>
            <Link
              href="/reservations"
              className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-white hover:bg-[#2a2a4a] transition"
            >
              ← Retour
            </Link>
          </div>
        </div>

        <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm font-medium mb-1">
                PC *
              </label>
              <select
                value={formData.pc_id}
                onChange={(e) => setFormData({...formData, pc_id: e.target.value})}
                className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                required
              >
                <option value="">Sélectionner un PC</option>
                {pcs.map((pc) => (
                  <option key={pc.id} value={pc.id}>
                    {pc.hostname || pc.id} - {pc.status === 'online' ? '🟢' : '🔴'}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-gray-400 text-sm font-medium mb-1">
                Début *
              </label>
              <input
                type="datetime-local"
                value={formData.start_time}
                onChange={(e) => setFormData({...formData, start_time: e.target.value})}
                className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                required
              />
            </div>

            <div>
              <label className="block text-gray-400 text-sm font-medium mb-1">
                Fin *
              </label>
              <input
                type="datetime-local"
                value={formData.end_time}
                onChange={(e) => setFormData({...formData, end_time: e.target.value})}
                className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white focus:border-[#e94560] focus:outline-none transition"
                required
              />
            </div>

            <div className="bg-[#0f0f23] rounded-lg p-4 text-center">
              <p className="text-yellow-400 text-sm font-semibold">
                💰 0.10€ / minute
              </p>
              <p className="text-gray-500 text-xs mt-1">Durée minimum: 30 minutes</p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#e94560] text-white py-3 rounded-lg font-semibold hover:bg-[#c73652] transition disabled:opacity-50"
            >
              {loading ? '⏳ Création...' : '🚀 Réserver'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}