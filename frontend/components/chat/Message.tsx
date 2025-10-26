import React from 'react';
import { User, Bot, Clock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { QAMessage, SourceReference } from '@/lib/api';
import { SourceReferences } from '@/components/document/SourceReference';

interface MessageProps {
  message: QAMessage;
  isUser: boolean;
  onSourceClick?: (source: SourceReference) => void;
  highlightedSourceIds?: string[];
}

export const Message: React.FC<MessageProps> = ({ message, isUser, onSourceClick, highlightedSourceIds = [] }) => {
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
          <div className="text-sm leading-relaxed prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              components={{
                // Customize heading styles
                h1: ({children}) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                h2: ({children}) => <h2 className="text-base font-semibold mb-2">{children}</h2>,
                h3: ({children}) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
                // Customize list styles
                ul: ({children}) => <ul className="list-disc list-inside space-y-1 mb-2">{children}</ul>,
                ol: ({children}) => <ol className="list-decimal list-inside space-y-1 mb-2">{children}</ol>,
                // Customize paragraph styles
                p: ({children}) => <p className="mb-2">{children}</p>,
                // Customize strong/bold text
                strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                // Customize emphasis/italic text
                em: ({children}) => <em className="italic">{children}</em>,
                // Customize code blocks
                code: ({children, className}) => {
                  const isInline = !className;
                  if (isInline) {
                    return <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>;
                  }
                  return <code className="block bg-muted p-2 rounded text-xs font-mono overflow-x-auto">{children}</code>;
                },
                // Customize blockquotes
                blockquote: ({children}) => <blockquote className="border-l-4 border-border pl-4 italic text-muted-foreground">{children}</blockquote>,
              }}
            >
              {message.content || ''}
            </ReactMarkdown>
          </div>
          
          {/* Show sources for assistant messages */}
          {!isUser && message.metadata?.rag_context && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs text-muted-foreground mb-2">Sources:</p>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">
                  • {message.metadata.rag_context.chunk_count} relevant sections found
                </p>
                {message.metadata.rag_context.source_positions && onSourceClick && (
                  <SourceReferences
                    sources={message.metadata.rag_context.source_positions}
                    onSourceClick={onSourceClick}
                    highlightedSourceIds={highlightedSourceIds}
                    className="mt-2"
                  />
                )}
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
