import { useState } from 'react';
import type { CitedSource } from '../api/types';
import CitationCard from './CitationCard';

interface CitationGroupCardProps {
  title: string | null;
  sourceType: string;
  date: string | null;
  sources: CitedSource[];
  variant?: 'paragpt' | 'sacred-archive';
}

export default function CitationGroupCard({
  title, sourceType, date, sources, variant = 'paragpt',
}: CitationGroupCardProps) {
  const [expanded, setExpanded] = useState(false);
  const accent = variant === 'paragpt' ? 'border-para-teal' : 'border-sacred-gold';
  const badgeBg = variant === 'paragpt'
    ? 'bg-para-teal/20 text-para-teal'
    : 'bg-sacred-gold/20 text-sacred-gold';

  const headerText = title
    ? `${title} (${sourceType})${date ? ` — ${date}` : ''}`
    : sourceType || 'Source';

  return (
    <div className={`border-l-2 ${accent} pl-3 py-1 mb-2`}>
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 font-medium">{headerText}</span>
          <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${badgeBg}`}>
            {sources.length} passages
          </span>
        </div>
        <svg
          className={`w-3 h-3 text-gray-500 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
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

      {expanded && (
        <div className="mt-2 ml-2 space-y-2 border-l border-gray-700 pl-3">
          {sources.map((source, idx) => (
            <CitationCard
              key={source.chunk_id || idx}
              source={source}
              variant={variant}
              passageOnly
            />
          ))}
        </div>
      )}
    </div>
  );
}
