import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VerifierTab from './VerifierTab';

function setup(overrides = {}) {
  const props = {
    singleEmail: '',
    setSingleEmail: vi.fn(),
    handleSingleVerify: vi.fn((e) => e && e.preventDefault && e.preventDefault()),
    singleResult: null,
    multiEmails: '',
    setMultiEmails: vi.fn(),
    handleMultiVerify: vi.fn(),
    handleFileVerify: vi.fn(),
    verifierResults: [],
    handleBulkVerify: vi.fn(),
    busy: false,
    ...overrides,
  };
  render(<VerifierTab {...props} />);
  return props;
}

describe('VerifierTab', () => {
  it('renders the four verification methods', () => {
    setup();
    expect(screen.getByText('Quick Identity Check')).toBeInTheDocument();
    expect(screen.getByText('Database Audit')).toBeInTheDocument();
    expect(screen.getByText('Paste & Verify')).toBeInTheDocument();
    expect(screen.getByText('Document Extraction')).toBeInTheDocument();
  });

  it('updates the single email input', async () => {
    const props = setup();
    await userEvent.type(screen.getByPlaceholderText('target@example.com'), 'x@y.com');
    expect(props.setSingleEmail).toHaveBeenCalled();
  });

  it('submits the single verify form', async () => {
    const props = setup();
    await userEvent.click(screen.getByRole('button', { name: /Verify Email/i }));
    expect(props.handleSingleVerify).toHaveBeenCalled();
  });

  it('runs a bulk audit', async () => {
    const props = setup();
    await userEvent.click(screen.getByRole('button', { name: /Begin Bulk Audit/i }));
    expect(props.handleBulkVerify).toHaveBeenCalled();
  });

  it('runs a batch verify from pasted emails', async () => {
    const props = setup();
    await userEvent.click(screen.getByRole('button', { name: /Verify Batch/i }));
    expect(props.handleMultiVerify).toHaveBeenCalled();
  });

  it('shows a positive single result', () => {
    setup({ singleResult: { is_verified: true, message: 'looks good' } });
    expect(screen.getByText('Email Verified')).toBeInTheDocument();
    expect(screen.getByText('looks good')).toBeInTheDocument();
  });

  it('shows a negative single result', () => {
    setup({ singleResult: { is_verified: false, message: 'bad domain' } });
    expect(screen.getByText('Verification Failed')).toBeInTheDocument();
  });

  it('renders the results table with valid/invalid counts', () => {
    setup({
      verifierResults: [
        { email: 'a@x.com', is_verified: true, message: 'ok' },
        { email: 'b@x.com', is_verified: false, message: 'no mx' },
      ],
    });
    expect(screen.getByText('1 Valid')).toBeInTheDocument();
    expect(screen.getByText('1 Invalid')).toBeInTheDocument();
    expect(screen.getByText('a@x.com')).toBeInTheDocument();
  });

  it('handles a file upload', async () => {
    const props = setup();
    const file = new File(['a@x.com'], 'emails.csv', { type: 'text/csv' });
    const input = document.querySelector('input[type="file"]');
    await userEvent.upload(input, file);
    expect(props.handleFileVerify).toHaveBeenCalled();
  });

  it('disables action buttons while busy', () => {
    setup({ busy: true });
    const disabled = screen.getAllByRole('button').filter((b) => b.disabled);
    expect(disabled.length).toBeGreaterThanOrEqual(3);
  });
});
