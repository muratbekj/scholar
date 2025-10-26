// Utility functions for PDF highlighting with PyMuPDF bounding boxes

import { getHighlightColorBySourceId } from '@/lib/constants/colors';

export interface PyMuPDFBoundingBox {
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  text: string;
  font: string;
  size: number;
  flags: number;
}

export interface PyMuPDFPageData {
  page: number;
  content: string;
  text_blocks: PyMuPDFBoundingBox[];
  page_bbox: [number, number, number, number];
}

export interface HighlightArea {
  pageIndex: number;
  left: number;
  top: number;
  width: number;
  height: number;
  color: string;
  opacity: number;
}

/**
 * Convert PyMuPDF bounding boxes to highlight areas for PDF viewer
 */
export const convertPyMuPDFToHighlightAreas = (
  pageData: PyMuPDFPageData,
  color: string = '#fbbf24'
): HighlightArea[] => {
  return pageData.text_blocks.map((block) => ({
    pageIndex: pageData.page - 1, // Convert to 0-based index
    left: block.bbox[0], // x0
    top: block.bbox[1],  // y0
    width: block.bbox[2] - block.bbox[0], // x1 - x0
    height: block.bbox[3] - block.bbox[1], // y1 - y0
    color,
    opacity: 0.4,
  }));
};

/**
 * Create highlights from source references using PyMuPDF data
 */
export const createHighlightsFromPyMuPDFData = (
  sources: any[],
  boundingBoxes: Record<number, PyMuPDFBoundingBox[]>
): HighlightArea[] => {
  const highlights: HighlightArea[] = [];
  
  sources.forEach((source) => {
    if (source.page_number && boundingBoxes[source.page_number]) {
      const pageBlocks = boundingBoxes[source.page_number];
      const color = getHighlightColorBySourceId(source.id, sources.length);
      
      // Find matching text blocks
      const matchingBlocks = pageBlocks.filter(block => 
        block.text.includes(source.text.substring(0, 30)) // Match first 30 chars
      );
      
      matchingBlocks.forEach(block => {
        highlights.push({
          pageIndex: source.page_number - 1,
          left: block.bbox[0],
          top: block.bbox[1],
          width: block.bbox[2] - block.bbox[0],
          height: block.bbox[3] - block.bbox[1],
          color,
          opacity: 0.4,
        });
      });
    }
  });
  
  return highlights;
};

/**
 * Example usage with backend data:
 * 
 * // Backend sends:
 * {
 *   "bounding_boxes": {
 *     "1": [
 *       {
 *         "bbox": [120, 300, 250, 320],
 *         "text": "machine learning algorithms",
 *         "font": "Arial",
 *         "size": 12
 *       }
 *     ]
 *   }
 * }
 * 
 * // Frontend usage:
 * const highlights = createHighlightsFromPyMuPDFData(
 *   sourceReferences,
 *   documentContent.bounding_boxes
 * );
 */
