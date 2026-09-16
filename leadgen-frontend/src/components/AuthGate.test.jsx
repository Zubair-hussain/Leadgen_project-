import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const { replace, useAuthUser } = vi.hoisted(() => ({
  replace: vi.fn(),
  useAuthUser: vi.fn(),
}));

vi.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));
vi.mock('@/hooks/useAuthUser', () => ({ useAuthUser: () => useAuthUser() }));

import AuthGate from './AuthGate';

describe('AuthGate', () => {
  beforeEach(() => {
    replace.mockReset();
    useAuthUser.mockReset();
  });

  it('shows a loader while auth state resolves', () => {
    useAuthUser.mockReturnValue(undefined);
    const { container } = render(
      <AuthGate require="authed">
        <div>secret</div>
      </AuthGate>,
    );
    expect(container.querySelector('.animate-spin')).toBeTruthy();
    expect(screen.queryByText('secret')).not.toBeInTheDocument();
  });

  it('renders children when the auth requirement is met', () => {
    useAuthUser.mockReturnValue({ uid: 'u1' });
    render(
      <AuthGate require="authed">
        <div>secret</div>
      </AuthGate>,
    );
    expect(screen.getByText('secret')).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it('redirects anonymous users away from a protected route', async () => {
    useAuthUser.mockReturnValue(null);
    render(
      <AuthGate require="authed" redirectTo="/login">
        <div>secret</div>
      </AuthGate>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
    expect(screen.queryByText('secret')).not.toBeInTheDocument();
  });

  it('redirects signed-in users away from an anon-only route', async () => {
    useAuthUser.mockReturnValue({ uid: 'u1' });
    render(
      <AuthGate require="anon" redirectTo="/dashboard">
        <div>login form</div>
      </AuthGate>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/dashboard'));
  });

  it('falls back to a default redirect target', async () => {
    useAuthUser.mockReturnValue(null);
    render(
      <AuthGate require="authed">
        <div>secret</div>
      </AuthGate>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  });
});
