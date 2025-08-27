import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingProps {
  message?: string;
  progress?: number;
  showProgress?: boolean;
}

export const Loading: React.FC<LoadingProps> = ({ 
  message = "Processing...", 
  progress, 
  showProgress = false 
}) => {
  return (
    <div className="flex flex-col items-center justify-center space-y-4 p-8">
      <div className="relative">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
        {showProgress && progress !== undefined && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs font-medium text-accent-foreground">
              {Math.round(progress)}%
            </span>
          </div>
        )}
      </div>
      
      <div className="text-center space-y-2">
        <p className="text-sm font-medium text-foreground">{message}</p>
        {showProgress && progress !== undefined && (
          <div className="w-48 h-2 bg-muted rounded-full overflow-hidden">
            <div 
              className="h-full bg-accent transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
};
