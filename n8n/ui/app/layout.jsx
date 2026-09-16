import './globals.css';

export const metadata = {
  title: 'LeadGen · n8n Control',
  description: 'Trigger the LeadGen n8n webhook workflow and view generated leads.',
};

export const viewport = { width: 'device-width', initialScale: 1 };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
