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
          <div className="w-48 h-2 bg-muted rounded-full overflow-hidden shadow-inner">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 transition-all duration-500 ease-out relative overflow-hidden"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_2s_ease-in-out_infinite]" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
