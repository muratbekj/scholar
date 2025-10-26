import { useState, useEffect, useCallback } from 'react';
import { apiService } from '@/lib/api';

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

interface UseDocumentViewerReturn {
  documentContent: DocumentContent | null;
  isLoading: boolean;
  error: string | null;
  loadDocument: (fileId: string) => Promise<void>;
  getPageForPosition: (position: number) => number | null;
  getSectionForPosition: (position: number) => string | null;
  scrollToPosition: (position: number) => void;
}

export const useDocumentViewer = (): UseDocumentViewerReturn => {
  const [documentContent, setDocumentContent] = useState<DocumentContent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDocument = useCallback(async (fileId: string) => {
    if (!fileId) return;

    setIsLoading(true);
    setError(null);

    try {
      const content = await apiService.getDocumentContent(fileId);
      setDocumentContent(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
      console.error('Error loading document:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getPageForPosition = useCallback((position: number): number | null => {
    if (!documentContent?.document_structure?.pages) return null;

    for (const page of documentContent.document_structure.pages) {
      if (position >= page.start_index && position <= page.end_index) {
        return page.page_number;
      }
    }
    return null;
  }, [documentContent]);

  const getSectionForPosition = useCallback((position: number): string | null => {
    if (!documentContent?.document_structure?.sections) return null;

    for (const section of documentContent.document_structure.sections) {
      if (position >= section.start_index && position <= section.end_index) {
        return section.title;
      }
    }
    return null;
  }, [documentContent]);

  const scrollToPosition = useCallback((position: number) => {
    // This will be implemented by the DocumentViewer component
    // The hook provides the interface, but the actual scrolling
    // is handled by the component that uses this hook
    console.log('Scroll to position:', position);
  }, []);

  return {
    documentContent,
    isLoading,
    error,
    loadDocument,
    getPageForPosition,
    getSectionForPosition,
    scrollToPosition
  };
};
