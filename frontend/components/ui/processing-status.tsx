"use client"

import React from 'react';
import { CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';

interface ProcessingStep {
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  details?: string;
  duration?: number;
}

interface ProcessingStatusProps {
  steps: ProcessingStep[];
  totalTime?: number;
  isComplete?: boolean;
  error?: string;
}

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({
  steps,
  totalTime,
  isComplete = false,
  error
}) => {
  const getStepIcon = (status: ProcessingStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStepColor = (status: ProcessingStep['status']) => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'processing':
        return 'text-blue-600';
      case 'error':
        return 'text-red-600';
      case 'pending':
      default:
        return 'text-gray-500';
    }
  };

  return (
    <Card className="p-4 bg-muted/30 border-dashed">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-foreground">Processing Status</h4>
          {isComplete && totalTime && (
            <span className="text-sm text-muted-foreground">
              Completed in {totalTime.toFixed(1)}s
            </span>
          )}
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        <div className="space-y-2">
          {steps.map((step, index) => (
            <div key={index} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getStepIcon(step.status)}
                <span className={`text-sm ${getStepColor(step.status)}`}>
                  {step.name}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {step.details && <span>{step.details}</span>}
                {step.duration && <span>({step.duration.toFixed(1)}s)</span>}
              </div>
            </div>
          ))}
        </div>

        {!isComplete && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Processing your document...</span>
          </div>
        )}
      </div>
    </Card>
  );
};
