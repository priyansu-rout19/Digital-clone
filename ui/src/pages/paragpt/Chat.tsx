import { useEffect, useRef, useState } from 'react';
import type { ChatMessage, CloneProfile } from '../../api/types';
import MessageBubble from '../../components/MessageBubble';
import ChatInput from '../../components/ChatInput';

import AudioPlayer from '../../components/AudioPlayer';
import CollapsibleCitations from '../../components/CollapsibleCitations';
import ReasoningTrace from '../../components/ReasoningTrace';
import ModelSelector from '../../components/ModelSelector';
import MemoryPanel from '../../components/MemoryPanel';
import { useAudio } from '../../hooks/useAudio';

interface ChatProps {
  messages: ChatMessage[];
  isLoading: boolean;
  currentNode: string | null;
  onSendMessage: (query: string) => void;
  onNewConversation?: () => void;
  profile: CloneProfile | null;
  error?: string | null;
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  voiceEnabled?: boolean;
  onVoiceToggle?: () => void;
  userId?: string;
  cloneSlug?: string;
  onHistoryCleared?: () => void;
}

export default function Chat({ messages, isLoading, currentNode, onSendMessage, onNewConversation, profile, error, selectedModel, onModelChange, voiceEnabled, onVoiceToggle, userId, cloneSlug, onHistoryCleared }: ChatProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isPlaying, progress, play, toggle, seek } = useAudio();
  const [memoryPanelOpen, setMemoryPanelOpen] = useState(false);

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
      <div className="flex-1 overflow-y-auto hide-scrollbar px-4 pt-8 pb-4 max-w-3xl mx-auto w-full" aria-live="polite">
        {/* Conversation start — scrolls with messages */}
        <div className="flex flex-col items-center pt-2 pb-6">
          <img src={profile?.avatar_url || '/avatars/parag-khanna.png'} alt={profile?.display_name || 'Clone'} className="w-12 h-12 rounded-full object-cover mb-2" />
          <span className="text-white/80 text-sm font-medium" style={{ fontFamily: 'var(--font-display)' }}>{profile?.display_name || 'Clone'}</span>
        </div>
        {messages.map((msg, i) => (
          <div key={i}>
            <MessageBubble message={msg} variant="paragpt" isLatest={i === messages.length - 1} />

            {/* Suggested topics — clickable pills */}
            {msg.role === 'assistant' && msg.suggested_topics && msg.suggested_topics.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3 ml-1">
                <span className="text-xs text-gray-500">You might explore:</span>
                {msg.suggested_topics.map((topic, j) => (
                  <button
                    key={j}
                    onClick={() => onSendMessage(topic)}
                    className="text-xs px-3 py-1 rounded-full bg-para-teal/15 text-para-teal hover:bg-para-teal/25 transition-colors cursor-pointer"
                  >
                    {topic}
                  </button>
                ))}
              </div>
            )}

            {/* Citations */}
            {msg.role === 'assistant' && !msg.silence_triggered && msg.cited_sources && msg.cited_sources.length > 0 && (
              <CollapsibleCitations sources={msg.cited_sources} variant="paragpt" />
            )}

            {/* Reasoning trace */}
            {msg.role === 'assistant' && msg.trace && msg.trace.length > 0 && (
              <ReasoningTrace trace={msg.trace} variant="paragpt" />
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
                  onSeek={seek}
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

      {/* Memory panel */}
      {profile?.user_memory_enabled && userId && (
        <MemoryPanel isOpen={memoryPanelOpen} onClose={() => setMemoryPanelOpen(false)} userId={userId} cloneSlug={cloneSlug} onHistoryCleared={onHistoryCleared} />
      )}

      {/* Input bar */}
      <div className="px-4 pt-4 pb-8 max-w-3xl mx-auto w-full border-t border-white/[0.06]">
        <div className="flex items-center gap-2">
          {onNewConversation && (
            <button
              onClick={onNewConversation}
              className="w-10 h-10 rounded-full flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/10 transition-colors flex-shrink-0"
              title="New conversation"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path d="M10 3a.75.75 0 0 1 .75.75v5.5h5.5a.75.75 0 0 1 0 1.5h-5.5v5.5a.75.75 0 0 1-1.5 0v-5.5h-5.5a.75.75 0 0 1 0-1.5h5.5v-5.5A.75.75 0 0 1 10 3Z" />
              </svg>
            </button>
          )}
          {onVoiceToggle && (
            <button
              onClick={onVoiceToggle}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors flex-shrink-0 ${
                voiceEnabled ? 'text-para-teal hover:bg-white/10' : 'text-gray-500 hover:bg-white/10'
              }`}
              title={voiceEnabled ? 'Disable voice' : 'Enable voice'}
            >
              {voiceEnabled ? (
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <path d="M10 3.75a.75.75 0 0 0-1.264-.546L5.203 6H3.667a.75.75 0 0 0-.7.48A6.985 6.985 0 0 0 2.5 9.25c0 .966.195 1.886.467 2.77a.75.75 0 0 0 .7.48h1.537l3.532 2.796A.75.75 0 0 0 10 14.75V3.75ZM15.95 5.05a.75.75 0 0 0-1.06 1.06 5.5 5.5 0 0 1 0 7.78.75.75 0 1 0 1.06 1.06 7 7 0 0 0 0-9.9Z" />
                  <path d="M13.829 7.172a.75.75 0 0 0-1.061 1.06 2.5 2.5 0 0 1 0 3.536.75.75 0 1 0 1.06 1.06 4 4 0 0 0 0-5.656Z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <path d="M10 3.75a.75.75 0 0 0-1.264-.546L5.203 6H3.667a.75.75 0 0 0-.7.48A6.985 6.985 0 0 0 2.5 9.25c0 .966.195 1.886.467 2.77a.75.75 0 0 0 .7.48h1.537l3.532 2.796A.75.75 0 0 0 10 14.75V3.75Z" />
                  <path d="M14.22 7.22a.75.75 0 0 1 1.06 0L16.5 8.44l1.22-1.22a.75.75 0 1 1 1.06 1.06L17.56 9.5l1.22 1.22a.75.75 0 1 1-1.06 1.06L16.5 10.56l-1.22 1.22a.75.75 0 1 1-1.06-1.06l1.22-1.22-1.22-1.22a.75.75 0 0 1 0-1.06Z" />
                </svg>
              )}
            </button>
          )}
          {profile?.user_memory_enabled && userId && (
            <button
              onClick={() => setMemoryPanelOpen(true)}
              className="w-10 h-10 rounded-full flex items-center justify-center text-gray-500 hover:text-para-teal hover:bg-white/10 transition-colors flex-shrink-0"
              title="Your memories"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path d="M12 2a1 1 0 0 1 1 1v.5a5.5 5.5 0 0 1 4.9 3.6A4.5 4.5 0 0 1 21 11.5a4.5 4.5 0 0 1-2.1 3.8A5.5 5.5 0 0 1 13 19.5V21a1 1 0 1 1-2 0v-1.5a5.5 5.5 0 0 1-5.9-4.2A4.5 4.5 0 0 1 3 11.5 4.5 4.5 0 0 1 6.1 7.1 5.5 5.5 0 0 1 11 3.5V3a1 1 0 0 1 1-1Zm-1 4a3.5 3.5 0 0 0-3.4 2.7 1 1 0 0 1-1 .8A2.5 2.5 0 0 0 5 11.5a2.5 2.5 0 0 0 1.6 2.3 1 1 0 0 1 .6.8A3.5 3.5 0 0 0 11 17.5V6Zm2 11.5a3.5 3.5 0 0 0 3.8-2.9 1 1 0 0 1 .6-.8A2.5 2.5 0 0 0 19 11.5a2.5 2.5 0 0 0-1.6-2.3 1 1 0 0 1-.6-.8A3.5 3.5 0 0 0 13 6v11.5Z" />
              </svg>
            </button>
          )}
          <div className="flex-1">
            <ChatInput onSend={onSendMessage} disabled={isLoading} placeholder="Ask anything..." />
          </div>
          <ModelSelector selectedModel={selectedModel} onModelChange={onModelChange} variant="paragpt" />
        </div>
      </div>
    </div>
  );
}
