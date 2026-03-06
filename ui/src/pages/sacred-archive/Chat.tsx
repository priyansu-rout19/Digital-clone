import { useEffect, useRef } from 'react';
import type { ChatMessage, CloneProfile } from '../../api/types';
import MessageBubble from '../../components/MessageBubble';
import ChatInput from '../../components/ChatInput';
import CollapsibleCitations from '../../components/CollapsibleCitations';
import ReasoningTrace from '../../components/ReasoningTrace';

interface ChatProps {
  messages: ChatMessage[];
  isLoading: boolean;
  currentNode: string | null;
  onSendMessage: (query: string) => void;
  onNewConversation?: () => void;
  accessTier: string;
  profile: CloneProfile | null;
  error?: string | null;
}

export default function Chat({ messages, isLoading, currentNode, onSendMessage, onNewConversation, accessTier, profile: _profile, error }: ChatProps) {
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

            {/* Suggested topics — clickable pills */}
            {msg.role === 'assistant' && msg.suggested_topics && msg.suggested_topics.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3 ml-1">
                <span className="text-xs text-gray-500" style={{ fontFamily: 'Georgia, serif' }}>You might explore:</span>
                {msg.suggested_topics.map((topic, j) => (
                  <button
                    key={j}
                    onClick={() => onSendMessage(topic)}
                    className="text-xs px-3 py-1 rounded-full bg-sacred-gold/15 text-sacred-gold hover:bg-sacred-gold/25 transition-colors cursor-pointer"
                    style={{ fontFamily: 'Georgia, serif' }}
                  >
                    {topic}
                  </button>
                ))}
              </div>
            )}

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

        {/* Thinking bubble — appears immediately when loading */}
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="glass-sacred rounded-2xl px-5 py-4 min-w-[80px]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-sacred-gold rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-sacred-gold rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-sacred-gold rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              {currentNode && (
                <p className="text-xs text-gray-500 mt-2" style={{ fontFamily: 'Georgia, serif' }}>{currentNode}</p>
              )}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="p-4 max-w-3xl mx-auto w-full">
        <div className="glass-sacred rounded-[16px]">
          <div className="flex items-center gap-2">
            {onNewConversation && (
              <button
                onClick={onNewConversation}
                className="w-10 h-10 ml-2 rounded-full flex items-center justify-center text-gray-500 hover:text-sacred-gold hover:bg-sacred-gold/10 transition-colors flex-shrink-0"
                title="New conversation"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <path d="M10 3a.75.75 0 0 1 .75.75v5.5h5.5a.75.75 0 0 1 0 1.5h-5.5v5.5a.75.75 0 0 1-1.5 0v-5.5h-5.5a.75.75 0 0 1 0-1.5h5.5v-5.5A.75.75 0 0 1 10 3Z" />
                </svg>
              </button>
            )}
            <div className="flex-1">
              <ChatInput
                onSend={onSendMessage}
                disabled={isLoading}
                placeholder="Ask from the teachings..."
                accentColor="sacred-gold"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
