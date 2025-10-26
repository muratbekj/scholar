import React, { useState, useEffect, useRef } from 'react';
import { FileText, ZoomIn, ZoomOut, RotateCcw, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loading } from '@/components/ui/loading';
import { apiService } from '@/lib/api';
import { PDFViewer, createHighlightsFromSourceReferences } from './PDFViewer';

interface DocumentStructure {
  pages: Array<{
    page_number: number;
    start_index: number;
    end_index: number;
    content?: string;
  }>;
  sections: Array<{
    title: string;
    start_index: number;
    end_index: number;
  }>;
  total_length: number;
  format_type: string;
}

interface DocumentContent {
  file_id: string;
  filename: string;
  full_text: string;
  document_structure: DocumentStructure;
  format: string;
  total_length: number;
}

interface Highlight {
  id: string;
  startIndex: number;
  endIndex: number;
  color: string;
  text: string;
  pageNumber?: number;
  sectionTitle?: string;
}

interface SourceReference {
  id: string;
  text: string;
  start_index: number;
  end_index: number;
  page_number?: number;
  section_title?: string;
  confidence: number;
  chunk_id?: string;
}

interface DocumentViewerProps {
  fileId?: string;
  filename?: string;
  highlights?: Highlight[];
  onHighlightClick?: (highlight: Highlight) => void;
  onSourceClick?: (source: SourceReference) => void;
  onClearHighlights?: () => void;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  fileId,
  filename,
  highlights = [],
  onHighlightClick,
  onSourceClick,
  onClearHighlights
}) => {
  const [documentContent, setDocumentContent] = useState<DocumentContent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(100);
  const [showHighlights, setShowHighlights] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50); // Number of lines per page
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Load document content when fileId changes
  useEffect(() => {
    if (fileId) {
      loadDocumentContent(fileId);
    }
  }, [fileId]);

  const loadDocumentContent = async (id: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const content = await apiService.getDocumentContent(id);
      setDocumentContent(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setIsLoading(false);
    }
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 10, 200));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 10, 50));
  };

  const handleResetZoom = () => {
    setZoom(100);
  };

  // Pagination logic
  const getPaginatedContent = () => {
    if (!documentContent) return { content: '', totalPages: 0 };
    
    const lines = documentContent.full_text.split('\n');
    const totalPages = Math.ceil(lines.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, lines.length);
    const paginatedLines = lines.slice(startIndex, endIndex);
    
    return {
      content: paginatedLines.join('\n'),
      totalPages,
      startLine: startIndex + 1,
      endLine: endIndex
    };
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleItemsPerPageChange = (items: number) => {
    setItemsPerPage(items);
    setCurrentPage(1); // Reset to first page
  };

  // Navigate to the page containing a highlight
  const navigateToHighlight = (highlight: Highlight) => {
    if (!documentContent) return;
    
    const lines = documentContent.full_text.split('\n');
    const highlightLine = lines.slice(0, highlight.startIndex).join('\n').split('\n').length;
    const targetPage = Math.ceil(highlightLine / itemsPerPage);
    
    if (targetPage !== currentPage) {
      setCurrentPage(targetPage);
    }
  };

  // Get pages that contain highlights
  const getPagesWithHighlights = () => {
    if (!documentContent || highlights.length === 0) return new Set();
    
    const lines = documentContent.full_text.split('\n');
    const pagesWithHighlights = new Set<number>();
    
    highlights.forEach(highlight => {
      const highlightLine = lines.slice(0, highlight.startIndex).join('\n').split('\n').length;
      const page = Math.ceil(highlightLine / itemsPerPage);
      pagesWithHighlights.add(page);
    });
    
    return pagesWithHighlights;
  };

  const scrollToHighlight = (highlight: Highlight) => {
    if (scrollAreaRef.current) {
      const element = scrollAreaRef.current.querySelector(`[data-highlight-id="${highlight.id}"]`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  };

  const renderHighlightedText = (text: string) => {
    if (!showHighlights || highlights.length === 0) {
      return <span>{text}</span>;
    }

    // Debug logging for highlighting issues
    console.log('DocumentViewer Debug:', {
      totalHighlights: highlights.length,
      documentLength: documentContent?.full_text.length,
      currentPageTextLength: text.length,
      showHighlights,
      highlights: highlights.map(h => ({
        id: h.id,
        startIndex: h.startIndex,
        endIndex: h.endIndex,
        text: h.text.substring(0, 50) + '...'
      }))
    });

    // Get pagination info to adjust highlight positions
    const { startLine, endLine } = getPaginatedContent();
    const lines = documentContent?.full_text.split('\n') || [];
    
    // Improved character index calculation
    let startCharIndex = 0;
    if (startLine && startLine > 1) {
      // Calculate character position more accurately
      const linesBefore = lines.slice(0, startLine - 1);
      startCharIndex = linesBefore.join('\n').length;
      // Add 1 for the newline character if there are lines before
      if (linesBefore.length > 0) {
        startCharIndex += 1;
      }
    }
    
    console.log('Pagination Debug:', {
      startLine,
      endLine,
      startCharIndex,
      currentPageTextLength: text.length,
      totalLines: lines.length
    });
    
    // Filter highlights that are within the current page
    const visibleHighlights = highlights.filter(highlight => {
      const isVisible = highlight.startIndex >= startCharIndex && 
             highlight.startIndex < startCharIndex + text.length;
      
      console.log('Highlight visibility check:', {
        highlightId: highlight.id,
        highlightStart: highlight.startIndex,
        pageStart: startCharIndex,
        pageEnd: startCharIndex + text.length,
        isVisible
      });
      
      return isVisible;
    });

    // Adjust highlight positions relative to the current page
    const adjustedHighlights = visibleHighlights.map(highlight => {
      const adjustedStart = Math.max(0, highlight.startIndex - startCharIndex);
      const adjustedEnd = Math.min(text.length, highlight.endIndex - startCharIndex);
      
      console.log('Highlight adjustment:', {
        originalStart: highlight.startIndex,
        originalEnd: highlight.endIndex,
        adjustedStart,
        adjustedEnd,
        textLength: text.length
      });
      
      return {
        ...highlight,
        startIndex: adjustedStart,
        endIndex: adjustedEnd
      };
    }).filter(highlight => {
      // Filter out invalid highlights
      const isValid = highlight.startIndex >= 0 && 
                     highlight.endIndex > highlight.startIndex && 
                     highlight.endIndex <= text.length;
      
      if (!isValid) {
        console.warn('Invalid highlight filtered out:', highlight);
      }
      
      return isValid;
    });

    // Sort highlights by start index
    const sortedHighlights = [...adjustedHighlights].sort((a, b) => a.startIndex - b.startIndex);
    
    let result: React.ReactNode[] = [];
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

      // Validate highlight text exists and is not empty
      const highlightText = text.slice(highlight.startIndex, highlight.endIndex);
      if (highlightText && highlightText.trim()) {
        // Add highlighted text
        result.push(
          <span
            key={`highlight-${highlight.id}`}
            data-highlight-id={highlight.id}
            className="cursor-pointer transition-colors hover:opacity-80"
            style={{
              backgroundColor: highlight.color,
              padding: '2px 4px',
              borderRadius: '3px',
              margin: '0 1px'
            }}
            onClick={() => {
              onHighlightClick?.(highlight);
              navigateToHighlight(highlight);
              // Small delay to ensure page navigation completes before scrolling
              setTimeout(() => scrollToHighlight(highlight), 100);
            }}
            title={`Page ${highlight.pageNumber || 'Unknown'}${highlight.sectionTitle ? ` - ${highlight.sectionTitle}` : ''}`}
          >
            {highlightText}
          </span>
        );
        
        lastIndex = highlight.endIndex;
      } else {
        console.warn('Empty or invalid highlight text:', {
          highlightId: highlight.id,
          startIndex: highlight.startIndex,
          endIndex: highlight.endIndex,
          textLength: text.length,
          highlightText
        });
      }
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
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loading message="Loading document..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-4">
        <FileText className="h-12 w-12 text-destructive mx-auto mb-4" />
        <h3 className="text-lg font-medium text-foreground mb-2">Error Loading Document</h3>
        <p className="text-destructive text-sm mb-4">{error}</p>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => fileId && loadDocumentContent(fileId)}
        >
          Try Again
        </Button>
      </div>
    );
  }

  if (!documentContent) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-4">
        <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-lg font-medium text-foreground mb-2">Document Viewer</h3>
        <p className="text-muted-foreground text-sm">
          {filename ? `Ready to display ${filename}` : 'No document selected'}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Document Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-foreground">Document Viewer</h2>
          <span className="text-sm text-muted-foreground">
            {documentContent.filename}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Zoom Controls */}
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleZoomOut}
              disabled={zoom <= 50}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-xs text-muted-foreground min-w-[3rem] text-center">
              {zoom}%
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleZoomIn}
              disabled={zoom >= 200}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetZoom}
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>

          {/* Highlight Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowHighlights(!showHighlights)}
            className={showHighlights ? 'text-accent-foreground' : 'text-muted-foreground'}
          >
            {showHighlights ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
          </Button>

          {/* Clear Highlights */}
          {highlights.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearHighlights}
              className="text-destructive hover:text-destructive"
            >
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Document Content */}
      {documentContent.format === 'pdf' ? (
        <div className="flex-1">
          <PDFViewer
            fileUrl={`/api/files/${fileId}/file`}
            highlights={highlights}
            onHighlightClick={onHighlightClick}
            className="h-full"
          />
        </div>
      ) : (
        <ScrollArea className="flex-1" ref={scrollAreaRef}>
          <div 
            className="p-4 prose prose-sm max-w-none dark:prose-invert"
            style={{ fontSize: `${zoom}%` }}
          >
            <div className="whitespace-pre-wrap leading-relaxed">
              {(() => {
                const { content } = getPaginatedContent();
                return renderHighlightedText(content);
              })()}
            </div>
          </div>
        </ScrollArea>
      )}

      {/* Document Footer */}
      <div className="flex items-center justify-between p-2 border-t border-border text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>Pages: {documentContent.document_structure?.pages?.length || 0}</span>
          <span>Sections: {documentContent.document_structure?.sections?.length || 0}</span>
          <span>Characters: {documentContent.total_length.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-2">
          {highlights.length > 0 && (
            <span className="text-accent-foreground">
              {highlights.length} highlight{highlights.length !== 1 ? 's' : ''} active
            </span>
          )}
        </div>
      </div>

      {/* Pagination Controls */}
      {documentContent && (
        <div className="flex items-center justify-between p-3 border-t border-border bg-muted/30">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Lines per page:</span>
            <select
              value={itemsPerPage}
              onChange={(e) => handleItemsPerPageChange(Number(e.target.value))}
              className="px-2 py-1 text-xs border border-border rounded bg-background"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
            {highlights.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const pagesWithHighlights = getPagesWithHighlights();
                  if (pagesWithHighlights.size > 0) {
                    const firstHighlightPage = Math.min(...Array.from(pagesWithHighlights).map(Number));
                    handlePageChange(firstHighlightPage);
                  }
                }}
                className="h-6 px-2 text-xs"
              >
                Jump to Highlight
              </Button>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handlePageChange(1)}
              disabled={currentPage === 1}
              className="h-6 px-2 text-xs"
            >
              First
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="h-6 px-2 text-xs"
            >
              Previous
            </Button>
            
            <span className="text-sm">
              Page {currentPage} of {getPaginatedContent().totalPages}
              {getPagesWithHighlights().has(currentPage) && (
                <span className="ml-2 text-accent-foreground">●</span>
              )}
            </span>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= getPaginatedContent().totalPages}
              className="h-6 px-2 text-xs"
            >
              Next
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handlePageChange(getPaginatedContent().totalPages)}
              disabled={currentPage >= getPaginatedContent().totalPages}
              className="h-6 px-2 text-xs"
            >
              Last
            </Button>
          </div>
          
          <div className="text-xs text-muted-foreground">
            Lines {getPaginatedContent().startLine}-{getPaginatedContent().endLine}
          </div>
        </div>
      )}
    </div>
  );
};
