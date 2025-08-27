import React from 'react';
import { User, Bot, Clock } from 'lucide-react';
import { QAMessage } from '@/lib/api';

interface MessageProps {
  message: QAMessage;
  isUser: boolean;
}

export const Message: React.FC<MessageProps> = ({ message, isUser }) => {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-accent rounded-full flex items-center justify-center">
          <Bot className="h-4 w-4 text-accent-foreground" />
        </div>
      )}
      
      <div
        className={`max-w-[70%] p-4 rounded-lg ${
          isUser
            ? 'bg-accent text-accent-foreground'
            : 'bg-card text-card-foreground border border-border'
        }`}
      >
        <div className="space-y-2">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
          
          {/* Show sources for assistant messages */}
          {!isUser && message.metadata?.rag_context && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs text-muted-foreground mb-1">Sources:</p>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">
                  • {message.metadata.rag_context.chunk_count} relevant sections found
                </p>
              </div>
            </div>
          )}
          
          <div className="flex items-center gap-1 text-xs opacity-60">
            <Clock className="h-3 w-3" />
            <span>{formatTime(message.timestamp)}</span>
          </div>
        </div>
      </div>
      
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-muted rounded-full flex items-center justify-center">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      )}
    </div>
  );
};
