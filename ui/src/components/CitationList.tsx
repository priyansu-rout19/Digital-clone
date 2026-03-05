import type { CitedSource } from '../api/types';
import CitationCard from './CitationCard';
import CitationGroupCard from './CitationGroupCard';

interface SourceGroup {
  key: string;
  title: string | null;
  sourceType: string;
  date: string | null;
  sources: CitedSource[];
}

function groupCitations(sources: CitedSource[]): SourceGroup[] {
  const groups = new Map<string, SourceGroup>();

  for (const s of sources) {
    const docId = s.doc_id;
    const key = (docId && docId !== 'unknown')
      ? docId
      : (s.source_title || s.chunk_text);

    if (!groups.has(key)) {
      groups.set(key, {
        key,
        title: s.source_title ?? null,
        sourceType: s.source,
        date: s.date ?? null,
        sources: [],
      });
    }
    groups.get(key)!.sources.push(s);
  }

  return Array.from(groups.values());
}

interface CitationListProps {
  sources: CitedSource[];
  variant?: 'paragpt' | 'sacred-archive';
}

export default function CitationList({ sources, variant = 'paragpt' }: CitationListProps) {
  if (!sources || sources.length === 0) return null;

  const groups = groupCitations(sources);

  return (
    <div className="ml-2 mb-4">
      {groups.map((group) =>
        group.sources.length === 1 ? (
          <CitationCard
            key={group.key}
            source={group.sources[0]}
            variant={variant}
          />
        ) : (
          <CitationGroupCard
            key={group.key}
            title={group.title}
            sourceType={group.sourceType}
            date={group.date}
            sources={group.sources}
            variant={variant}
          />
        )
      )}
    </div>
  );
}
