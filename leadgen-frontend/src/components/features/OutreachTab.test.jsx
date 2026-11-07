import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const { apiMock } = vi.hoisted(() => ({
  apiMock: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

vi.mock('../../services/api', () => ({ default: apiMock }));

import OutreachTab from './OutreachTab';

const status = {
  gmail_configured: false, dry_run: true, from_email: 'me@mydomain.com', in_send_window: true,
  sent_today: 1, sent_last_hour: 0, daily_limit: 10, hourly_limit: 5, queued: 0, next_send_at: null,
};
const draftMessage = {
  id: 7, to_email: 'james@dental.co.uk', subject: 'A concept for ABC Dental', body: 'Hi James',
  status: 'draft', warnings: [], skip_reason: '', error: '', dry_run: false,
};
const leads = [
  { id: 1, email: 'james@dental.co.uk', is_verified: true },
  { id: 2, email: 'unverified@x.co.uk', is_verified: false },
];

beforeEach(() => {
  apiMock.get.mockReset();
  apiMock.post.mockReset();
  apiMock.delete.mockReset();
  apiMock.get.mockImplementation((url) => {
    if (url === 'outreach/status/') return Promise.resolve({ data: status });
    if (url.startsWith('outreach/messages/')) return Promise.resolve({ data: { results: [draftMessage] } });
    if (url === 'outreach/suppressions/') return Promise.resolve({ data: { results: [{ id: 3, email: 'no@thanks.co.uk', reason: 'opt_out' }] } });
    return Promise.resolve({ data: {} });
  });
  apiMock.post.mockResolvedValue({ data: {} });
  apiMock.delete.mockResolvedValue({ data: {} });
});

describe('OutreachTab', () => {
  it('shows dry-run status, limits, messages and suppressions', async () => {
    render(<OutreachTab leads={leads} />);
    expect(await screen.findByText(/Dry run: nothing is really sent/)).toBeInTheDocument();
    expect(screen.getByText('1 / 10')).toBeInTheDocument();
    expect(screen.getByText('A concept for ABC Dental')).toBeInTheDocument();
    expect(screen.getByText(/no@thanks.co.uk/)).toBeInTheDocument();
    // Only verified leads are offered.
    expect(screen.getByRole('option', { name: 'james@dental.co.uk' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'unverified@x.co.uk' })).not.toBeInTheDocument();
  });

  it('saves a draft for the chosen lead', async () => {
    render(<OutreachTab leads={leads} />);
    await screen.findByText('A concept for ABC Dental');
    await userEvent.selectOptions(screen.getByLabelText('Verified lead'), '1');
    await userEvent.type(screen.getByLabelText('Subject'), 'Hello');
    await userEvent.type(screen.getByLabelText('Body'), 'Hi there');
    await userEvent.click(screen.getByRole('button', { name: 'Save draft' }));
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith(
      'outreach/messages/', { lead_id: 1, subject: 'Hello', body: 'Hi there' },
    ));
    expect(await screen.findByText(/Draft saved/)).toBeInTheDocument();
  });

  it('approves a draft and shows safety-check problems', async () => {
    apiMock.post.mockRejectedValueOnce({ response: { data: { problems: ['Recipient is on the suppression list.'] } } });
    render(<OutreachTab leads={leads} />);
    await userEvent.click(await screen.findByRole('button', { name: /Approve/ }));
    expect(apiMock.post).toHaveBeenCalledWith('outreach/messages/7/approve/');
    expect(await screen.findByText('Recipient is on the suppression list.')).toBeInTheDocument();
  });

  it('cancels, deletes, blocks and unblocks', async () => {
    render(<OutreachTab leads={leads} />);
    await userEvent.click(await screen.findByRole('button', { name: /Cancel/ }));
    expect(apiMock.post).toHaveBeenCalledWith('outreach/messages/7/cancel/');
    await userEvent.click(screen.getByRole('button', { name: 'Delete draft' }));
    expect(apiMock.delete).toHaveBeenCalledWith('outreach/messages/7/');
    await userEvent.type(screen.getByLabelText('Email to block'), 'stop@me.co.uk');
    await userEvent.click(screen.getByRole('button', { name: /Block/ }));
    expect(apiMock.post).toHaveBeenCalledWith('outreach/suppressions/', { email: 'stop@me.co.uk', reason: 'manual' });
    await userEvent.click(screen.getByRole('button', { name: 'Unblock no@thanks.co.uk' }));
    expect(apiMock.delete).toHaveBeenCalledWith('outreach/suppressions/3/');
  });

  it('switches filters and reports load errors', async () => {
    render(<OutreachTab leads={[]} />);
    await screen.findByText('A concept for ABC Dental');
    apiMock.get.mockRejectedValueOnce({ message: 'Network Error' });
    await userEvent.click(screen.getByRole('button', { name: 'Sent' }));
    expect(apiMock.get).toHaveBeenCalledWith('outreach/messages/?page_size=100&status=sent');
    expect(await screen.findByText('Network Error')).toBeInTheDocument();
  });
});
