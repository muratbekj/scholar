import { useState, useCallback, useRef } from 'react';
import { SourceReference } from '@/lib/api';
import { getHighlightColorBySourceId } from '@/lib/constants/colors';

interface Highlight {
  id: string;
  startIndex: number;
  endIndex: number;
  color: string;
  text: string;
  pageNumber?: number;
  sectionTitle?: string;
}

interface UseHighlightManagerReturn {
  highlights: Highlight[];
  highlightedSourceIds: string[];
  addHighlight: (source: SourceReference) => void;
  removeHighlight: (highlightId: string) => void;
  clearHighlights: () => void;
  toggleHighlight: (source: SourceReference) => void;
  isHighlighted: (sourceId: string) => boolean;
  getHighlightColor: (index: number) => string;
}

export const useHighlightManager = (): UseHighlightManagerReturn => {
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [highlightedSourceIds, setHighlightedSourceIds] = useState<string[]>([]);

  const getHighlightColor = useCallback((index: number) => {
    // Use the same color assignment logic as SourceReference
    return getHighlightColorBySourceId(`highlight_${index}`, 10);
  }, []);

  const addHighlight = useCallback((source: SourceReference) => {
    // Validate source reference has required position data
    if (source.start_index === undefined || source.end_index === undefined) {
      console.warn('Source reference missing position data:', source);
      return;
    }

    // Validate position data is reasonable
    if (source.start_index < 0 || source.end_index <= source.start_index) {
      console.warn('Invalid position data in source reference:', source);
      return;
    }

    const newHighlight: Highlight = {
      id: source.id,
      startIndex: source.start_index,
      endIndex: source.end_index,
      color: getHighlightColorBySourceId(source.id, 10), // Use same color as SourceReference
      text: source.text,
      pageNumber: source.page_number,
      sectionTitle: source.section_title
    };

    console.log('Adding highlight:', {
      id: newHighlight.id,
      startIndex: newHighlight.startIndex,
      endIndex: newHighlight.endIndex,
      text: newHighlight.text.substring(0, 50) + '...',
      color: newHighlight.color
    });

    setHighlights(prev => {
      // Check if highlight already exists
      if (prev.some(h => h.id === source.id)) {
        console.log('Highlight already exists, skipping:', source.id);
        return prev;
      }
      return [...prev, newHighlight];
    });

    setHighlightedSourceIds(prev => {
      if (prev.includes(source.id)) {
        return prev;
      }
      return [...prev, source.id];
    });
  }, [highlights.length, getHighlightColor]);

  const removeHighlight = useCallback((highlightId: string) => {
    setHighlights(prev => prev.filter(h => h.id !== highlightId));
    setHighlightedSourceIds(prev => prev.filter(id => id !== highlightId));
  }, []);

  const clearHighlights = useCallback(() => {
    setHighlights([]);
    setHighlightedSourceIds([]);
  }, []);

  const toggleHighlight = useCallback((source: SourceReference) => {
    if (highlightedSourceIds.includes(source.id)) {
      removeHighlight(source.id);
    } else {
      addHighlight(source);
    }
  }, [highlightedSourceIds, addHighlight, removeHighlight]);

  const isHighlighted = useCallback((sourceId: string) => {
    return highlightedSourceIds.includes(sourceId);
  }, [highlightedSourceIds]);

  return {
    highlights,
    highlightedSourceIds,
    addHighlight,
    removeHighlight,
    clearHighlights,
    toggleHighlight,
    isHighlighted,
    getHighlightColor
  };
};
