import '@testing-library/jest-dom/vitest';

// Ensure the API base URL is defined before modules read it at import time.
process.env.NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
