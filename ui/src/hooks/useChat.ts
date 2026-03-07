import { useState, useCallback, useRef, useEffect } from 'react';
import type { ChatMessage, WSMessage, WSResponseMessage, TraceRecord } from '../api/types';
import { NODE_LABELS } from '../api/types';

const WS_TIMEOUT_MS = 60_000;
const WS_CONNECT_TIMEOUT_MS = 10_000;

export function useChat(slug: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentNode, setCurrentNode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const traceRef = useRef<TraceRecord[]>([]);
  const isMountedRef = useRef(true);

  const clearResponseTimeout = useCallback(() => {
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const clearConnectTimeout = useCallback(() => {
    if (connectTimeoutRef.current !== null) {
      clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }
  }, []);

  const closeWs = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
    }
    wsRef.current = null;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearResponseTimeout();
      clearConnectTimeout();
      closeWs();
    };
  }, [clearResponseTimeout, clearConnectTimeout, closeWs]);

  // Reset state when slug changes (prevents cross-clone message bleed)
  useEffect(() => {
    setMessages([]);
    setIsLoading(false);
    setCurrentNode(null);
    setError(null);
    traceRef.current = [];
    clearResponseTimeout();
    clearConnectTimeout();
    closeWs();
  }, [slug]); // eslint-disable-line react-hooks/exhaustive-deps

  const sendMessage = useCallback(
    (query: string, userId = 'anonymous', accessTier = 'public', model = '') => {
      clearResponseTimeout();
      clearConnectTimeout();
      closeWs();

      setMessages((prev) => [...prev, { role: 'user', content: query }]);
      setIsLoading(true);
      setError(null);
      setCurrentNode(null);
      traceRef.current = [];

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/chat/ws/${slug}`);
      wsRef.current = ws;

      // Connection timeout — fires if WS handshake never completes (backend down)
      connectTimeoutRef.current = setTimeout(() => {
        if (!isMountedRef.current) return;
        setError('Could not connect to server. Please try again.');
        setIsLoading(false);
        setCurrentNode(null);
        closeWs();
      }, WS_CONNECT_TIMEOUT_MS);

      ws.onopen = () => {
        clearConnectTimeout();
        // Race guard: if a newer sendMessage() replaced wsRef, this ws is stale
        if (ws !== wsRef.current) { ws.close(); return; }
        if (!isMountedRef.current) return;

        ws.send(JSON.stringify({ query, user_id: userId, access_tier: accessTier, model }));

        timeoutRef.current = setTimeout(() => {
          if (!isMountedRef.current) return;
          setError('Response timed out. Please try again.');
          setIsLoading(false);
          setCurrentNode(null);
          closeWs();
        }, WS_TIMEOUT_MS);
      };

      ws.onmessage = (event) => {
        if (ws !== wsRef.current || !isMountedRef.current) return;

        let msg: WSMessage;
        try {
          msg = JSON.parse(event.data);
        } catch {
          setError('Received malformed response from server.');
          setIsLoading(false);
          setCurrentNode(null);
          clearResponseTimeout();
          closeWs();
          return;
        }

        if (msg.type === 'progress') {
          clearResponseTimeout();
          setCurrentNode(NODE_LABELS[msg.node] || msg.node);
          if (msg.trace) {
            traceRef.current = [...traceRef.current, msg.trace];
          }
          timeoutRef.current = setTimeout(() => {
            if (!isMountedRef.current) return;
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
              model: resp.model,
              review_id: resp.review_id ?? undefined,
              review_status: resp.review_id ? 'pending' : undefined,
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
        if (ws !== wsRef.current || !isMountedRef.current) return;
        clearResponseTimeout();
        clearConnectTimeout();
        setError('Connection error. Please try again.');
        setIsLoading(false);
        setCurrentNode(null);
      };

      ws.onclose = () => {
        // Only null out if this is still the current WS (race guard)
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
      };
    },
    [slug, clearResponseTimeout, clearConnectTimeout, closeWs],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, setMessages, isLoading, currentNode, error, sendMessage, clearMessages };
}
