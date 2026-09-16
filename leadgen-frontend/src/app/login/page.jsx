'use client';

import AuthGate from '@/components/AuthGate';
import Login from '@/views/Login';

export default function LoginPage() {
  return (
    <AuthGate require="anon" redirectTo="/dashboard">
      <Login />
    </AuthGate>
  );
}
