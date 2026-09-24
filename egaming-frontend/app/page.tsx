// frontend/app/page.tsx

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAuthToken } from '@/lib/api';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = getAuthToken();
    router.replace(token ? '/dashboard' : '/login');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#0a0a1a]">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-t-[#e94560] border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin mx-auto"></div>
        <p className="mt-4 text-gray-400">Redirection…</p>
      </div>
    </div>
  );
}