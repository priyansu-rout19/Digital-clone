import { useState } from 'react';
import type { CloneProfile } from '../../api/types';

interface LandingProps {
  profile: CloneProfile | null;
  onSelectTier: (tier: string) => void;
  onSendMessage: (query: string) => void;
  onQuestionClick: (question: string) => void;
}

const TIERS = [
  { id: 'devotee', name: 'Devotee', desc: 'Full access to all verified teachings', borderColor: 'border-sacred-gold' },
  { id: 'friend', name: 'Friend', desc: 'Selected teachings and discourses', borderColor: 'border-gray-400' },
  { id: 'follower', name: 'Follower', desc: 'Public teachings and introductions', borderColor: 'border-gray-600' },
];

const SUGGESTED_QUESTIONS = [
  'What did the master teach about the nature of silence?',
  'Share the original words on devotion and surrender',
  'What teachings exist about the practice of meditation?',
];

export default function Landing({ profile: _profile, onSelectTier, onSendMessage, onQuestionClick }: LandingProps) {
  const [selectedTier, setSelectedTier] = useState('devotee');
  const [query, setQuery] = useState('');

  const handleTierSelect = (tierId: string) => {
    setSelectedTier(tierId);
    onSelectTier(tierId);
  };

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
    <div className="relative min-h-screen bg-sacred-brown flex flex-col items-center px-4 pt-12 pb-32">
      {/* Sacred geometry icon */}
      <div className="w-16 h-16 rounded-full border-2 border-sacred-gold/40 flex items-center justify-center mb-6">
        <div className="w-8 h-8 rounded-full border border-sacred-gold/60 flex items-center justify-center">
          <div className="w-3 h-3 rounded-full bg-sacred-gold/40" />
        </div>
      </div>

      {/* Title */}
      <h1 className="text-sacred-gold text-3xl font-bold tracking-[0.2em] mb-2" style={{ fontFamily: "'Playfair Display', Georgia, serif" }}>
        SACRED ARCHIVE
      </h1>

      {/* Tagline */}
      <p className="text-sacred-gold/70 text-sm tracking-wide mb-6">
        Preserved Teachings &middot; Verified Words &middot; Living Wisdom
      </p>

      {/* Description */}
      <p className="text-sacred-ivory/80 text-sm italic text-center max-w-md mb-10" style={{ fontFamily: 'Georgia, serif' }}>
        A reverently curated mirror of timeless wisdom. Direct teachings, unaltered and verified, preserved for seekers of truth.
      </p>

      {/* Tier Selector Cards */}
      <div className="w-full max-w-[640px] grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
        {TIERS.map((tier) => (
          <button
            key={tier.id}
            type="button"
            onClick={() => handleTierSelect(tier.id)}
            className={`glass-sacred rounded-xl p-4 text-left transition-all cursor-pointer ${
              selectedTier === tier.id
                ? `${tier.borderColor} border-2 shadow-[0_0_15px_rgba(196,150,60,0.2)]`
                : 'border border-gray-700'
            }`}
          >
            <h3
              className={`text-sm font-semibold mb-1 ${
                tier.id === 'devotee' ? 'text-sacred-gold' : tier.id === 'friend' ? 'text-gray-300' : 'text-gray-400'
              }`}
            >
              {tier.name}
            </h3>
            <p className="text-sacred-ivory/60 text-xs">{tier.desc}</p>
          </button>
        ))}
      </div>

      {/* Continue button */}
      <button
        type="button"
        onClick={() => onQuestionClick(SUGGESTED_QUESTIONS[0])}
        className="bg-sacred-gold text-sacred-brown px-8 py-3 rounded-xl font-semibold tracking-wide text-sm hover:bg-sacred-gold-dark transition-colors mb-8 uppercase"
      >
        Continue to Archive
      </button>

      {/* Suggested questions */}
      <div className="w-full max-w-[640px] space-y-2 mb-8">
        {SUGGESTED_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onQuestionClick(q)}
            className="block w-full text-left text-sacred-ivory/50 text-sm italic hover:text-sacred-ivory/80 transition-colors cursor-pointer"
            style={{ fontFamily: 'Georgia, serif' }}
          >
            &ldquo;{q}&rdquo;
          </button>
        ))}
      </div>

      {/* Sticky Input Bar */}
      <div className="fixed bottom-0 left-0 right-0 p-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <div className="glass-sacred rounded-[16px] max-w-[640px] mx-auto flex items-center gap-2 p-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask from the teachings..."
            className="flex-1 bg-transparent text-sacred-ivory placeholder-sacred-ivory/40 rounded-xl px-4 py-2.5 text-sm outline-none"
            style={{ fontFamily: 'Georgia, serif' }}
          />
          <button
            type="button"
            onClick={handleSend}
            aria-label="Send message"
            className="flex-shrink-0 w-10 h-10 rounded-full bg-sacred-gold flex items-center justify-center hover:bg-sacred-gold-dark transition-colors cursor-pointer"
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
