"use client"

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { apiService } from '@/lib/api';

export const ApiTest = () => {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const testConnection = async () => {
    setStatus('loading');
    setMessage('Testing connection...');
    
    try {
      const health = await apiService.healthCheck();
      setStatus('success');
      setMessage(`Backend is healthy: ${health.service}`);
    } catch (error) {
      setStatus('error');
      setMessage(`Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="p-4 border rounded-lg">
      <h3 className="text-lg font-semibold mb-2">API Connection Test</h3>
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">
          Backend URL: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
        </p>
        <Button 
          onClick={testConnection} 
          disabled={status === 'loading'}
          variant={status === 'success' ? 'default' : status === 'error' ? 'destructive' : 'outline'}
        >
          {status === 'loading' ? 'Testing...' : 'Test Connection'}
        </Button>
        {message && (
          <p className={`text-sm ${status === 'success' ? 'text-green-600' : status === 'error' ? 'text-red-600' : 'text-muted-foreground'}`}>
            {message}
          </p>
        )}
      </div>
    </div>
  );
};
