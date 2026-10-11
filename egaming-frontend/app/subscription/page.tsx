'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cloud, getAuthToken } from '@/lib/api';

type Plan = {
  id: number;
  name: string;
  price_per_month: number;
  included_hours: number;
  discount_percent: number;
  color: string;
  description: string;
  is_active: boolean;
};

type Subscription = {
  id: number;
  plan_id: number;
  plan_name: string;
  plan_color: string;
  started_at: string;
  expires_at: string;
  hours_remaining: number;
  is_active: boolean;
};

export default function SubscriptionPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [mySub, setMySub] = useState<Subscription | null>(null);
  const [walletBalance, setWalletBalance] = useState(0);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState<number | null>(null);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push('/login');
      return;
    }

    const raw = localStorage.getItem('cloud_user') || localStorage.getItem('user');
    if (raw) {
      try { setUser(JSON.parse(raw)); } catch {}
    }

    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [plansRes, subRes, walletRes] = await Promise.all([
        cloud.listPlans(),
        cloud.mySubscription(),
        cloud.getWallet(),
      ]);
      setPlans(plansRes.data.plans || []);
      setMySub(subRes.data.subscription || null);
      setWalletBalance(walletRes.data.wallet?.balance || 0);
    } catch (e: any) {
      console.error(e);
      toast.error('Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (plan: Plan) => {
    if (plan.price_per_month > walletBalance) {
      toast.error(
        `Solde insuffisant. Requis: ${plan.price_per_month} TND, Disponible: ${walletBalance.toFixed(2)} TND`
      );
      return;
    }

    if (!confirm(`S'abonner au plan "${plan.name}" pour ${plan.price_per_month} TND ?`))
      return;

    setSubscribing(plan.id);
    try {
      const res = await cloud.subscribe(plan.id);
      toast.success(`Abonné à ${plan.name} !`);
      setMySub(res.data.subscription);
      setWalletBalance(res.data.new_balance);
      loadData();
    } catch (e: any) {
      toast.error(e.response?.data?.error || 'Erreur lors de l\'abonnement');
    } finally {
      setSubscribing(null);
    }
  };

  const getPlanCardStyle = (plan: Plan) => {
    if (plan.color === 'platinum') {
      return 'border-purple-500/50 hover:border-purple-500 bg-gradient-to-br from-purple-500/5 to-transparent';
    }
    if (plan.color === 'gold') {
      return 'border-yellow-500/50 hover:border-yellow-500 bg-gradient-to-br from-yellow-500/5 to-transparent';
    }
    if (plan.color === 'silver') {
      return 'border-gray-400/50 hover:border-gray-400 bg-gradient-to-br from-gray-400/5 to-transparent';
    }
    return 'border-[#2a2a4a] hover:border-[#3a3a5a]';
  };

  const getPlanBadge = (plan: Plan) => {
    if (plan.name === 'Pro Gamer') {
      return (
        <span className="text-[10px] bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full font-bold">
          🏆 VIP
        </span>
      );
    }
    if (plan.name === 'Premium') {
      return (
        <span className="text-[10px] bg-yellow-500/20 text-yellow-300 px-2 py-0.5 rounded-full font-bold">
          ⭐ POPULAIRE
        </span>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a1a] flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-t-[#e94560] border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const isSubscribedTo = (planId: number) =>
    mySub && mySub.is_active && mySub.plan_id === planId;

  return (
    <div className="min-h-screen bg-[#0a0a1a] p-6">
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white">⭐ Abonnements</h1>
            <p className="text-gray-500 text-sm mt-1">
              Choisissez le plan qui vous convient
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg px-4 py-2">
              <div className="text-xs text-gray-500">Solde</div>
              <div className="text-lg font-bold text-[#e94560]">
                {walletBalance.toFixed(2)} TND
              </div>
            </div>
            <Link
              href="/profil"
              className="px-4 py-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg text-sm text-white hover:border-[#e94560] transition"
            >
              ← Profil
            </Link>
          </div>
        </div>

        {/* Current subscription banner */}
        {mySub && mySub.is_active && (
          <div className={`mb-8 p-5 rounded-xl border-2 ${
            mySub.plan_color === 'platinum' ? 'border-purple-500 bg-purple-500/10' :
            mySub.plan_color === 'gold' ? 'border-yellow-500 bg-yellow-500/10' :
            mySub.plan_color === 'silver' ? 'border-gray-400 bg-gray-400/10' :
            'border-[#2a2a4a] bg-[#1a1a2e]'
          }`}>
            <div className="flex justify-between items-center flex-wrap gap-4">
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wide">
                  Abonnement actif
                </div>
                <div className="text-2xl font-bold text-white mt-1">
                  ⭐ {mySub.plan_name}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  Expire le{' '}
                  {new Date(mySub.expires_at).toLocaleDateString('fr-FR', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric',
                  })}
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-400 uppercase">Heures restantes</div>
                <div className="text-3xl font-bold text-green-400">
                  {mySub.hours_remaining.toFixed(1)}h
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Plans grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {plans.map((plan) => {
            const isCurrent = isSubscribedTo(plan.id);
            const canAfford = plan.price_per_month <= walletBalance;
            const isFree = plan.price_per_month === 0;

            return (
              <div
                key={plan.id}
                className={`relative bg-[#1a1a2e] rounded-2xl p-6 border-2 transition-all hover:transform hover:-translate-y-1 ${getPlanCardStyle(plan)}`}
              >
                {/* Top badge */}
                <div className="flex justify-between items-start mb-4 min-h-[24px]">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">
                    {plan.color}
                  </div>
                  {getPlanBadge(plan)}
                </div>

                {/* Plan name */}
                <div className="text-2xl font-bold text-white mb-3">
                  {plan.name}
                </div>

                {/* Price */}
                <div className="mb-5">
                  {isFree ? (
                    <div className="text-4xl font-extrabold text-gray-300">
                      Gratuit
                    </div>
                  ) : (
                    <>
                      <span className="text-4xl font-extrabold text-[#e94560]">
                        {plan.price_per_month.toFixed(0)}
                      </span>
                      <span className="text-sm text-gray-400 ml-1">
                        TND<span className="text-xs">/mois</span>
                      </span>
                    </>
                  )}
                </div>

                {/* Divider */}
                <div className="border-t border-[#2a2a4a] mb-5"></div>

                {/* Benefits */}
                <ul className="space-y-3 mb-6 text-sm">
                  <li className="flex items-start gap-2 text-gray-300">
                    <span className="text-green-400 mt-0.5">✓</span>
                    <span>
                      {plan.included_hours > 0
                        ? `${plan.included_hours}h de jeu incluses`
                        : 'Payez à la minute'}
                    </span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <span className="text-green-400 mt-0.5">✓</span>
                    <span>
                      {plan.discount_percent > 0
                        ? `${plan.discount_percent}% de réduction`
                        : 'Aucune réduction'}
                    </span>
                  </li>
                  {plan.name === 'Premium' && (
                    <li className="flex items-start gap-2 text-gray-300">
                      <span className="text-green-400 mt-0.5">✓</span>
                      <span>Réservation prioritaire</span>
                    </li>
                  )}
                  {plan.name === 'Pro Gamer' && (
                    <>
                      <li className="flex items-start gap-2 text-gray-300">
                        <span className="text-green-400 mt-0.5">✓</span>
                        <span>Réservation prioritaire</span>
                      </li>
                      <li className="flex items-start gap-2 text-gray-300">
                        <span className="text-green-400 mt-0.5">✓</span>
                        <span>Accès aux tournois</span>
                      </li>
                      <li className="flex items-start gap-2 text-gray-300">
                        <span className="text-green-400 mt-0.5">✓</span>
                        <span>Salon VIP</span>
                      </li>
                    </>
                  )}
                  {plan.name === 'Free / Guest' && (
                    <li className="flex items-start gap-2 text-gray-300">
                      <span className="text-green-400 mt-0.5">✓</span>
                      <span>Aucun engagement</span>
                    </li>
                  )}
                </ul>

                {/* Description */}
                {plan.description && (
                  <div className="text-xs text-gray-500 italic mb-5">
                    {plan.description}
                  </div>
                )}

                {/* Action button */}
                {isCurrent ? (
                  <div className="w-full py-3 bg-green-500/20 text-green-400 rounded-xl text-center text-sm font-bold">
                    ✅ Plan actuel
                  </div>
                ) : isFree ? (
                  <div className="w-full py-3 bg-[#0f0f23] text-gray-500 rounded-xl text-center text-sm">
                    Plan par défaut
                  </div>
                ) : (
                  <button
                    onClick={() => handleSubscribe(plan)}
                    disabled={subscribing === plan.id || !canAfford}
                    className={`w-full py-3 rounded-xl text-sm font-bold transition ${
                      canAfford
                        ? 'bg-[#e94560] text-white hover:bg-[#c73652]'
                        : 'bg-[#2a2a4a] text-gray-500 cursor-not-allowed'
                    } disabled:opacity-50`}
                  >
                    {subscribing === plan.id
                      ? '⏳ Traitement...'
                      : canAfford
                      ? 'S\'abonner'
                      : 'Solde insuffisant'}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Info footer */}
        <div className="mt-8 p-4 bg-[#1a1a2e] border border-[#2a2a4a] rounded-xl">
          <div className="text-xs text-gray-500">
            💡 <b>Astuce :</b> Les abonnements sont débités automatiquement de
            votre portefeuille et sont valables 30 jours. Les heures non
            utilisées ne sont pas reportées au mois suivant.
          </div>
        </div>

      </div>
    </div>
  );
}