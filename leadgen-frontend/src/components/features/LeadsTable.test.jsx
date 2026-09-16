import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LeadsTable from './LeadsTable';

const leads = [
  { id: 1, email: 'a@x.com', is_verified: true, source: 'reddit', location: 'NYC', link: 'https://x.com/a', created_at: '2024-01-01' },
  { id: 2, email: 'b@y.com', is_verified: false, source: 'maps', location: '', link: '', created_at: '2024-01-02' },
];

function setup(overrides = {}) {
  const props = {
    leads,
    handleVerify: vi.fn(),
    handleDelete: vi.fn(),
    verifying: {},
    handleExport: vi.fn(),
    ...overrides,
  };
  render(<LeadsTable {...props} />);
  return props;
}

describe('LeadsTable', () => {
  it('renders the empty state with no leads', () => {
    setup({ leads: [] });
    expect(screen.getByText('No leads found')).toBeInTheDocument();
  });

  it('renders lead rows and verified/pending counts', () => {
    setup();
    expect(screen.getByText('a@x.com')).toBeInTheDocument();
    expect(screen.getByText('b@y.com')).toBeInTheDocument();
    expect(screen.getByText(/2 contacts discovered/)).toBeInTheDocument();
  });

  it('exports when the export button is clicked', async () => {
    const props = setup();
    await userEvent.click(screen.getByRole('button', { name: /Export CSV/i }));
    expect(props.handleExport).toHaveBeenCalled();
  });

  it('verifies an unverified lead', async () => {
    const props = setup();
    await userEvent.click(screen.getByRole('button', { name: /Verify/i }));
    expect(props.handleVerify).toHaveBeenCalledWith(2);
  });

  it('shows a verifying spinner state', () => {
    setup({ verifying: { 2: true } });
    expect(screen.getByText('Verifying...')).toBeInTheDocument();
  });

  it('deletes a lead', async () => {
    const props = setup();
    const deleteButtons = screen.getAllByTitle('Delete lead');
    await userEvent.click(deleteButtons[0]);
    expect(props.handleDelete).toHaveBeenCalledWith(1);
  });

  it('renders the host name for a lead with a link', () => {
    setup();
    expect(screen.getByText('x.com')).toBeInTheDocument();
  });
});
