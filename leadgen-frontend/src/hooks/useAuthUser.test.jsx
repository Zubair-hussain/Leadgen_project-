import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, act } from '@testing-library/react';

const { onAuthStateChanged } = vi.hoisted(() => ({ onAuthStateChanged: vi.fn() }));

vi.mock('firebase/auth', () => ({ onAuthStateChanged }));
vi.mock('@/firebase', () => ({ auth: {} }));

import { useAuthUser } from './useAuthUser';

// Test harness component that surfaces the hook's value.
function Probe() {
  const user = useAuthUser();
  return <div data-testid="v">{user === undefined ? 'loading' : JSON.stringify(user)}</div>;
}

describe('useAuthUser', () => {
  let authCallback;
  let unsub;

  beforeEach(() => {
    authCallback = null;
    unsub = vi.fn();
    onAuthStateChanged.mockReset();
    onAuthStateChanged.mockImplementation((_auth, cb) => {
      authCallback = cb;
      return unsub;
    });
  });

  it('is loading until the first auth callback', () => {
    const { getByTestId } = render(<Probe />);
    expect(getByTestId('v').textContent).toBe('loading');
    expect(typeof authCallback).toBe('function');
  });

  it('returns the user when signed in', () => {
    const { getByTestId } = render(<Probe />);
    act(() => authCallback({ uid: 'u1' }));
    expect(getByTestId('v').textContent).toBe(JSON.stringify({ uid: 'u1' }));
  });

  it('returns null when signed out', () => {
    const { getByTestId } = render(<Probe />);
    act(() => authCallback(null));
    expect(getByTestId('v').textContent).toBe('null');
  });

  it('unsubscribes on unmount', () => {
    const { unmount } = render(<Probe />);
    unmount();
    expect(unsub).toHaveBeenCalled();
  });
});
