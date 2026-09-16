'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuthUser } from '@/hooks/useAuthUser';

function FullScreenLoader() {
  return (
    <div className="h-screen bg-premium-bg flex items-center justify-center text-premium-accent">
      <Loader2 className="animate-spin w-10 h-10" />
    </div>
  );
}

/**
 * Client-side route guard.
 * - require="authed": redirect anonymous users to `redirectTo`.
 * - require="anon": redirect signed-in users to `redirectTo`.
 */
export default function AuthGate({ require: requirement = 'authed', redirectTo, children }) {
  const user = useAuthUser();
  const router = useRouter();
  const loading = user === undefined;
  const blocked =
    !loading &&
    ((requirement === 'authed' && !user) || (requirement === 'anon' && user));

  useEffect(() => {
    if (loading || !blocked) return;
    router.replace(redirectTo || (requirement === 'authed' ? '/login' : '/dashboard'));
  }, [loading, blocked, requirement, redirectTo, router]);

  if (loading || blocked) return <FullScreenLoader />;
  return children;
}
