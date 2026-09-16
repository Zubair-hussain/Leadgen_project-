'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuthUser } from '@/hooks/useAuthUser';

export default function Home() {
  const user = useAuthUser();
  const router = useRouter();

  useEffect(() => {
    if (user === undefined) return;
    router.replace(user ? '/dashboard' : '/login');
  }, [user, router]);

  return (
    <div className="h-screen bg-premium-bg flex items-center justify-center text-premium-accent">
      <Loader2 className="animate-spin w-10 h-10" />
    </div>
  );
}
