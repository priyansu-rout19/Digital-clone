import { useEffect, useRef } from 'react';
import type { ChatMessage, CloneProfile } from '../../api/types';
import MessageBubble from '../../components/MessageBubble';
import ChatInput from '../../components/ChatInput';
import NodeProgress from '../../components/NodeProgress';
import AudioPlayer from '../../components/AudioPlayer';
import CitationCard from '../../components/CitationCard';
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
      {/* Compact top bar */}
      <div className="glass sticky top-0 z-10 px-4 py-3 flex items-center gap-3">
        <img src="/avatars/parag-khanna.png" alt={profile?.display_name || 'Clone'} className="w-8 h-8 rounded-full object-cover" />
        <span className="text-white text-sm font-medium">{profile?.display_name || 'Clone'}</span>
        <span className="w-2 h-2 rounded-full bg-green-400" />
      </div>

      {/* Error banner — auto-clears when user sends next message */}
      {error && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-20 bg-red-900/90 text-red-200 px-4 py-2 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 max-w-2xl mx-auto w-full">
        {messages.map((msg, i) => (
          <div key={i}>
            <MessageBubble message={msg} variant="paragpt" isLatest={i === messages.length - 1} />

            {/* Citations */}
            {msg.role === 'assistant' && msg.cited_sources && msg.cited_sources.length > 0 && (
              <div className="ml-2 mb-4">
                {msg.cited_sources.map((source, j) => (
                  <CitationCard key={j} source={source} variant="paragpt" />
                ))}
              </div>
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

        <NodeProgress currentNode={currentNode} />
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="p-4 max-w-2xl mx-auto w-full">
        <ChatInput onSend={onSendMessage} disabled={isLoading} placeholder="Ask anything..." />
      </div>
    </div>
  );
}
