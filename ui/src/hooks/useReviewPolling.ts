import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../api/types';
import { getReviewStatus } from '../api/client';

const POLL_INTERVAL_MS = 15_000; // Poll every 15 seconds
const MAX_POLL_DURATION_MS = 3_600_000; // Stop after 1 hour

/**
 * Polls review status for messages with review_id + status='pending'.
 * On rejection: replaces message content with silence message.
 * On approval/edit: updates review_status (and content for edits).
 * No-op when no messages need polling (safe for ParaGPT).
 */
export function useReviewPolling(
  slug: string,
  messages: ChatMessage[],
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  silenceMessage: string,
) {
  const intervalsRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());
  const startTimesRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    if (!slug || !silenceMessage) return;

    // Find messages that need polling (have review_id, status=pending)
    const pendingMessages = messages.filter(
      (m) => m.review_id && m.review_status === 'pending',
    );

    for (const msg of pendingMessages) {
      const rid = msg.review_id!;
      if (intervalsRef.current.has(rid)) continue; // already polling

      startTimesRef.current.set(rid, Date.now());

      const interval = setInterval(async () => {
        // Stop if max duration exceeded
        const startTime = startTimesRef.current.get(rid) || Date.now();
        if (Date.now() - startTime > MAX_POLL_DURATION_MS) {
          clearInterval(intervalsRef.current.get(rid)!);
          intervalsRef.current.delete(rid);
          startTimesRef.current.delete(rid);
          return;
        }

        try {
          const result = await getReviewStatus(slug, rid);

          if (result.status !== 'pending') {
            // Stop polling
            clearInterval(intervalsRef.current.get(rid)!);
            intervalsRef.current.delete(rid);
            startTimesRef.current.delete(rid);

            // Update the message
            setMessages((prev) =>
              prev.map((m) => {
                if (m.review_id !== rid) return m;
                if (result.status === 'rejected') {
                  return {
                    ...m,
                    content: silenceMessage,
                    review_status: 'rejected',
                    silence_triggered: true,
                    cited_sources: [],
                  };
                }
                return {
                  ...m,
                  review_status: result.status,
                  content: result.response_text || m.content,
                };
              }),
            );
          }
        } catch {
          // Silently ignore poll errors (network blips, etc.)
        }
      }, POLL_INTERVAL_MS);

      intervalsRef.current.set(rid, interval);
    }

    // Cleanup on unmount
    return () => {
      for (const interval of intervalsRef.current.values()) {
        clearInterval(interval);
      }
      intervalsRef.current.clear();
      startTimesRef.current.clear();
    };
  }, [messages, slug, silenceMessage, setMessages]);
}
