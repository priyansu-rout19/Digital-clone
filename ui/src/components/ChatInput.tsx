import { useState, useRef, useEffect, type KeyboardEvent } from 'react';

const MAX_CHARS = 2000;

// Full class strings so Tailwind can detect them at build time (no interpolation)
const ACCENT_BG: Record<string, string> = {
  'para-teal': 'bg-para-teal',
  'sacred-gold': 'bg-sacred-gold',
};

interface ChatInputProps {
  onSend: (query: string) => void;
  disabled?: boolean;
  placeholder?: string;
  accentColor?: string;
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Ask anything...',
  accentColor = 'para-teal',
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isComposingRef = useRef(false);
  const compositionEndTimeRef = useRef(0);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled || trimmed.length > MAX_CHARS) return;
    onSend(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    // Chromium fires compositionend BEFORE the final keydown, so check a 50ms window
    const justFinishedComposing = Date.now() - compositionEndTimeRef.current < 50;
    if (e.key === 'Enter' && !e.shiftKey && !isComposingRef.current && !justFinishedComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }, [input]);

  const overLimit = input.length > MAX_CHARS;
  const nearLimit = input.length > MAX_CHARS - 100;

  return (
    <div>
      <div className="flex items-end gap-2 p-2 glass rounded-[20px]">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => { isComposingRef.current = true; }}
          onCompositionEnd={() => { isComposingRef.current = false; compositionEndTimeRef.current = Date.now(); }}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent px-4 py-3 text-white placeholder-gray-500 outline-none text-sm resize-none"
          style={{ maxHeight: '120px' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim() || overLimit}
          className={`w-10 h-10 rounded-full ${ACCENT_BG[accentColor] || 'bg-para-teal'} flex items-center justify-center transition-opacity hover:opacity-90 disabled:opacity-40 flex-shrink-0`}
        >
          {disabled ? (
            <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="w-5 h-5 text-white"
            >
              <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
            </svg>
          )}
        </button>
      </div>
      {nearLimit && (
        <div className={`text-xs mt-1 px-4 ${overLimit ? 'text-red-400' : 'text-gray-600'}`}>
          {input.length}/{MAX_CHARS}
        </div>
      )}
    </div>
  );
}
