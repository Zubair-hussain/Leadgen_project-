import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GeneratorForm from './GeneratorForm';

const baseForm = { niche: '', country: '', platforms: [], is_professional: false };

function setup(overrides = {}) {
  const props = {
    form: { ...baseForm, ...(overrides.form || {}) },
    setForm: vi.fn(),
    busy: false,
    handleGenerate: vi.fn((e) => e && e.preventDefault && e.preventDefault()),
    togglePlatform: vi.fn(),
    ...overrides,
  };
  render(<GeneratorForm {...props} />);
  return props;
}

describe('GeneratorForm', () => {
  it('renders headline and platform choices', () => {
    setup();
    expect(screen.getByText('Find Your Perfect Leads')).toBeInTheDocument();
    expect(screen.getByText('Reddit')).toBeInTheDocument();
    expect(screen.getByText('Google Maps')).toBeInTheDocument();
  });

  it('updates the niche field', async () => {
    const props = setup();
    await userEvent.type(screen.getByPlaceholderText(/Real Estate Agents/), 'Dentists');
    expect(props.setForm).toHaveBeenCalled();
  });

  it('updates the location field', async () => {
    const props = setup();
    await userEvent.type(screen.getByPlaceholderText(/New York, London/), 'Austin');
    expect(props.setForm).toHaveBeenCalled();
  });

  it('toggles a platform on click', async () => {
    const props = setup();
    await userEvent.click(screen.getByText('Reddit'));
    expect(props.togglePlatform).toHaveBeenCalledWith('reddit');
  });

  it('disables submit until required fields are filled', () => {
    setup();
    expect(screen.getByRole('button', { name: /START AI DISCOVERY/i })).toBeDisabled();
  });

  it('enables submit and calls handleGenerate when valid', async () => {
    const props = setup({ form: { niche: 'SaaS', country: 'US', platforms: ['reddit'] } });
    const submit = screen.getByRole('button', { name: /START AI DISCOVERY/i });
    expect(submit).toBeEnabled();
    await userEvent.click(submit);
    expect(props.handleGenerate).toHaveBeenCalled();
  });

  it('reveals the professional toggle when google-maps is selected', () => {
    setup({ form: { platforms: ['google-maps'] } });
    expect(screen.getByText('Professional Deep Search')).toBeInTheDocument();
  });

  it('does not show the professional toggle without google-maps', () => {
    setup({ form: { platforms: ['reddit'] } });
    expect(screen.queryByText('Professional Deep Search')).not.toBeInTheDocument();
  });

  it('shows the scanning hint while busy', () => {
    setup({ busy: true });
    expect(screen.getByText(/AI is scanning multiple platforms/)).toBeInTheDocument();
  });
});
