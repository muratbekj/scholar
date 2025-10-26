import React, { useMemo } from 'react';

interface Highlight {
  id: string;
  startIndex: number;
  endIndex: number;
  color: string;
  text: string;
  pageNumber?: number;
  sectionTitle?: string;
}

interface HighlightableTextProps {
  text: string;
  highlights: Highlight[];
  onHighlightClick?: (highlight: Highlight) => void;
  className?: string;
}

export const HighlightableText: React.FC<HighlightableTextProps> = ({
  text,
  highlights,
  onHighlightClick,
  className = ''
}) => {
  const highlightedContent = useMemo(() => {
    if (!highlights || highlights.length === 0) {
      return <span>{text}</span>;
    }

    // Sort highlights by start index to avoid conflicts
    const sortedHighlights = [...highlights].sort((a, b) => a.startIndex - b.startIndex);
    
    const result: React.ReactNode[] = [];
    let lastIndex = 0;

    sortedHighlights.forEach((highlight, index) => {
      // Add text before highlight
      if (highlight.startIndex > lastIndex) {
        result.push(
          <span key={`text-${index}`}>
            {text.slice(lastIndex, highlight.startIndex)}
          </span>
        );
      }

      // Add highlighted text
      result.push(
        <span
          key={`highlight-${highlight.id}`}
          data-highlight-id={highlight.id}
          className="cursor-pointer transition-all duration-200 hover:opacity-80 hover:shadow-sm"
          style={{
            backgroundColor: highlight.color,
            padding: '2px 4px',
            borderRadius: '3px',
            margin: '0 1px',
            display: 'inline-block'
          }}
          onClick={() => onHighlightClick?.(highlight)}
          title={`Page ${highlight.pageNumber || 'Unknown'}${highlight.sectionTitle ? ` - ${highlight.sectionTitle}` : ''}`}
        >
          {text.slice(highlight.startIndex, highlight.endIndex)}
        </span>
      );

      lastIndex = highlight.endIndex;
    });

    // Add remaining text
    if (lastIndex < text.length) {
      result.push(
        <span key="text-end">
          {text.slice(lastIndex)}
        </span>
      );
    }

    return <>{result}</>;
  }, [text, highlights, onHighlightClick]);

  return (
    <div className={`whitespace-pre-wrap leading-relaxed ${className}`}>
      {highlightedContent}
    </div>
  );
};
