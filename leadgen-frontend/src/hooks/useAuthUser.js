'use client';

import { useEffect, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '@/firebase';

/**
 * Subscribe to Firebase auth state.
 * Returns `undefined` while resolving, then the user object or `null`.
 */
export function useAuthUser() {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser ?? null);
    });
    return () => unsubscribe();
  }, []);

  return user;
}
