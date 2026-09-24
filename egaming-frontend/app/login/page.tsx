// app/login/page.tsx

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cloud } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('cloud_access_token')
                || localStorage.getItem('access_token');
    if (token) {
      router.replace('/dashboard');
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!username || !password) {
      toast.error('Veuillez remplir tous les champs');
      return;
    }

    setLoading(true);

    try {
      console.log('🔐 Logging in to CLOUD server with:', username);

      // ✅ Axios returns { data, status, headers, ... }
      const res = await cloud.login(username, password);
      const body = res.data;

      console.log('📥 Login response:', body);

      if (body?.access_token) {
        // ✅ Persist token + user so the rest of the app can find them
        localStorage.setItem('access_token', body.access_token);
        localStorage.setItem('cloud_access_token', body.access_token);
        localStorage.setItem('cloud_user', JSON.stringify(body.user));
        localStorage.setItem('username', body.user.username);
        localStorage.setItem('role', body.user.role);

        toast.success(`Bienvenue ${body.user.username}!`);
        router.replace('/dashboard');
      } else {
        toast.error(body?.error || 'Réponse invalide du serveur');
      }
    } catch (error: any) {
      console.error('❌ Login error:', error);
      const msg =
        error?.response?.data?.error ||
        error?.message ||
        'Erreur de connexion au serveur cloud';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a1a] flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-[#1a1a2e] to-[#0f0f23] rounded-2xl p-8 w-full max-w-md border border-[#2a2a4a]">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🎮</div>
          <h1 className="text-2xl font-bold text-[#e94560]">Ninety Gaming House</h1>
          <p className="text-gray-400 text-sm mt-1">Connectez-vous pour réserver</p>
          <span className="inline-block mt-2 text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full">
            ☁️ Cloud
          </span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-400 text-sm font-medium mb-1">
              Nom d'utilisateur
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none transition"
              placeholder="admin"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-gray-400 text-sm font-medium mb-1">
              Mot de passe
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none transition pr-12"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#e94560] text-white py-3 rounded-lg font-semibold hover:bg-[#c73652] transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                Connexion...
              </span>
            ) : (
              'Se connecter'
            )}
          </button>
        </form>

        <p className="text-center text-gray-400 text-sm mt-6">
          Pas encore de compte ?{' '}
          <Link href="/register" className="text-[#e94560] hover:underline">
            S'inscrire
          </Link>
        </p>

        <div className="mt-6 p-4 bg-[#0a0a1a] rounded-lg border border-[#1a1a2e]">
          <p className="text-xs text-gray-500 text-center">🔑 Comptes de démonstration</p>
          <div className="flex justify-center gap-4 text-xs text-gray-400 mt-1">
            <span>👤 admin</span>
            <span>🔒 admin123</span>
          </div>
        </div>
      </div>
    </div>
  );
}