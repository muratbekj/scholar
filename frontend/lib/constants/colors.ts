// Shared color constants for consistent highlighting across components
export const HIGHLIGHT_COLORS = [
  '#fbbf24', // yellow
  '#60a5fa', // blue  
  '#34d399', // green
  '#f472b6', // pink
  '#a78bfa', // purple
  '#fb7185', // rose
  '#f59e0b', // amber
  '#10b981', // emerald
  '#8b5cf6', // violet
  '#ef4444', // red
];

export const getHighlightColor = (index: number): string => {
  return HIGHLIGHT_COLORS[index % HIGHLIGHT_COLORS.length];
};

export const getHighlightColorBySourceId = (sourceId: string, totalSources: number): string => {
  // Create a consistent hash from sourceId to ensure same color for same source
  let hash = 0;
  for (let i = 0; i < sourceId.length; i++) {
    const char = sourceId.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  const index = Math.abs(hash) % totalSources;
  return getHighlightColor(index);
};
