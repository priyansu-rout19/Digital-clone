import { useState, useEffect } from 'react';
import type { ReviewItem } from '../../api/types';
import { getReviews, updateReview } from '../../api/client';
import CollapsibleCitations from '../../components/CollapsibleCitations';

interface DashboardProps {
  slug: string;
}

export default function Dashboard({ slug }: DashboardProps) {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [selected, setSelected] = useState<ReviewItem | null>(null);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editText, setEditText] = useState('');

  const fetchReviews = () => {
    setLoading(true);
    getReviews(slug)
      .then(setReviews)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchReviews();
  }, [slug]);

  const handleAction = async (action: 'approve' | 'reject') => {
    if (!selected) return;
    setActionLoading(true);
    try {
      await updateReview(slug, selected.id, { action, notes: notes || undefined });
      setReviews((prev) => prev.filter((r) => r.id !== selected.id));
      setSelected(null);
      setNotes('');
      setEditMode(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleEdit = async () => {
    if (!selected || !editText.trim()) return;
    setActionLoading(true);
    try {
      const result = await updateReview(slug, selected.id, {
        action: 'edit',
        edited_response: editText,
        notes: notes || undefined,
      });
      const updatedText = result.response_text || editText;
      setReviews((prev) =>
        prev.map((r) => (r.id === selected.id ? { ...r, response_text: updatedText } : r))
      );
      setSelected({ ...selected, response_text: updatedText });
      setEditMode(false);
      setNotes('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Edit failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'TEXTAREA' || tag === 'INPUT') return;
      if (!selected || actionLoading) return;

      switch (e.key) {
        case 'a':
          handleAction('approve');
          break;
        case 'r':
          handleAction('reject');
          break;
        case 'e':
          setEditMode(true);
          setEditText(selected.response_text);
          break;
        case 'ArrowDown': {
          e.preventDefault();
          const idx = reviews.findIndex((r) => r.id === selected.id);
          if (idx < reviews.length - 1) { setSelected(reviews[idx + 1]); setEditMode(false); }
          break;
        }
        case 'ArrowUp': {
          e.preventDefault();
          const idx = reviews.findIndex((r) => r.id === selected.id);
          if (idx > 0) { setSelected(reviews[idx - 1]); setEditMode(false); }
          break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selected, reviews, actionLoading, editMode]);

  const confidenceColor = (score: number | null) => {
    if (score == null) return 'text-gray-500';
    if (score > 0.9) return 'text-green-400';
    if (score > 0.7) return 'text-yellow-400';
    return 'text-red-400';
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-sacred-brown">
        <span className="text-sacred-ivory/50 text-sm">Loading review queue...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-sacred-brown">
        <div className="text-center">
          <p className="text-red-400 mb-2">Error loading reviews</p>
          <p className="text-gray-500 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row h-full bg-sacred-brown text-sacred-ivory">
      {/* Left — Queue List */}
      <div className="w-full md:w-[30%] h-48 md:h-auto border-r border-gray-700 overflow-y-auto">
        <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-sacred-gold font-semibold text-sm tracking-wide">Review Queue</h2>
          <span className="text-xs px-2 py-0.5 rounded-full bg-sacred-gold/20 text-sacred-gold">
            {reviews.length}
          </span>
        </div>
        {reviews.length === 0 ? (
          <p className="px-4 py-8 text-center text-gray-500 text-sm">No pending reviews</p>
        ) : (
          reviews.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => { setSelected(item); setEditMode(false); }}
              className={`w-full text-left px-4 py-3 border-b border-gray-800 hover:bg-gray-800/50 transition-colors cursor-pointer ${
                selected?.id === item.id ? 'border-l-2 border-l-sacred-gold bg-gray-800/30' : ''
              }`}
            >
              <p className="text-sm text-sacred-ivory/80 truncate">{item.query_text}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-xs ${confidenceColor(item.confidence_score)}`}>
                  {item.confidence_score != null ? `${Math.round(item.confidence_score * 100)}%` : 'N/A'}
                </span>
                <span className="text-xs text-gray-600">{new Date(item.created_at).toLocaleDateString()}</span>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Center — Detail */}
      <div className="w-full md:w-[45%] flex-1 md:flex-none overflow-y-auto p-6">
        {!selected ? (
          <div className="h-full flex items-center justify-center">
            <p className="text-gray-500 text-sm">Select a review item</p>
          </div>
        ) : (
          <div>
            <div className="mb-6">
              <h3 className="text-sacred-gold text-xs font-semibold uppercase tracking-wide mb-2">Question</h3>
              <p className="text-sacred-ivory/90 text-sm">{selected.query_text}</p>
            </div>
            <div className="mb-6">
              <h3 className="text-sacred-gold text-xs font-semibold uppercase tracking-wide mb-2">Generated Response</h3>
              {editMode ? (
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="w-full h-48 bg-gray-800/50 border border-gray-700 rounded-xl p-3 text-sm text-sacred-ivory/80 outline-none resize-y"
                  style={{ fontFamily: 'Georgia, serif' }}
                />
              ) : (
                <p className="text-sacred-ivory/80 text-sm leading-relaxed" style={{ fontFamily: 'Georgia, serif' }}>
                  {selected.response_text}
                </p>
              )}
            </div>
            {selected.confidence_score != null && (
              <span className={`text-xs px-2 py-0.5 rounded-full bg-sacred-gold/20 ${confidenceColor(selected.confidence_score)}`}>
                {Math.round(selected.confidence_score * 100)}% confidence
              </span>
            )}

            {/* Cited sources */}
            {selected.cited_sources && selected.cited_sources.length > 0 && (
              <div className="mt-4">
                <CollapsibleCitations
                  sources={selected.cited_sources}
                  variant="sacred-archive"
                  defaultExpanded={true}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right — Actions */}
      <div className="w-full md:w-[25%] border-t md:border-t-0 md:border-l border-gray-700 p-6 flex flex-col gap-4">
        <h3 className="text-sacred-gold text-xs font-semibold uppercase tracking-wide">Actions</h3>

        {editMode ? (
          <>
            <button
              onClick={handleEdit}
              disabled={actionLoading || !editText.trim()}
              className="w-full py-2.5 rounded-xl bg-sacred-gold text-sacred-brown font-semibold text-sm hover:bg-sacred-gold-dark transition-colors disabled:opacity-40"
            >
              {actionLoading ? 'Saving...' : 'Save Edit'}
            </button>
            <button
              onClick={() => setEditMode(false)}
              disabled={actionLoading}
              className="w-full py-2.5 rounded-xl bg-gray-700 text-gray-300 font-semibold text-sm hover:bg-gray-600 transition-colors disabled:opacity-40"
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => handleAction('approve')}
              disabled={!selected || actionLoading}
              className="w-full py-2.5 rounded-xl bg-sacred-gold text-sacred-brown font-semibold text-sm hover:bg-sacred-gold-dark transition-colors disabled:opacity-40"
            >
              {actionLoading ? 'Processing...' : <span className="flex items-center justify-center gap-2">Approve <kbd className="text-xs px-1.5 py-0.5 rounded bg-sacred-brown text-sacred-gold/60 font-mono">a</kbd></span>}
            </button>
            <button
              onClick={() => {
                if (selected) {
                  setEditMode(true);
                  setEditText(selected.response_text);
                }
              }}
              disabled={!selected || actionLoading}
              className="w-full py-2.5 rounded-xl bg-gray-700 text-gray-300 font-semibold text-sm hover:bg-gray-600 transition-colors disabled:opacity-40"
            >
              <span className="flex items-center justify-center gap-2">Edit <kbd className="text-xs px-1.5 py-0.5 rounded bg-gray-800 text-gray-500 font-mono">e</kbd></span>
            </button>
            <button
              onClick={() => handleAction('reject')}
              disabled={!selected || actionLoading}
              className="w-full py-2.5 rounded-xl bg-red-900/60 text-red-200 font-semibold text-sm hover:bg-red-900/80 transition-colors disabled:opacity-40"
            >
              <span className="flex items-center justify-center gap-2">Reject <kbd className="text-xs px-1.5 py-0.5 rounded bg-red-950 text-red-400/60 font-mono">r</kbd></span>
            </button>
          </>
        )}

        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add reviewer notes..."
          disabled={!selected}
          className="w-full h-32 bg-gray-800/50 border border-gray-700 rounded-xl p-3 text-sm text-sacred-ivory/80 placeholder-gray-600 outline-none resize-none disabled:opacity-40"
        />

        <p className="text-xs text-gray-600 mt-auto">Arrow keys to navigate queue</p>
      </div>
    </div>
  );
}
