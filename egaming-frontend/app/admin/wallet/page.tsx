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
  plan_name?: string;
  plan_color?: string;
  hours_remaining?: number;
};

type Transaction = {
  id: number;
  user_id: number;
  amount: number;
  type: string;
  description: string | null;
  balance_after: number | null;
  created_by: string | null;
  timestamp: string;
};

const TYPE_LABELS: Record<string, string> = {
  recharge: 'Recharge',
  session_deduction: 'Session',
  subscription: 'Abonnement',
  admin_adjustment: 'Ajustement Admin',
  refund: 'Remboursement',
};

const TYPE_COLORS: Record<string, string> = {
  recharge: 'bg-green-500/20 text-green-400',
  session_deduction: 'bg-orange-500/20 text-orange-400',
  subscription: 'bg-blue-500/20 text-blue-400',
  admin_adjustment: 'bg-purple-500/20 text-purple-400',
  refund: 'bg-yellow-500/20 text-yellow-400',
};

export default function AdminWalletPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [recentTx, setRecentTx] = useState<Transaction[]>([]);

  // Adjust modal state
  const [adjustUser, setAdjustUser] = useState<User | null>(null);
  const [adjustAmount, setAdjustAmount] = useState('10');
  const [adjustReason, setAdjustReason] = useState('');
  const [isAdjusting, setIsAdjusting] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push('/login');
      return;
    }
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await cloud.adminListUsers();
      const list: User[] = res.data.users || [];
      setUsers(list);

      const allTx: Transaction[] = [];
      for (const u of list.slice(0, 20)) {
        try {
          const detail = await cloud.adminGetUser(u.id);
          const txs: Transaction[] = detail.data.transactions || [];
          for (const tx of txs) {
            allTx.push({ ...tx, user_id: u.id });
          }
        } catch {
          /* skip user if fetch fails */
        }
      }
      allTx.sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      setRecentTx(allTx.slice(0, 50));
    } catch (e: any) {
      console.error('Failed to load wallet data:', e);
      toast.error(e.response?.data?.error || 'Erreur de chargement');
      if (e.response?.status === 403) router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleAdjust = async () => {
    if (!adjustUser) return;
    const amount = parseFloat(adjustAmount);
    if (isNaN(amount) || amount === 0) {
      toast.error('Montant invalide (doit être non nul)');
      return;
    }
    if (!adjustReason.trim()) {
      toast.error('Raison obligatoire');
      return;
    }

    setIsAdjusting(true);
    try {
      await cloud.adminAdjustWallet(
        adjustUser.username,
        amount,
        adjustReason.trim()
      );
      toast.success(
        `${amount > 0 ? '+' : ''}${amount} TND appliqué à ${adjustUser.username}`
      );
      setAdjustUser(null);
      setAdjustReason('');
      setAdjustAmount('10');
      loadData();
    } catch (e: any) {
      toast.error(e.response?.data?.error || "Échec de l'ajustement");
    } finally {
      setIsAdjusting(false);
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      (u.email && u.email.toLowerCase().includes(search.toLowerCase()))
  );

  const filteredTx = recentTx.filter(
    (tx) => !typeFilter || tx.type === typeFilter
  );

  const totalInCirculation = users.reduce(
    (sum, u) => sum + (u.wallet_balance || 0),
    0
  );
  const totalRecharges = recentTx
    .filter((t) => t.type === 'recharge' || t.type === 'admin_adjustment')
    .reduce((sum, t) => sum + (t.amount > 0 ? t.amount : 0), 0);
  const totalDeductions = recentTx
    .filter((t) => t.type === 'session_deduction' || t.type === 'subscription')
    .reduce((sum, t) => sum + Math.abs(t.amount), 0);

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white">
              💰 Gestion des Portefeuilles
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              {users.length} utilisateur(s) • {recentTx.length} transaction(s)
              récente(s)
            </p>
          </div>
          <Link
            href="/dashboard"
            className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-sm text-white hover:border-[#e94560] transition"
          >
            ← Retour
          </Link>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-[#1a1a2e] rounded-xl border border-[#2a2a4a] p-5">
            <p className="text-xs uppercase text-gray-500 mb-2">
              Total en circulation
            </p>
            <p className="text-3xl font-bold text-[#e94560]">
              {totalInCirculation.toFixed(2)} TND
            </p>
          </div>
          <div className="bg-[#1a1a2e] rounded-xl border border-[#2a2a4a] p-5">
            <p className="text-xs uppercase text-gray-500 mb-2">
              Crédits récents
            </p>
            <p className="text-3xl font-bold text-green-400">
              +{totalRecharges.toFixed(2)} TND
            </p>
          </div>
          <div className="bg-[#1a1a2e] rounded-xl border border-[#2a2a4a] p-5">
            <p className="text-xs uppercase text-gray-500 mb-2">
              Débits récents
            </p>
            <p className="text-3xl font-bold text-orange-400">
              −{totalDeductions.toFixed(2)} TND
            </p>
          </div>
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

        {/* Users table */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">Chargement…</div>
        ) : filteredUsers.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            Aucun utilisateur trouvé.
          </div>
        ) : (
          <div className="bg-[#1a1a2e] rounded-xl border border-[#2a2a4a] overflow-hidden mb-10">
            <table className="w-full text-left">
              <thead className="bg-[#0f0f23] text-xs text-gray-400 uppercase">
                <tr>
                  <th className="p-4">Utilisateur</th>
                  <th className="p-4">Email</th>
                  <th className="p-4">Rôle</th>
                  <th className="p-4">Abonnement</th>
                  <th className="p-4">Solde</th>
                  <th className="p-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <tr
                    key={u.id}
                    className="border-t border-[#2a2a4a] hover:bg-[#0f0f23]/50"
                  >
                    <td className="p-4 text-white font-medium">
                      👤 {u.username}
                    </td>
                    <td className="p-4 text-gray-400 text-sm">
                      {u.email || '—'}
                    </td>
                    <td className="p-4">
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${
                          u.role === 'admin'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-green-500/20 text-green-400'
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-gray-300">
                      {u.plan_name || 'Free / Guest'}
                    </td>
                    <td className="p-4">
                      <span
                        className={`font-bold ${
                          u.wallet_balance > 0
                            ? 'text-[#e94560]'
                            : 'text-gray-500'
                        }`}
                      >
                        {u.wallet_balance.toFixed(2)} TND
                      </span>
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => setAdjustUser(u)}
                        className="text-xs bg-[#2a2a4a] hover:bg-[#3a3a5a] text-white px-3 py-1.5 rounded-lg transition"
                      >
                        ⚙️ Ajuster
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Recent transactions */}
        <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-xl font-bold text-white">
            📜 Transactions récentes
          </h2>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#e94560]"
          >
            <option value="">Tous les types</option>
            {Object.entries(TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {filteredTx.length === 0 ? (
          <div className="text-center py-12 text-gray-500 bg-[#1a1a2e] rounded-xl border border-[#2a2a4a]">
            Aucune transaction.
          </div>
        ) : (
          <div className="bg-[#1a1a2e] rounded-xl border border-[#2a2a4a] overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-[#0f0f23] text-xs text-gray-400 uppercase">
                <tr>
                  <th className="p-4">Date</th>
                  <th className="p-4">Utilisateur</th>
                  <th className="p-4">Type</th>
                  <th className="p-4">Description</th>
                  <th className="p-4 text-right">Montant</th>
                  <th className="p-4 text-right">Solde après</th>
                </tr>
              </thead>
              <tbody>
                {filteredTx.map((tx) => {
                  const user = users.find((u) => u.id === tx.user_id);
                  return (
                    <tr
                      key={tx.id}
                      className="border-t border-[#2a2a4a] hover:bg-[#0f0f23]/50"
                    >
                      <td className="p-4 text-xs text-gray-400">
                        {new Date(tx.timestamp).toLocaleString('fr-FR')}
                      </td>
                      <td className="p-4 text-white text-sm">
                        {user?.username || `User #${tx.user_id}`}
                      </td>
                      <td className="p-4">
                        <span
                          className={`text-xs px-2 py-1 rounded-full ${
                            TYPE_COLORS[tx.type] ||
                            'bg-gray-500/20 text-gray-400'
                          }`}
                        >
                          {TYPE_LABELS[tx.type] || tx.type}
                        </span>
                      </td>
                      <td className="p-4 text-gray-400 text-sm max-w-md truncate">
                        {tx.description || '—'}
                        {tx.created_by && (
                          <span className="text-xs text-purple-400 ml-2">
                            (par {tx.created_by})
                          </span>
                        )}
                      </td>
                      <td
                        className={`p-4 text-right font-semibold ${
                          tx.amount >= 0 ? 'text-green-400' : 'text-orange-400'
                        }`}
                      >
                        {tx.amount >= 0 ? '+' : ''}
                        {tx.amount.toFixed(2)} TND
                      </td>
                      <td className="p-4 text-right text-gray-300 text-sm">
                        {tx.balance_after !== null
                          ? `${tx.balance_after.toFixed(2)} TND`
                          : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Adjust modal */}
      {adjustUser && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-[#1a1a2e] rounded-xl p-6 w-full max-w-sm border border-[#2a2a4a]">
            <h3 className="text-xl font-bold text-white mb-1">
              ⚙️ Ajuster le solde
            </h3>
            <p className="text-sm text-gray-400 mb-4">
              Utilisateur:{' '}
              <span className="text-[#e94560]">{adjustUser.username}</span>
              <br />
              Solde actuel:{' '}
              <span className="text-white">
                {adjustUser.wallet_balance.toFixed(2)} TND
              </span>
            </p>

            <label className="block text-xs text-gray-500 mb-1">
              Montant (TND) — positif pour crédit, négatif pour débit
            </label>
            <input
              type="number"
              step="0.5"
              value={adjustAmount}
              onChange={(e) => setAdjustAmount(e.target.value)}
              className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#e94560] mb-3"
            />

            <label className="block text-xs text-gray-500 mb-1">
              Raison (obligatoire)
            </label>
            <textarea
              rows={2}
              placeholder="Ex: correction, geste commercial, remboursement..."
              value={adjustReason}
              onChange={(e) => setAdjustReason(e.target.value)}
              className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#e94560] mb-4 resize-none"
            />

            <div className="flex gap-2">
              <button
                onClick={() => setAdjustUser(null)}
                className="flex-1 py-2 bg-[#2a2a4a] text-white rounded-lg hover:bg-[#3a3a5a] transition"
              >
                Annuler
              </button>
              <button
                onClick={handleAdjust}
                disabled={isAdjusting}
                className="flex-1 py-2 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73652] transition disabled:opacity-50"
              >
                {isAdjusting ? '...' : 'Confirmer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}