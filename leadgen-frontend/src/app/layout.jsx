import './globals.css';
import AppChrome from '@/components/AppChrome';

export const metadata = {
  title: 'LeadGen AI',
  description: 'AI-powered B2B lead discovery, verification, and deliverability.',
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
