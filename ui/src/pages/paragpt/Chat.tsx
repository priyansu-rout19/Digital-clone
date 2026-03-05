import { useEffect, useRef } from 'react';
import type { ChatMessage, CloneProfile } from '../../api/types';
import MessageBubble from '../../components/MessageBubble';
import ChatInput from '../../components/ChatInput';

import AudioPlayer from '../../components/AudioPlayer';
import CollapsibleCitations from '../../components/CollapsibleCitations';
import { useAudio } from '../../hooks/useAudio';

interface ChatProps {
  messages: ChatMessage[];
  isLoading: boolean;
  currentNode: string | null;
  onSendMessage: (query: string) => void;
  profile: CloneProfile | null;
  error?: string | null;
}

export default function Chat({ messages, isLoading, currentNode, onSendMessage, profile, error }: ChatProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isPlaying, progress, play, toggle } = useAudio();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentNode]);

  return (
    <div className="relative flex flex-col h-full bg-para-navy">
      {/* Error banner — auto-clears when user sends next message */}
      {error && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-red-900/90 text-red-200 px-4 py-2 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto hide-scrollbar px-4 pt-8 pb-4 max-w-3xl mx-auto w-full">
        {/* Conversation start — scrolls with messages */}
        <div className="flex flex-col items-center pt-2 pb-6">
          <img src="/avatars/parag-khanna.png" alt={profile?.display_name || 'Clone'} className="w-12 h-12 rounded-full object-cover mb-2" />
          <span className="text-white/80 text-sm font-medium">{profile?.display_name || 'Clone'}</span>
        </div>
        {messages.map((msg, i) => (
          <div key={i}>
            <MessageBubble message={msg} variant="paragpt" isLatest={i === messages.length - 1} />

            {/* Citations */}
            {msg.role === 'assistant' && msg.cited_sources && msg.cited_sources.length > 0 && (
              <CollapsibleCitations sources={msg.cited_sources} variant="paragpt" />
            )}

            {/* Audio player */}
            {msg.role === 'assistant' && msg.audio_base64 && (
              <div className="ml-2 mb-4">
                <AudioPlayer
                  isPlaying={isPlaying}
                  progress={progress}
                  onToggle={() => {
                    if (!isPlaying && msg.audio_base64) {
                      play(msg.audio_base64, msg.audio_format || 'mp3');
                    } else {
                      toggle();
                    }
                  }}
                  variant="paragpt"
                />
              </div>
            )}
          </div>
        ))}

        {/* Thinking bubble — appears immediately when loading */}
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="glass rounded-2xl px-5 py-4 min-w-[80px]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              {currentNode && (
                <p className="text-xs text-gray-500 mt-2">{currentNode}</p>
              )}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="px-4 pt-3 pb-6 max-w-3xl mx-auto w-full border-t border-white/[0.06]">
        <ChatInput onSend={onSendMessage} disabled={isLoading} placeholder="Ask anything..." />
      </div>
    </div>
  );
}
