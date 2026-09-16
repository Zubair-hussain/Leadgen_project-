import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const { apiMock, signOut } = vi.hoisted(() => ({
  apiMock: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
  signOut: vi.fn(),
}));

vi.mock('../services/api', () => ({ default: apiMock, clearTokens: vi.fn() }));
vi.mock('firebase/auth', () => ({ signOut: (...a) => signOut(...a) }));
vi.mock('../firebase', () => ({ auth: {} }));

import Dashboard from './Dashboard';

const sampleLead = {
  id: 1,
  email: 'lead@example.com',
  is_verified: false,
  source: 'reddit',
  location: 'US',
  link: 'https://reddit.com/x',
  created_at: '2024-01-01',
};

function mockInitialLoad(leads = [sampleLead]) {
  apiMock.get.mockImplementation((url) => {
    if (url.startsWith('leads/?')) {
      return Promise.resolve({ data: { results: leads, count: leads.length, next: null } });
    }
    if (url === 'health/') {
      return Promise.resolve({ data: { sender: { email: 'sender@example.com' } } });
    }
    if (url.startsWith('leads/export')) {
      return Promise.resolve({ data: new Blob(['csv']) });
    }
    return Promise.resolve({ data: {} });
  });
}

beforeEach(() => {
  apiMock.get.mockReset();
  apiMock.post.mockReset();
  apiMock.delete.mockReset();
  signOut.mockReset();
  vi.spyOn(window, 'alert').mockImplementation(() => {});
  globalThis.URL.createObjectURL = vi.fn(() => 'blob:url');
  globalThis.URL.revokeObjectURL = vi.fn();
  mockInitialLoad();
});

describe('Dashboard', () => {
  it('loads leads and the sender identity on mount', async () => {
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalledWith('leads/?page_size=100'));
    await waitFor(() => expect(apiMock.get).toHaveBeenCalledWith('health/'));
    expect(screen.getByText('Lead Extraction Engine')).toBeInTheDocument();
  });

  it('validates the generator form and alerts when niche is missing', async () => {
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Run Extraction'));
    await waitFor(() => expect(window.alert).toHaveBeenCalled());
    expect(apiMock.post).not.toHaveBeenCalled();
  });

  it('submits a valid generation request', async () => {
    apiMock.post.mockResolvedValue({ data: { leads: [], message: 'done' } });
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());

    const selects = container.querySelectorAll('select');
    fireEvent.change(selects[0], { target: { value: 'SaaS' } });
    fireEvent.change(selects[1], { target: { value: 'US' } });

    fireEvent.click(screen.getByText('Run Extraction'));
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith('generate/', expect.objectContaining({ category: 'SaaS' })));
  });

  it('switches to the Leads tab and exports CSV', async () => {
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Leads Hub'));
    await waitFor(() => expect(screen.getByText('Export CSV')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Export CSV'));
    await waitFor(() => expect(apiMock.get).toHaveBeenCalledWith('leads/export/', expect.any(Object)));
  });

  it('verifies a lead from the Leads tab', async () => {
    apiMock.post.mockResolvedValue({ data: { is_verified: true, message: 'ok' } });
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Leads Hub'));
    const verifyBtn = await screen.findByText('Verify');
    fireEvent.click(verifyBtn);
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith('leads/1/verify/'));
  });

  it('deletes a lead from the Leads tab', async () => {
    apiMock.delete.mockResolvedValue({ data: {} });
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Leads Hub'));
    await screen.findByText('lead@example.com');
    const delBtn = container.querySelector('button.bd');
    fireEvent.click(delBtn);
    await waitFor(() => expect(apiMock.delete).toHaveBeenCalledWith('leads/1/'));
  });

  it('filters leads with the search box', async () => {
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Leads Hub'));
    await screen.findByText('lead@example.com');
    fireEvent.change(container.querySelector('input[placeholder="Search email, source…"]'), {
      target: { value: 'nomatch' },
    });
    expect(screen.getByText('No leads found')).toBeInTheDocument();
  });

  it('verifies a single email in the Verifier tab', async () => {
    apiMock.post.mockResolvedValue({ data: { is_verified: true } });
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Verifier'));
    fireEvent.change(await screen.findByPlaceholderText('hello@company.com'), {
      target: { value: 'a@b.com' },
    });
    fireEvent.click(screen.getByText('Verify Now'));
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith('leads/verify-single/', { email: 'a@b.com' }));
    await waitFor(() => expect(screen.getByText('Valid')).toBeInTheDocument());
  });

  it('runs a batch verify in the Verifier tab', async () => {
    apiMock.post.mockResolvedValue({ data: { results: [{ email: 'a@b.com', is_verified: false }] } });
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Verifier'));
    const textarea = container.querySelector('textarea.ta');
    fireEvent.change(textarea, { target: { value: 'a@b.com, c@d.com' } });
    fireEvent.click(screen.getByText('Run Batch'));
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith('leads/verify-multi/', { emails: ['a@b.com', 'c@d.com'] }));
  });

  it('runs a deliverability policy check in the Sender tab', async () => {
    apiMock.post.mockResolvedValue({
      data: {
        score: 82,
        status: 'inbox_ready',
        inbox_prediction: 'Likely inbox',
        checks: [{ key: 'spf', label: 'SPF', detail: 'ok', passed: true }],
        recommendations: ['Add DMARC'],
      },
    });
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Sender'));
    fireEvent.click(await screen.findByText('Run Policy Check'));
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith('deliverability/check/', expect.objectContaining({ subject: 'Quick question' })));
    await waitFor(() => expect(screen.getByText('Likely inbox')).toBeInTheDocument());
    expect(screen.getByText('Low Risk')).toBeInTheDocument();
  });

  it('surfaces a deliverability policy error', async () => {
    apiMock.post.mockRejectedValue({ response: { data: { error: 'bad sender' } } });
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Sender'));
    fireEvent.click(await screen.findByText('Run Policy Check'));
    await waitFor(() => expect(screen.getByText('bad sender')).toBeInTheDocument());
  });

  it('shows an alert when generation returns leads', async () => {
    apiMock.post.mockResolvedValue({ data: { leads: [{ id: 9, email: 'new@x.com' }] } });
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    const selects = container.querySelectorAll('select');
    fireEvent.change(selects[0], { target: { value: 'SaaS' } });
    fireEvent.change(selects[1], { target: { value: 'US' } });
    fireEvent.click(screen.getByText('Run Extraction'));
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('Generated 1 leads')));
  });

  it('toggles dark mode and signs out', async () => {
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Sign Out'));
    expect(signOut).toHaveBeenCalled();
  });

  it('alerts when generation returns no leads', async () => {
    apiMock.post.mockResolvedValue({ data: { leads: [] } });
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    const selects = container.querySelectorAll('select');
    fireEvent.change(selects[0], { target: { value: 'SaaS' } });
    fireEvent.change(selects[1], { target: { value: 'US' } });
    fireEvent.click(screen.getByText('Run Extraction'));
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('No leads found')));
  });

  it('alerts on a generation error', async () => {
    apiMock.post.mockRejectedValue({ response: { data: { error: 'server boom' } } });
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    const selects = container.querySelectorAll('select');
    fireEvent.change(selects[0], { target: { value: 'SaaS' } });
    fireEvent.change(selects[1], { target: { value: 'US' } });
    fireEvent.click(screen.getByText('Run Extraction'));
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('server boom')));
  });

  it('alerts when CSV export fails', async () => {
    apiMock.get.mockImplementation((url) => {
      if (url.startsWith('leads/export')) return Promise.reject(new Error('nope'));
      if (url.startsWith('leads/?')) return Promise.resolve({ data: { results: [sampleLead], count: 1, next: null } });
      return Promise.resolve({ data: {} });
    });
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    fireEvent.click(screen.getByText('Leads Hub'));
    fireEvent.click(await screen.findByText('Export CSV'));
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('Export failed')));
  });

  it('resets the generator form', async () => {
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    const selects = container.querySelectorAll('select');
    fireEvent.change(selects[0], { target: { value: 'SaaS' } });
    fireEvent.click(screen.getByText('Reset'));
    expect(container.querySelectorAll('select')[0].value).toBe('');
  });

  it('toggles dark mode from the topbar', async () => {
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    const root = container.querySelector('#lfr');
    const themeBtns = container.querySelectorAll('.topbar .ibtn');
    fireEvent.click(themeBtns[1]);
    expect(root.hasAttribute('data-dark')).toBe(true);
  });

  it('opens and closes the mobile menu', async () => {
    const { container } = render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    const menuBtn = container.querySelector('.topbar .ibtn');
    fireEvent.click(menuBtn);
    expect(container.querySelector('aside.sb.mob')).toBeTruthy();
  });

  it('recovers from a failed initial load', async () => {
    apiMock.get.mockRejectedValue(new Error('down'));
    render(<Dashboard />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    expect(screen.getByText('Lead Extraction Engine')).toBeInTheDocument();
  });
});
