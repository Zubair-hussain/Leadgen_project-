'use client';

import AuthGate from '@/components/AuthGate';
import Dashboard from '@/views/Dashboard';

export default function DashboardPage() {
  return (
    <AuthGate require="authed" redirectTo="/login">
      <Dashboard />
    </AuthGate>
  );
}
