'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cloud, getAuthToken } from '@/lib/api';

type User = {
  id: number;
  username: string;
  email: string | null;
  role: string;
  wallet_balance: number;
  created_at: string;
};

export default function AdminUsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  
  // Top-up modal state
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [topupAmount, setTopupAmount] = useState('10');
  const [isTopupLoading, setIsTopupLoading] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push('/login');
      return;
    }

    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const res = await cloud.adminListUsers();
      setUsers(res.data.users || []);
    } catch (e: any) {
      console.error('Failed to load users:', e);
      toast.error(e.response?.data?.error || 'Erreur de chargement');
      if (e.response?.status === 403) router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleTopup = async () => {
    if (!selectedUser) return;
    const amount = parseFloat(topupAmount);
    if (isNaN(amount) || amount <= 0) {
      toast.error('Montant invalide');
      return;
    }

    setIsTopupLoading(true);
    try {
      await cloud.adminTopupUser(selectedUser.id, amount);
      toast.success(`+${amount} TND ajouté à ${selectedUser.username}`);
      setSelectedUser(null);
      loadUsers();
    } catch (e: any) {
      toast.error(e.response?.data?.error || 'Échec du rechargement');
    } finally {
      setIsTopupLoading(false);
    }
  };

  const filteredUsers = users.filter(u => 
    u.username.toLowerCase().includes(search.toLowerCase()) ||
    (u.email && u.email.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white">👥 Gestion des Utilisateurs</h1>
            <p className="text-gray-500 text-sm mt-1">
              {users.length} utilisateur(s) enregistré(s)
            </p>
          </div>
          <Link 
            href="/dashboard"
            className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-sm text-white hover:border-[#e94560] transition"
          >
            ← Retour
          </Link>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="🔍 Rechercher par nom ou email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-md bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[#e94560]"
          />
        </div>

        {/* Users Table */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">Chargement…</div>
        ) : filteredUsers.length === 0 ? (
          <div className="text-center py-12 text-gray-500">Aucun utilisateur trouvé.</div>
        ) : (
          <div className="bg-[#1a1a2e] rounded-xl border border-[#2a2a4a] overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-[#0f0f23] text-xs text-gray-400 uppercase">
                <tr>
                  <th className="p-4">Utilisateur</th>
                  <th className="p-4">Email</th>
                  <th className="p-4">Rôle</th>
                  <th className="p-4">Solde</th>
                  <th className="p-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <tr key={u.id} className="border-t border-[#2a2a4a] hover:bg-[#0f0f23]/50">
                    <td className="p-4 text-white font-medium">
                      👤 {u.username}
                    </td>
                    <td className="p-4 text-gray-400 text-sm">
                      {u.email || '—'}
                    </td>
                    <td className="p-4">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        u.role === 'admin' 
                          ? 'bg-red-500/20 text-red-400' 
                          : 'bg-green-500/20 text-green-400'
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`font-bold ${
                        u.wallet_balance > 0 ? 'text-[#e94560]' : 'text-gray-500'
                      }`}>
                        {u.wallet_balance.toFixed(2)} TND
                      </span>
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => setSelectedUser(u)}
                        className="text-xs bg-[#2a2a4a] hover:bg-[#3a3a5a] text-white px-3 py-1.5 rounded-lg transition"
                      >
                        💰 Recharger
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Top-up Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-[#1a1a2e] rounded-xl p-6 w-full max-w-sm border border-[#2a2a4a]">
            <h3 className="text-xl font-bold text-white mb-1">💰 Recharger le solde</h3>
            <p className="text-sm text-gray-400 mb-4">
              Utilisateur: <span className="text-[#e94560]">{selectedUser.username}</span>
            </p>

            <label className="block text-xs text-gray-500 mb-1">Montant (TND)</label>
            <input
              type="number"
              min="1"
              step="0.5"
              value={topupAmount}
              onChange={(e) => setTopupAmount(e.target.value)}
              className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#e94560] mb-4"
            />

            <div className="flex gap-2">
              <button
                onClick={() => setSelectedUser(null)}
                className="flex-1 py-2 bg-[#2a2a4a] text-white rounded-lg hover:bg-[#3a3a5a] transition"
              >
                Annuler
              </button>
              <button
                onClick={handleTopup}
                disabled={isTopupLoading}
                className="flex-1 py-2 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73652] transition disabled:opacity-50"
              >
                {isTopupLoading ? '...' : 'Confirmer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}