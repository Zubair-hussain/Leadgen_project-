import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './Button';

describe('Button', () => {
  it('renders its children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('fires onClick when enabled', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    await userEvent.click(screen.getByRole('button', { name: 'Go' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('does not fire onClick when disabled', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick} disabled>Go</Button>);
    const button = screen.getByRole('button', { name: 'Go' });
    expect(button).toBeDisabled();
    await userEvent.click(button).catch(() => {});
    expect(onClick).not.toHaveBeenCalled();
  });

  it.each(['primary', 'secondary', 'accent'])('applies the %s variant', (variant) => {
    render(<Button variant={variant}>V</Button>);
    expect(screen.getByRole('button', { name: 'V' })).toBeInTheDocument();
  });

  it('merges extra className', () => {
    render(<Button className="extra-class">V</Button>);
    expect(screen.getByRole('button', { name: 'V' }).className).toContain('extra-class');
  });
});
