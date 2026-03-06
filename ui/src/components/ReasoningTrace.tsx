import { useState } from 'react';
import type { TraceRecord } from '../api/types';
import { NODE_DISPLAY_NAMES } from '../api/types';

function formatDetail(r: TraceRecord): string {
  const parts: string[] = [];
  if (r.intent) parts.push(`intent: ${r.intent}`);
  if (r.sub_query_count != null) parts.push(`${r.sub_query_count} sub-queries`);
  if (r.response_tokens != null) parts.push(`target: ${r.response_tokens} tokens`);
  if (r.passage_count != null) parts.push(`${r.passage_count} passages`);
  if (r.vector_count != null || r.bm25_count != null) {
    const v = r.vector_count ?? 0;
    const b = r.bm25_count ?? 0;
    if (v > 0 && b > 0) parts.push('vector + BM25');
    else if (b > 0)      parts.push('BM25 only');
    else if (v > 0)      parts.push('vector only');
  }
  if (r.reranked) parts.push('reranked');
  if (r.confidence != null) parts.push(`confidence: ${Math.round(r.confidence * 100)}%`);
  if (r.retry_count != null) parts.push(`retry #${r.retry_count}`);
  if (r.new_queries != null) parts.push(`${r.new_queries} new queries`);
  if (r.context_chars != null) parts.push(`~${Math.round(r.context_chars / 4)} tokens`);
  if (r.has_history) parts.push('loaded');
  if (r.has_memory) parts.push('found memories');
  if (r.generated) parts.push('done');
  if (r.citation_count != null) parts.push(`${r.citation_count} citations`);
  if (r.final_confidence != null) parts.push(`score: ${Math.round(r.final_confidence * 100)}%`);
  if (r.silence_triggered) parts.push('silenced');
  if (r.has_audio) parts.push('audio generated');
  return parts.join(' · ');
}

interface ReasoningTraceProps {
  trace: TraceRecord[];
  variant?: 'paragpt' | 'sacred-archive';
}

export default function ReasoningTrace({ trace, variant = 'paragpt' }: ReasoningTraceProps) {
  const [expanded, setExpanded] = useState(false);

  if (!trace || trace.length === 0) return null;

  const isParagpt = variant === 'paragpt';

  return (
    <div className="mb-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
          transition-colors duration-150 cursor-pointer select-none
          ${isParagpt
            ? 'text-[#d08050] hover:bg-[#d08050]/10'
            : 'text-sacred-gold hover:bg-sacred-gold/10'
          }
        `}
        aria-expanded={expanded}
        aria-label={expanded ? 'Hide reasoning trace' : 'Show reasoning trace'}
      >
        {/* Pipeline icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-3.5 h-3.5"
        >
          <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.379 2.624l-1.02 1.02a.75.75 0 11-1.06-1.06l1.02-1.02A5.5 5.5 0 018.5 3a5.5 5.5 0 015.207 3.73l1.543-1.544a.75.75 0 011.06 1.06l-1.543 1.545A5.48 5.48 0 0115.5 11a5.48 5.48 0 01-.188.424zM14 11a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
        </svg>

        <span>{trace.length} pipeline steps</span>

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
        <div className="mt-2 ml-4 border-l border-gray-700 pl-3 space-y-1.5">
          {trace.map((record, i) => {
            const label = NODE_DISPLAY_NAMES[record.node] || record.node;
            const detail = formatDetail(record);
            const isLast = i === trace.length - 1;

            return (
              <div key={i} className="flex items-start gap-2">
                <div className={`w-2 h-2 mt-1 rounded-full flex-shrink-0 ${isLast ? 'bg-green-400' : 'bg-gray-600'}`} />
                <div className="min-w-0">
                  <span className="text-xs text-gray-400">{label}</span>
                  {detail && <span className="text-xs text-gray-600 ml-2">{detail}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
