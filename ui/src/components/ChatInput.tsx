import { useState, type KeyboardEvent } from 'react';

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

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-center gap-2 p-2 glass rounded-[20px]">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 bg-transparent px-4 py-3 text-white placeholder-gray-500 outline-none text-sm"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className={`w-10 h-10 rounded-full bg-${accentColor} flex items-center justify-center transition-opacity hover:opacity-90 disabled:opacity-40`}
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
  );
}
