import { useState } from 'react';
import type { CitedSource } from '../api/types';

interface CitationCardProps {
  source: CitedSource;
  variant?: 'paragpt' | 'sacred-archive';
}

export default function CitationCard({ source, variant = 'paragpt' }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const accent = variant === 'paragpt' ? 'border-para-teal' : 'border-sacred-gold';

  return (
    <div className={`border-l-2 ${accent} pl-3 py-1 mb-2 cursor-pointer`} onClick={() => setExpanded(!expanded)}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 font-medium">{source.source || 'Source'}</span>
        <svg
          className={`w-3 h-3 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </div>
      {expanded && <p className="text-xs text-gray-500 mt-1">{source.chunk_text}</p>}
    </div>
  );
}
