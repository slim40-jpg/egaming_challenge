'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cloud, getAuthToken } from '@/lib/api';

type Transaction = {
  id: number;
  amount: number;
  type: 'recharge' | 'session_deduction';
  description: string;
  timestamp: string;
};

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Recharge state
  const [rechargeAmount, setRechargeAmount] = useState<string>('10');
  const [isRecharging, setIsRecharging] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push('/login');
      return;
    }

    // Load user from local storage
    const raw = localStorage.getItem('cloud_user') || localStorage.getItem('user');
    if (raw) {
      try {
        setUser(JSON.parse(raw));
      } catch {}
    }

    loadWalletData();
  }, []);

  const loadWalletData = async () => {
    setLoading(true);
    try {
      // Fetch Balance
      const walletRes = await cloud.getWallet();
      setBalance(walletRes.data.wallet.balance);

      // Fetch Transactions
      const txRes = await cloud.getTransactions();
      setTransactions(txRes.data.transactions || []);
    } catch (e: any) {
      console.error('Failed to load wallet:', e);
      toast.error('Erreur lors du chargement du portefeuille');
    } finally {
      setLoading(false);
    }
  };

  const handleRecharge = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(rechargeAmount);
    
    if (isNaN(amount) || amount <= 0) {
      toast.error('Veuillez entrer un montant valide');
      return;
    }

    setIsRecharging(true);
    try {
      const res = await cloud.rechargeWallet(amount);
      setBalance(res.data.new_balance);
      toast.success(`Rechargement de ${amount} TND réussi !`);
      
      // Refresh transactions to show the new one
      const txRes = await cloud.getTransactions();
      setTransactions(txRes.data.transactions || []);
      
    } catch (e: any) {
      console.error('Recharge failed:', e);
      toast.error(e.response?.data?.error || 'Échec du rechargement');
    } finally {
      setIsRecharging(false);
    }
  };

  const logout = () => {
    localStorage.clear();
    router.push('/login');
  };

  if (loading && balance === null) {
    return (
      <div className="min-h-screen bg-[#0a0a1a] flex items-center justify-center text-gray-500">
        Chargement du profil…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-4xl mx-auto">
        
        {/* Header / Nav */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-white">👤 Mon Profil</h1>
          <div className="flex gap-3">
            <Link 
              href="/dashboard" 
              className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-sm text-white hover:border-[#e94560] transition"
            >
              ← Retour au Dashboard
            </Link>
            <button
              onClick={logout}
              className="px-4 py-2 bg-[#2a2a4a] rounded-lg text-white hover:bg-[#3a3a5a] text-sm transition"
            >
              Déconnexion
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Left Column: User Info & Wallet */}
          <div className="md:col-span-1 space-y-6">
            
            {/* User Card */}
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a]">
              <h2 className="text-xl font-bold text-white mb-4">Informations</h2>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-gray-500 block">Nom d'utilisateur</span>
                  <span className="text-white font-medium">{user?.username || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Email</span>
                  <span className="text-white font-medium">{user?.email || 'Non renseigné'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Rôle</span>
                  <span className="text-[#e94560] font-bold uppercase">{user?.role || 'player'}</span>
                </div>
              </div>
            </div>

            {/* Wallet Card */}
            <div className="bg-gradient-to-br from-[#1a1a2e] to-[#0f0f23] rounded-xl p-6 border border-[#e94560]/30 shadow-[0_0_15px_rgba(233,69,96,0.1)]">
              <h2 className="text-xl font-bold text-white mb-2">💳 Mon Portefeuille</h2>
              <div className="text-4xl font-extrabold text-[#e94560] mb-6">
                {balance !== null ? `${balance.toFixed(2)} TND` : '--- TND'}
              </div>
              
              <form onSubmit={handleRecharge} className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Montant à recharger (TND)</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min="1"
                      step="0.5"
                      value={rechargeAmount}
                      onChange={(e) => setRechargeAmount(e.target.value)}
                      className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-[#e94560]"
                      placeholder="Ex: 20"
                    />
                    <button
                      type="submit"
                      disabled={isRecharging}
                      className="px-4 py-2 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73652] transition disabled:opacity-50 whitespace-nowrap"
                    >
                      {isRecharging ? '...' : 'Recharger'}
                    </button>
                  </div>
                </div>
              </form>
              <p className="text-[10px] text-gray-500 mt-3">
                * Paiement simulé pour le MVP. Dans la version finale, cela redirigera vers Stripe/Flouci.
              </p>
            </div>
          </div>

          {/* Right Column: Transaction History */}
          <div className="md:col-span-2">
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-[#2a2a4a] h-full">
              <h2 className="text-xl font-bold text-white mb-4">📜 Historique des transactions</h2>
              
              {transactions.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  Aucune transaction pour le moment.
                </div>
              ) : (
                <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                  {transactions.map((tx) => (
                    <div 
                      key={tx.id} 
                      className="flex justify-between items-center bg-[#0f0f23] p-4 rounded-lg border border-[#2a2a4a]"
                    >
                      <div>
                        <p className="text-white font-medium">{tx.description}</p>
                        <p className="text-xs text-gray-500">
                          {new Date(tx.timestamp).toLocaleString('fr-FR')}
                        </p>
                      </div>
                      <div className={`font-bold ${tx.type === 'recharge' ? 'text-green-400' : 'text-red-400'}`}>
                        {tx.type === 'recharge' ? '+' : '-'}{tx.amount.toFixed(2)} TND
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}