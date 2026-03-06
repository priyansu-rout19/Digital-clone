import { useState, useCallback, useRef, useEffect } from 'react';
import type { ChatMessage, WSMessage, WSResponseMessage, TraceRecord } from '../api/types';
import { NODE_LABELS } from '../api/types';

const WS_TIMEOUT_MS = 60_000;

export function useChat(slug: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentNode, setCurrentNode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const traceRef = useRef<TraceRecord[]>([]);

  // Helper: clear the response timeout
  const clearResponseTimeout = useCallback(() => {
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Helper: close WS if it's still open
  const closeWs = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
    }
    wsRef.current = null;
  }, []);

  // Cleanup on unmount — close any open WS and clear timeout
  useEffect(() => {
    return () => {
      clearResponseTimeout();
      closeWs();
    };
  }, [clearResponseTimeout, closeWs]);

  const sendMessage = useCallback(
    (query: string, userId = 'anonymous', accessTier = 'public') => {
      // Close any existing WS before opening a new one
      clearResponseTimeout();
      closeWs();

      setMessages((prev) => [...prev, { role: 'user', content: query }]);
      setIsLoading(true);
      setError(null);
      setCurrentNode(null);
      traceRef.current = [];

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/chat/ws/${slug}`);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ query, user_id: userId, access_tier: accessTier }));

        // Start 30s response timeout after message is sent
        timeoutRef.current = setTimeout(() => {
          setError('Response timed out. Please try again.');
          setIsLoading(false);
          setCurrentNode(null);
          closeWs();
        }, WS_TIMEOUT_MS);
      };

      ws.onmessage = (event) => {
        const msg: WSMessage = JSON.parse(event.data);

        if (msg.type === 'progress') {
          // Reset timeout on every progress event — only fires if backend
          // goes completely silent for 60s, not just because pipeline is slow
          clearResponseTimeout();
          setCurrentNode(NODE_LABELS[msg.node] || msg.node);
          // Accumulate trace record for reasoning panel
          if (msg.trace) {
            traceRef.current = [...traceRef.current, msg.trace];
          }
          timeoutRef.current = setTimeout(() => {
            setError('Response timed out. Please try again.');
            setIsLoading(false);
            setCurrentNode(null);
            closeWs();
          }, WS_TIMEOUT_MS);
        } else if (msg.type === 'response') {
          clearResponseTimeout();
          const resp = msg as WSResponseMessage;
          const accumulatedTrace = [...traceRef.current];
          traceRef.current = [];
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: resp.response,
              confidence: resp.confidence,
              cited_sources: resp.cited_sources,
              silence_triggered: resp.silence_triggered,
              suggested_topics: resp.suggested_topics,
              audio_base64: resp.audio_base64 ?? undefined,
              audio_format: resp.audio_format ?? undefined,
              trace: accumulatedTrace,
            },
          ]);
          setIsLoading(false);
          setCurrentNode(null);
        } else if (msg.type === 'error') {
          clearResponseTimeout();
          setError(msg.message);
          setIsLoading(false);
          setCurrentNode(null);
        }
      };

      ws.onerror = () => {
        clearResponseTimeout();
        setError('Connection error. Please try again.');
        setIsLoading(false);
        setCurrentNode(null);
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    },
    [slug, clearResponseTimeout, closeWs],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isLoading, currentNode, error, sendMessage, clearMessages };
}
