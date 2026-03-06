import { useEffect, useRef } from 'react';
import type { ChatMessage, CloneProfile } from '../../api/types';
import MessageBubble from '../../components/MessageBubble';
import ChatInput from '../../components/ChatInput';
import NodeProgress from '../../components/NodeProgress';
import CollapsibleCitations from '../../components/CollapsibleCitations';
import ReasoningTrace from '../../components/ReasoningTrace';

interface ChatProps {
  messages: ChatMessage[];
  isLoading: boolean;
  currentNode: string | null;
  onSendMessage: (query: string) => void;
  accessTier: string;
  profile: CloneProfile | null;
  error?: string | null;
}

export default function Chat({ messages, isLoading, currentNode, onSendMessage, accessTier, profile: _profile, error }: ChatProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentNode]);

  const tierLabel = accessTier.charAt(0).toUpperCase() + accessTier.slice(1);

  return (
    <div className="relative flex flex-col h-full bg-sacred-brown">
      {/* Top bar */}
      <div className="glass-sacred sticky top-0 z-10 px-4 py-3 flex items-center justify-between">
        <span
          className="text-sacred-gold text-sm font-semibold tracking-widest uppercase"
          style={{ fontFamily: "'Playfair Display', Georgia, serif" }}
        >
          Sacred Archive
        </span>
        <span className="text-xs px-3 py-1 rounded-full bg-sacred-gold/20 text-sacred-gold">
          Viewing as: {tierLabel}
        </span>
      </div>

      {/* Error banner — auto-clears when user sends next message */}
      {error && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-20 bg-red-900/90 text-red-200 px-4 py-2 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto hide-scrollbar px-4 py-4 max-w-3xl mx-auto w-full">
        {messages.map((msg, i) => (
          <div key={i}>
            <MessageBubble message={msg} variant="sacred-archive" isLatest={i === messages.length - 1} />

            {/* Provenance / citations */}
            {msg.role === 'assistant' && msg.cited_sources && msg.cited_sources.length > 0 && (
              <CollapsibleCitations sources={msg.cited_sources} variant="sacred-archive" />
            )}

            {/* Reasoning trace */}
            {msg.role === 'assistant' && msg.trace && msg.trace.length > 0 && (
              <ReasoningTrace trace={msg.trace} variant="sacred-archive" />
            )}
          </div>
        ))}

        <NodeProgress currentNode={currentNode} />
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="p-4 max-w-3xl mx-auto w-full">
        <div className="glass-sacred rounded-[16px]">
          <ChatInput
            onSend={onSendMessage}
            disabled={isLoading}
            placeholder="Ask from the teachings..."
            accentColor="sacred-gold"
          />
        </div>
      </div>
    </div>
  );
}
