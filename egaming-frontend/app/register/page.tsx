// frontend/app/register/page.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const { username, email, password, confirmPassword, full_name } = formData;

    if (!username || !email || !password || !confirmPassword) {
      toast.error('Veuillez remplir tous les champs obligatoires');
      return;
    }

    if (password.length < 6) {
      toast.error('Le mot de passe doit contenir au moins 6 caractères');
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Les mots de passe ne correspondent pas');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          email,
          password,
          full_name: full_name || username,
        }),
      });

      const data = await response.json();

      if (data.status === 'ok') {
        toast.success('Inscription réussie ! Vous pouvez maintenant vous connecter');
        router.push('/login');
      } else {
        toast.error(data.message || 'Erreur lors de l\'inscription');
      }
    } catch (error) {
      toast.error('Erreur de connexion au serveur');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a1a] flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-[#1a1a2e] to-[#0f0f23] rounded-2xl p-8 w-full max-w-md border border-[#2a2a4a]">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🎮</div>
          <h1 className="text-2xl font-bold text-[#e94560]">Créer un compte</h1>
          <p className="text-gray-400 text-sm mt-1">Rejoignez Ninety Gaming House</p>
        </div>

        {/* Register Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-400 text-sm font-medium mb-1">
              Nom d'utilisateur <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none transition"
              placeholder="john_doe"
              required
            />
          </div>

          <div>
            <label className="block text-gray-400 text-sm font-medium mb-1">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none transition"
              placeholder="john@example.com"
              required
            />
          </div>

          <div>
            <label className="block text-gray-400 text-sm font-medium mb-1">
              Nom complet
            </label>
            <input
              type="text"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none transition"
              placeholder="John Doe"
            />
          </div>

          <div>
            <label className="block text-gray-400 text-sm font-medium mb-1">
              Mot de passe <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none transition pr-12"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">Minimum 6 caractères</p>
          </div>

          <div>
            <label className="block text-gray-400 text-sm font-medium mb-1">
              Confirmer le mot de passe <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-[#e94560] focus:outline-none transition"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#e94560] text-white py-3 rounded-lg font-semibold hover:bg-[#c73652] transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                Inscription...
              </span>
            ) : (
              'S\'inscrire'
            )}
          </button>
        </form>

        {/* Login Link */}
        <p className="text-center text-gray-400 text-sm mt-6">
          Déjà un compte ?{' '}
          <Link href="/login" className="text-[#e94560] hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}