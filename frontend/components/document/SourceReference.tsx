import React from 'react';
import { FileText, MapPin, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SourceReference as ApiSourceReference } from '@/lib/api';
import { getHighlightColorBySourceId } from '@/lib/constants/colors';

interface SourceReferenceProps {
  source: ApiSourceReference;
  onClick: (source: ApiSourceReference) => void;
  isHighlighted?: boolean;
  color?: string;
}

export const SourceReference: React.FC<SourceReferenceProps> = ({
  source,
  onClick,
  isHighlighted = false,
  color = '#fbbf24' // Default yellow color
}) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceText = (confidence: number) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  return (
    <div className="inline-block">
      <Button
        variant="outline"
        size="sm"
        className={`
          relative inline-flex items-center gap-1 px-2 py-1 text-xs
          transition-all duration-200 hover:scale-105
          ${isHighlighted ? 'ring-2 ring-accent ring-offset-1' : ''}
        `}
        style={{
          backgroundColor: isHighlighted ? color : 'transparent',
          borderColor: color,
          color: isHighlighted ? 'white' : 'inherit'
        }}
        onClick={() => onClick(source)}
      >
        <FileText className="h-3 w-3" />
        <span className="font-medium">
          Source {source.page_number ? `Page ${source.page_number}` : 'Reference'}
        </span>
        {source.section_title && (
          <>
            <span className="text-muted-foreground">•</span>
            <span className="text-muted-foreground truncate max-w-20">
              {source.section_title}
            </span>
          </>
        )}
        <div className="flex items-center gap-1 ml-1">
          <span className={`text-xs ${getConfidenceColor(source.confidence)}`}>
            {getConfidenceText(source.confidence)}
          </span>
          <Eye className="h-3 w-3 opacity-60" />
        </div>
      </Button>
    </div>
  );
};

interface SourceReferencesProps {
  sources: ApiSourceReference[];
  onSourceClick: (source: ApiSourceReference) => void;
  highlightedSourceIds?: string[];
  className?: string;
}

export const SourceReferences: React.FC<SourceReferencesProps> = ({
  sources,
  onSourceClick,
  highlightedSourceIds = [],
  className = ''
}) => {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <MapPin className="h-3 w-3" />
        <span>Sources ({sources.length})</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {sources.map((source) => (
          <SourceReference
            key={source.id}
            source={source}
            onClick={onSourceClick}
            isHighlighted={highlightedSourceIds.includes(source.id)}
            color={getHighlightColorBySourceId(source.id, sources.length)}
          />
        ))}
      </div>
    </div>
  );
};
