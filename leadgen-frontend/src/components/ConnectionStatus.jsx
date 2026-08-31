import { useEffect, useState } from 'react';
import { checkBackendHealth } from '../services/api';

export default function ConnectionStatus() {
  const [connected, setConnected] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkConnection = async () => {
      setLoading(true);
      const result = await checkBackendHealth();
      setConnected(result.connected);
      setLoading(false);
    };

    // Check on mount
    checkConnection();

    // Re-check every 10 seconds
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-800">
        <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse"></div>
        <span className="text-xs text-gray-600 dark:text-gray-400">Checking...</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
      connected 
        ? 'bg-green-100 dark:bg-green-900/30' 
        : 'bg-red-100 dark:bg-red-900/30'
    }`}>
      <div className={`w-2 h-2 rounded-full ${
        connected 
          ? 'bg-green-500' 
          : 'bg-red-500'
      }`}></div>
      <span className={`text-xs font-medium ${
        connected 
          ? 'text-green-700 dark:text-green-400' 
          : 'text-red-700 dark:text-red-400'
      }`}>
        {connected ? 'Backend Connected' : 'Backend Disconnected'}
      </span>
    </div>
  );
}
