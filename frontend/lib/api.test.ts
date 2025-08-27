// Simple test to verify API service configuration
import { apiService } from './api';

// Test API base URL configuration
console.log('API Base URL:', process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

// Test that apiService is properly configured
console.log('API Service configured:', !!apiService);

// Export for testing
export { apiService };
