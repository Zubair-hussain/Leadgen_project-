import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Sidebar from './Sidebar';

function setup(overrides = {}) {
  const props = {
    tab: 'generator',
    setTab: vi.fn(),
    mobileOpen: true,
    setMobileOpen: vi.fn(),
    darkMode: false,
    setDarkMode: vi.fn(),
    handleLogout: vi.fn(),
    ...overrides,
  };
  render(<Sidebar {...props} />);
  return props;
}

describe('Sidebar', () => {
  beforeEach(() => {
    window.innerWidth = 1280;
  });

  it('renders the navigation items', () => {
    setup();
    expect(screen.getByText('Lead Generator')).toBeInTheDocument();
    expect(screen.getByText('Data Warehouse')).toBeInTheDocument();
    expect(screen.getByText('Bulk Verifier')).toBeInTheDocument();
  });

  it('switches tabs when an item is clicked', async () => {
    const props = setup();
    await userEvent.click(screen.getByText('Data Warehouse'));
    expect(props.setTab).toHaveBeenCalledWith('leads');
  });

  it('toggles dark mode', async () => {
    const props = setup();
    await userEvent.click(screen.getByRole('button', { name: /Dark Mode/i }));
    expect(props.setDarkMode).toHaveBeenCalledWith(true);
  });

  it('shows Light Mode label when dark mode is active', () => {
    setup({ darkMode: true });
    expect(screen.getByText('Light Mode')).toBeInTheDocument();
  });

  it('logs out', async () => {
    const props = setup();
    await userEvent.click(screen.getByRole('button', { name: /Sign Out/i }));
    expect(props.handleLogout).toHaveBeenCalled();
  });

  it('closes on mobile when a tab is selected', async () => {
    window.innerWidth = 500;
    const props = setup({ mobileOpen: true });
    await userEvent.click(screen.getByText('Bulk Verifier'));
    expect(props.setMobileOpen).toHaveBeenCalledWith(false);
  });
});
