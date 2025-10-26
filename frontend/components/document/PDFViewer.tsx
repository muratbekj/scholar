import React, { useState } from 'react';

interface HighlightArea {
  pageIndex: number;
  left: number;
  top: number;
  width: number;
  height: number;
  color?: string;
  opacity?: number;
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

interface PDFViewerProps {
  fileUrl: string;
  highlights?: Highlight[];
  onHighlightClick?: (highlight: Highlight) => void;
  className?: string;
}

// Simple PDF viewer using iframe (no react-pdf dependencies)
export const PDFViewer: React.FC<PDFViewerProps> = ({
  fileUrl,
  highlights = [],
  onHighlightClick,
  className = ''
}) => {
  const [error, setError] = useState<string | null>(null);

  const handleIframeError = () => {
    setError('Failed to load PDF. Please check the file URL.');
  };

  // Convert PyMuPDF bounding boxes to highlight areas
  const convertBoundingBoxesToHighlights = (boundingBoxes: any[], pageNumber: number): HighlightArea[] => {
    return boundingBoxes.map((bbox, index) => ({
      pageIndex: pageNumber - 1, // Convert to 0-based index
      left: bbox[0], // x0
      top: bbox[1],  // y0
      width: bbox[2] - bbox[0], // x1 - x0
      height: bbox[3] - bbox[1], // y1 - y0
      color: '#fbbf24', // Default yellow
      opacity: 0.4,
    }));
  };

  return (
    <div className={`pdf-viewer-container ${className}`}>
      {/* PDF Controls */}
      <div className="flex items-center justify-between p-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">PDF Viewer</span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1 text-sm border rounded hover:bg-muted"
          >
            Open in New Tab
          </a>
        </div>
      </div>

      {/* PDF Document */}
      <div className="flex-1 bg-gray-50">
        {error ? (
          <div className="text-center p-8 text-red-500">
            <div className="text-lg font-semibold mb-2">PDF Error</div>
            <div className="text-sm">{error}</div>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Retry
            </button>
          </div>
        ) : (
          <iframe
            src={fileUrl}
            width="100%"
            height="600px"
            style={{ border: 'none' }}
            onError={handleIframeError}
            title="PDF Document"
          />
        )}
      </div>

      {/* Highlights Info */}
      {highlights.length > 0 && (
        <div className="p-2 border-t bg-muted/30">
          <div className="text-sm text-muted-foreground">
            {highlights.length} highlight{highlights.length !== 1 ? 's' : ''} available
          </div>
        </div>
      )}
    </div>
  );
};

// Utility function to convert PyMuPDF data to highlight areas
export const createHighlightsFromPyMuPDF = (
  textBlocks: any[],
  pageNumber: number,
  color: string = '#fbbf24'
): HighlightArea[] => {
  return textBlocks
    .filter(block => block.bbox && block.text.trim())
    .map(block => ({
      pageIndex: pageNumber - 1,
      left: block.bbox[0],
      top: block.bbox[1],
      width: block.bbox[2] - block.bbox[0],
      height: block.bbox[3] - block.bbox[1],
      color,
      opacity: 0.4,
    }));
};

// Utility function to create highlights from source references
export const createHighlightsFromSourceReferences = (
  sources: any[],
  documentStructure: any
): HighlightArea[] => {
  const highlights: HighlightArea[] = [];
  
  sources.forEach((source, index) => {
    if (source.start_index !== undefined && source.end_index !== undefined) {
      // Find the page and bounding box for this source
      const pageData = documentStructure.pages?.find((page: any) => 
        source.start_index >= page.start_index && 
        source.start_index <= page.end_index
      );
      
      if (pageData && pageData.text_blocks) {
        // Find matching text blocks in the page
        const matchingBlocks = pageData.text_blocks.filter((block: any) => 
          block.text.includes(source.text.substring(0, 50)) // Match first 50 chars
        );
        
        matchingBlocks.forEach(block => {
          highlights.push({
            pageIndex: pageData.page_number - 1,
            left: block.bbox[0],
            top: block.bbox[1],
            width: block.bbox[2] - block.bbox[0],
            height: block.bbox[3] - block.bbox[1],
            color: getHighlightColorBySourceId(source.id, sources.length),
            opacity: 0.4,
          });
        });
      }
    }
  });
  
  return highlights;
};

// Import the color function
import { getHighlightColorBySourceId } from '@/lib/constants/colors';
