import { useState } from 'react';
import type { CloneProfile } from '../../api/types';
import ModelSelector from '../../components/ModelSelector';
import MemoryPanel from '../../components/MemoryPanel';

interface LandingProps {
  profile: CloneProfile;
  onSendMessage: (query: string) => void;
  onQuestionClick: (question: string) => void;
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  userId?: string;
  cloneSlug?: string;
  onHistoryCleared?: () => void;
  userMemoryEnabled?: boolean;
}

const TOPIC_TAGS = ['Geopolitics', 'Connectivity', 'Strategic Thinking', 'Asia', 'Global Trends'];

const STARTER_QUESTIONS = [
  'What is the future of ASEAN?',
  'How does infrastructure shape global power?',
  'What is your best recipe for chocolate cake?',
];

export default function Landing({ profile, onSendMessage, onQuestionClick, selectedModel, onModelChange, userId, cloneSlug, onHistoryCleared, userMemoryEnabled }: LandingProps) {
  const [query, setQuery] = useState('');
  const [memoryPanelOpen, setMemoryPanelOpen] = useState(false);

  const handleSend = () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setQuery('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend();
  };

  return (
    <div className="relative min-h-screen bg-para-navy flex flex-col items-center px-4 pt-12 pb-32">
      {/* Profile Card */}
      <div className="glass glass-glow-hover rounded-[16px] w-full max-w-[640px] p-8 flex flex-col items-center text-center">
        <img
          src={profile.avatar_url || '/avatars/parag-khanna.png'}
          alt={profile.display_name}
          className="w-20 h-20 rounded-full object-cover mb-4"
        />

        <h1 className="text-white text-2xl font-bold mb-2" style={{ fontFamily: 'var(--font-display)' }}>{profile.display_name}</h1>
        <p className="text-slate-400 text-sm leading-relaxed mb-4 max-w-md">{profile.bio}</p>

        <div className="flex flex-wrap justify-center gap-2">
          {TOPIC_TAGS.map((tag) => (
            <span key={tag} className="border border-para-teal/50 text-para-teal text-xs px-3 py-1 rounded-full">
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Starter Questions */}
      <div className="w-full max-w-[640px] mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
        {STARTER_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onQuestionClick(question)}
            className="glass glass-glow-hover rounded-2xl p-4 text-left text-slate-300 text-sm leading-snug hover:bg-para-card-hover transition-colors cursor-pointer"
          >
            {question}
          </button>
        ))}
      </div>

      {/* Memory panel */}
      {userMemoryEnabled && userId && (
        <MemoryPanel isOpen={memoryPanelOpen} onClose={() => setMemoryPanelOpen(false)} userId={userId} cloneSlug={cloneSlug} onHistoryCleared={onHistoryCleared} />
      )}

      {/* Sticky Input Bar */}
      <div className="fixed bottom-0 left-0 right-0 p-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <div className="glass rounded-[20px] max-w-[640px] mx-auto flex items-center gap-2 p-2">
          <button type="button" disabled aria-label="Voice input (coming soon)" className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-slate-500 cursor-not-allowed">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <rect x="9" y="1" width="6" height="12" rx="3" />
              <path d="M5 10a7 7 0 0 0 14 0" />
              <line x1="12" y1="17" x2="12" y2="21" />
              <line x1="8" y1="21" x2="16" y2="21" />
            </svg>
          </button>

          {userMemoryEnabled && userId && (
            <button
              type="button"
              onClick={() => setMemoryPanelOpen(true)}
              className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-slate-500 hover:text-para-teal hover:bg-white/10 transition-colors"
              title="Your memories"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path d="M12 2a1 1 0 0 1 1 1v.5a5.5 5.5 0 0 1 4.9 3.6A4.5 4.5 0 0 1 21 11.5a4.5 4.5 0 0 1-2.1 3.8A5.5 5.5 0 0 1 13 19.5V21a1 1 0 1 1-2 0v-1.5a5.5 5.5 0 0 1-5.9-4.2A4.5 4.5 0 0 1 3 11.5 4.5 4.5 0 0 1 6.1 7.1 5.5 5.5 0 0 1 11 3.5V3a1 1 0 0 1 1-1Zm-1 4a3.5 3.5 0 0 0-3.4 2.7 1 1 0 0 1-1 .8A2.5 2.5 0 0 0 5 11.5a2.5 2.5 0 0 0 1.6 2.3 1 1 0 0 1 .6.8A3.5 3.5 0 0 0 11 17.5V6Zm2 11.5a3.5 3.5 0 0 0 3.8-2.9 1 1 0 0 1 .6-.8A2.5 2.5 0 0 0 19 11.5a2.5 2.5 0 0 0-1.6-2.3 1 1 0 0 1-.6-.8A3.5 3.5 0 0 0 13 6v11.5Z" />
              </svg>
            </button>
          )}

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            className="flex-1 bg-para-navy/80 text-white placeholder-slate-500 rounded-[20px] px-4 py-2.5 text-sm outline-none border border-glass-border focus:border-para-teal/40 transition-colors"
          />

          <ModelSelector selectedModel={selectedModel} onModelChange={onModelChange} variant="paragpt" />

          <button
            type="button"
            onClick={handleSend}
            aria-label="Send message"
            className="flex-shrink-0 w-10 h-10 rounded-full bg-para-teal flex items-center justify-center hover:bg-para-teal-dark transition-colors cursor-pointer"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
