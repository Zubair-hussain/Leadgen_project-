'use client';

import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import ConnectionStatus from '@/components/ConnectionStatus';

/**
 * Global app shell: renders the persistent connection indicator and toast host
 * around every page. Client component so browser-only providers work.
 */
export default function AppChrome({ children }) {
  return (
    <div className="flex flex-col min-h-screen">
      <div className="fixed top-4 right-4 z-50">
        <ConnectionStatus />
      </div>
      {children}
      <ToastContainer position="top-right" autoClose={3000} newestOnTop />
    </div>
  );
}
