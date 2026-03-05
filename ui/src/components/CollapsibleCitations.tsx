import { useState } from 'react';
import type { CitedSource } from '../api/types';
import CitationList from './CitationList';

interface CollapsibleCitationsProps {
  sources: CitedSource[];
  variant?: 'paragpt' | 'sacred-archive';
  defaultExpanded?: boolean;
}

export default function CollapsibleCitations({
  sources,
  variant = 'paragpt',
  defaultExpanded = false,
}: CollapsibleCitationsProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (!sources || sources.length === 0) return null;

  const isParagpt = variant === 'paragpt';
  const count = sources.length;
  const label = `${count} source${count > 1 ? 's' : ''} cited`;

  return (
    <div className="mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
          transition-colors duration-150 cursor-pointer select-none
          ${isParagpt
            ? 'text-para-teal hover:bg-para-teal/10'
            : 'text-sacred-gold hover:bg-sacred-gold/10'
          }
        `}
        aria-expanded={expanded}
        aria-label={expanded ? 'Hide citations' : 'Show citations'}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-3.5 h-3.5"
        >
          <path d="M10.75 16.82A7.462 7.462 0 0115 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0018 15.06V3.44a.75.75 0 00-.546-.721A9.006 9.006 0 0015 2.5a9.006 9.006 0 00-4.25 1.065v13.255zM9.25 4.565A9.006 9.006 0 005 2.5a9.006 9.006 0 00-2.454.219A.75.75 0 002 3.44v11.62a.75.75 0 00.954.721A7.462 7.462 0 015 15.5a7.462 7.462 0 014.25 1.32V4.565z" />
        </svg>

        <span>{label}</span>

        <svg
          className={`w-3 h-3 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
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
      </button>

      {expanded && (
        <div className="mt-1.5 ml-1">
          <CitationList sources={sources} variant={variant} />
        </div>
      )}
    </div>
  );
}
