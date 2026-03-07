import type { MouseEvent } from 'react';

const ACCENT_BG: Record<string, string> = {
  'para-teal': 'bg-para-teal',
  'sacred-gold': 'bg-sacred-gold',
};

interface AudioPlayerProps {
  isPlaying: boolean;
  progress: number;
  onToggle: () => void;
  onSeek?: (percentage: number) => void;
  variant?: 'paragpt' | 'sacred-archive';
}

export default function AudioPlayer({
  isPlaying,
  progress,
  onToggle,
  onSeek,
  variant = 'paragpt',
}: AudioPlayerProps) {
  const accent = variant === 'paragpt' ? 'para-teal' : 'sacred-gold';

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${
        variant === 'paragpt' ? 'glass' : 'glass-sacred'
      }`}
    >
      <button
        onClick={onToggle}
        className={`w-6 h-6 rounded-full ${ACCENT_BG[accent]} flex items-center justify-center`}
      >
        {isPlaying ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3 text-white">
            <path
              fillRule="evenodd"
              d="M6.75 5.25a.75.75 0 0 1 .75-.75H9a.75.75 0 0 1 .75.75v13.5a.75.75 0 0 1-.75.75H7.5a.75.75 0 0 1-.75-.75V5.25Zm7.5 0A.75.75 0 0 1 15 4.5h1.5a.75.75 0 0 1 .75.75v13.5a.75.75 0 0 1-.75.75H15a.75.75 0 0 1-.75-.75V5.25Z"
              clipRule="evenodd"
            />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3 text-white">
            <path
              fillRule="evenodd"
              d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </button>
      <div
        className="w-24 h-3 bg-white/10 rounded-full overflow-hidden cursor-pointer flex items-center"
        onClick={(e: MouseEvent<HTMLDivElement>) => {
          if (!onSeek) return;
          const rect = e.currentTarget.getBoundingClientRect();
          const pct = ((e.clientX - rect.left) / rect.width) * 100;
          onSeek(pct);
        }}
      >
        <div
          className={`h-1 ${ACCENT_BG[accent]} rounded-full transition-all duration-200`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
