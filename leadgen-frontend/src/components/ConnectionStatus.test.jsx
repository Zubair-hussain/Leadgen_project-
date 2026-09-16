import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

const checkBackendHealth = vi.fn();
vi.mock('../services/api', () => ({
  checkBackendHealth: (...args) => checkBackendHealth(...args),
}));

import ConnectionStatus from './ConnectionStatus';

describe('ConnectionStatus', () => {
  beforeEach(() => {
    checkBackendHealth.mockReset();
  });

  it('shows the checking state before the first result resolves', () => {
    checkBackendHealth.mockReturnValue(new Promise(() => {}));
    render(<ConnectionStatus />);
    expect(screen.getByText('Checking...')).toBeInTheDocument();
  });

  it('shows connected when the backend is reachable', async () => {
    checkBackendHealth.mockResolvedValue({ connected: true, data: {} });
    render(<ConnectionStatus />);
    expect(await screen.findByText('Backend Connected')).toBeInTheDocument();
  });

  it('shows disconnected when the backend is unreachable', async () => {
    checkBackendHealth.mockResolvedValue({ connected: false, error: 'boom' });
    render(<ConnectionStatus />);
    expect(await screen.findByText('Backend Disconnected')).toBeInTheDocument();
  });

  it('polls the backend on an interval', async () => {
    vi.useFakeTimers();
    try {
      checkBackendHealth.mockResolvedValue({ connected: true });
      render(<ConnectionStatus />);
      await vi.advanceTimersByTimeAsync(0);
      expect(checkBackendHealth).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(10000);
      expect(checkBackendHealth).toHaveBeenCalledTimes(2);
    } finally {
      vi.runOnlyPendingTimers();
      vi.useRealTimers();
    }
  });
});
