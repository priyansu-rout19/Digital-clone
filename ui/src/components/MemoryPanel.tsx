import { useState, useEffect, useCallback } from 'react';
import type { MemoryItem } from '../api/types';
import { getUserMemories, deleteUserMemory, deleteAllUserMemories, deleteConversationHistory, getConversationHistoryCount } from '../api/client';

interface MemoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  cloneSlug?: string;
  onHistoryCleared?: () => void;
}

function relativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function MemoryPanel({ isOpen, onClose, userId, cloneSlug, onHistoryCleared }: MemoryPanelProps) {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [confirmClearHistory, setConfirmClearHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyCount, setHistoryCount] = useState<number | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyCleared, setHistoryCleared] = useState(false);

  const fetchMemories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getUserMemories(userId);
      setMemories(res.memories);
    } catch {
      setError('Could not load memories');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Fetch when panel opens
  useEffect(() => {
    if (isOpen) {
      fetchMemories();
      setConfirmClearAll(false);
      setConfirmClearHistory(false);
      setHistoryCleared(false);
      setHistoryError(null);
      if (cloneSlug) {
        getConversationHistoryCount(userId, cloneSlug)
          .then(res => setHistoryCount(res.message_count))
          .catch(() => setHistoryCount(null));
      }
    }
  }, [isOpen, fetchMemories, userId, cloneSlug]);

  const handleDelete = async (memoryId: string) => {
    // Optimistic removal
    const prev = memories;
    setMemories(m => m.filter(item => item.id !== memoryId));
    setDeleting(s => new Set(s).add(memoryId));

    try {
      await deleteUserMemory(userId, memoryId);
    } catch {
      // Restore on failure
      setMemories(prev);
    } finally {
      setDeleting(s => {
        const next = new Set(s);
        next.delete(memoryId);
        return next;
      });
    }
  };

  const handleClearHistory = async () => {
    if (!confirmClearHistory) {
      setConfirmClearHistory(true);
      return;
    }
    if (!cloneSlug) return;
    setConfirmClearHistory(false);
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      await deleteConversationHistory(userId, cloneSlug);
      setHistoryCount(0);
      setHistoryCleared(true);
      setTimeout(() => setHistoryCleared(false), 2000);
      onHistoryCleared?.();
    } catch {
      setHistoryError('Could not clear conversation history');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleClearAll = async () => {
    if (!confirmClearAll) {
      setConfirmClearAll(true);
      return;
    }
    setConfirmClearAll(false);
    setLoading(true);
    try {
      await deleteAllUserMemories(userId);
      setMemories([]);
    } catch {
      setError('Could not clear memories');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-full max-w-sm z-50 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="h-full flex flex-col glass border-l border-white/10">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
            <h2 className="text-white font-semibold text-base" style={{ fontFamily: 'var(--font-display)' }}>
              Your Memories
            </h2>
            <div className="flex items-center gap-2">
              {memories.length > 0 && (
                <button
                  onClick={handleClearAll}
                  className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
                    confirmClearAll
                      ? 'bg-red-600/80 text-white hover:bg-red-600'
                      : 'text-red-400 hover:bg-red-900/30'
                  }`}
                >
                  {confirmClearAll ? 'Confirm clear all' : 'Clear all'}
                </button>
              )}
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
                </svg>
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto hide-scrollbar px-5 py-4">
            {loading && (
              <div className="flex justify-center py-12">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}

            {error && !loading && (
              <div className="text-center py-12">
                <p className="text-red-400 text-sm mb-3">{error}</p>
                <button
                  onClick={fetchMemories}
                  className="text-xs px-4 py-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {!loading && !error && memories.length === 0 && (
              <div className="text-center py-12">
                <div className="text-4xl opacity-20 mb-3">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-12 h-12 mx-auto text-gray-500">
                    <path d="M12 2a1 1 0 0 1 1 1v.5a5.5 5.5 0 0 1 4.9 3.6A4.5 4.5 0 0 1 21 11.5a4.5 4.5 0 0 1-2.1 3.8A5.5 5.5 0 0 1 13 19.5V21a1 1 0 1 1-2 0v-1.5a5.5 5.5 0 0 1-5.9-4.2A4.5 4.5 0 0 1 3 11.5 4.5 4.5 0 0 1 6.1 7.1 5.5 5.5 0 0 1 11 3.5V3a1 1 0 0 1 1-1Zm-1 4a3.5 3.5 0 0 0-3.4 2.7 1 1 0 0 1-1 .8A2.5 2.5 0 0 0 5 11.5a2.5 2.5 0 0 0 1.6 2.3 1 1 0 0 1 .6.8A3.5 3.5 0 0 0 11 17.5V6Zm2 11.5a3.5 3.5 0 0 0 3.8-2.9 1 1 0 0 1 .6-.8A2.5 2.5 0 0 0 19 11.5a2.5 2.5 0 0 0-1.6-2.3 1 1 0 0 1-.6-.8A3.5 3.5 0 0 0 13 6v11.5Z" />
                  </svg>
                </div>
                <p className="text-gray-500 text-sm">No memories stored yet</p>
                <p className="text-gray-600 text-xs mt-1">Memories are created as you chat</p>
              </div>
            )}

            {!loading && !error && memories.map(mem => (
              <div
                key={mem.id}
                className={`group mb-3 rounded-xl bg-white/[0.04] border border-white/[0.06] px-4 py-3 transition-opacity ${
                  deleting.has(mem.id) ? 'opacity-40' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-white/90 text-sm leading-relaxed flex-1">{mem.memory}</p>
                  <button
                    onClick={() => handleDelete(mem.id)}
                    disabled={deleting.has(mem.id)}
                    className="w-7 h-7 rounded-full flex items-center justify-center text-gray-600 hover:text-red-400 hover:bg-red-900/20 transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100"
                    title="Delete memory"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                      <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
                {(mem.updated_at || mem.created_at) && (
                  <p className="text-gray-600 text-xs mt-1.5">
                    {relativeTime(mem.updated_at || mem.created_at)}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Conversation history section */}
          {cloneSlug && (
            <div className="mx-5 mb-4 mt-2 rounded-xl bg-white/[0.03] border border-white/[0.06] px-4 py-3">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-1">
                Conversation History
              </p>

              {historyCount === null && !historyCleared && (
                <p className="text-gray-500 text-xs">Loading...</p>
              )}

              {historyCount === 0 && !historyCleared && (
                <p className="text-gray-600 text-xs">No conversation history stored</p>
              )}

              {historyCleared && (
                <p className="text-green-400 text-xs">Conversation history cleared</p>
              )}

              {historyCount !== null && historyCount > 0 && (
                <>
                  <p className="text-gray-500 text-xs mb-3">
                    {historyCount} {historyCount === 1 ? 'message' : 'messages'} stored. Clear to start fresh.
                  </p>
                  <button
                    onClick={handleClearHistory}
                    disabled={historyLoading}
                    className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
                      confirmClearHistory
                        ? 'bg-red-600/80 text-white hover:bg-red-600'
                        : 'text-red-400 hover:bg-red-900/30 border border-red-400/20'
                    }`}
                  >
                    {historyLoading ? 'Clearing...'
                      : confirmClearHistory ? 'Confirm: clear history'
                      : 'Clear conversation history'}
                  </button>
                </>
              )}

              {historyError && (
                <p className="text-red-400 text-xs mt-2">{historyError}</p>
              )}
            </div>
          )}

          {/* Footer count */}
          {!loading && !error && memories.length > 0 && (
            <div className="px-5 py-3 border-t border-white/10 text-center">
              <span className="text-gray-500 text-xs">{memories.length} {memories.length === 1 ? 'memory' : 'memories'} stored</span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
