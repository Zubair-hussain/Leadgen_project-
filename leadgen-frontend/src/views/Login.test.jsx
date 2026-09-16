import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const signInWithPopup = vi.fn();
const toastSuccess = vi.fn();
const toastError = vi.fn();
const exchangeFirebaseToken = vi.fn();

vi.mock('firebase/auth', () => ({
  signInWithPopup: (...args) => signInWithPopup(...args),
}));
vi.mock('../firebase', () => ({
  auth: {},
  googleProvider: {},
}));
vi.mock('../services/api', () => ({
  exchangeFirebaseToken: (...a) => exchangeFirebaseToken(...a),
}));
vi.mock('react-toastify', () => ({
  toast: { success: (...a) => toastSuccess(...a), error: (...a) => toastError(...a) },
}));

import Login from './Login';

describe('Login', () => {
  beforeEach(() => {
    signInWithPopup.mockReset();
    toastSuccess.mockReset();
    toastError.mockReset();
    exchangeFirebaseToken.mockReset();
    exchangeFirebaseToken.mockResolvedValue({ access: 'a', refresh: 'r' });
  });

  it('renders the hero content and sign-in button', () => {
    render(<Login />);
    expect(screen.getByText('Big Client')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Continue with Google/i })).toBeInTheDocument();
  });

  it('signs in successfully', async () => {
    signInWithPopup.mockResolvedValue({ user: {} });
    render(<Login />);
    await userEvent.click(screen.getByRole('button', { name: /Continue with Google/i }));
    await waitFor(() => expect(signInWithPopup).toHaveBeenCalled());
    await waitFor(() => expect(exchangeFirebaseToken).toHaveBeenCalled());
    await waitFor(() => expect(toastSuccess).toHaveBeenCalled());
  });

  it('still signs in when the JWT exchange fails', async () => {
    signInWithPopup.mockResolvedValue({ user: {} });
    exchangeFirebaseToken.mockRejectedValue(new Error('backend down'));
    render(<Login />);
    await userEvent.click(screen.getByRole('button', { name: /Continue with Google/i }));
    await waitFor(() => expect(toastSuccess).toHaveBeenCalled());
  });

  it('shows an error toast on failed sign-in', async () => {
    signInWithPopup.mockRejectedValue(new Error('nope'));
    render(<Login />);
    await userEvent.click(screen.getByRole('button', { name: /Continue with Google/i }));
    await waitFor(() => expect(toastError).toHaveBeenCalled());
  });
});
