import { useState, useEffect } from 'react';
import Markdown from 'react-markdown';
import type { ChatMessage } from '../api/types';

interface MessageBubbleProps {
  message: ChatMessage;
  variant?: 'paragpt' | 'sacred-archive';
  isLatest?: boolean;
}

export default function MessageBubble({ message, variant = 'paragpt', isLatest = false }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isParagpt = variant === 'paragpt';

  // Typewriter effect for the latest assistant message
  const [displayedText, setDisplayedText] = useState('');
  const fullText = message.content;

  useEffect(() => {
    if (!isLatest || isUser || !fullText) {
      setDisplayedText(fullText);
      return;
    }

    setDisplayedText('');
    let idx = 0;
    const interval = setInterval(() => {
      idx += 3;
      if (idx >= fullText.length) {
        setDisplayedText(fullText);
        clearInterval(interval);
      } else {
        setDisplayedText(fullText.slice(0, idx));
      }
    }, 12);

    return () => clearInterval(interval);
  }, [fullText, isLatest, isUser]);

  const shownText = (!isUser && isLatest) ? displayedText : fullText;

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div
          className={`max-w-[90%] sm:max-w-[80%] md:max-w-[75%] px-4 py-3 rounded-2xl text-white text-sm ${
            isParagpt ? 'bg-gradient-to-r from-para-teal to-para-teal-dark' : 'bg-gray-700'
          }`}
        >
          {message.content}
        </div>
      </div>
    );
  }

  const isSilence = message.silence_triggered;

  return (
    <div className="flex justify-start mb-4">
      <div
        className={`max-w-[90%] sm:max-w-[80%] md:max-w-[75%] rounded-2xl text-sm leading-relaxed ${
          isParagpt ? 'glass px-4 py-3 text-gray-200' : 'glass-sacred px-5 py-4'
        }`}
      >
        {isSilence && !isParagpt ? (
          <div className="text-sacred-ivory italic font-serif">
            <span className="text-sacred-gold text-2xl leading-none">&ldquo;</span>
            {shownText}
            <span className="text-sacred-gold text-2xl leading-none">&rdquo;</span>
          </div>
        ) : isParagpt ? (
          <div className="text-gray-200 markdown-body">
            <Markdown>{shownText}</Markdown>
          </div>
        ) : (
          <div className="text-sacred-ivory font-serif">
            <span className="text-sacred-gold text-4xl leading-none font-serif">&ldquo;</span>
            <span className="italic">{shownText}</span>
            <span className="text-sacred-gold text-4xl leading-none font-serif">&rdquo;</span>
          </div>
        )}

        {message.confidence != null && !isSilence && (
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                isParagpt ? 'bg-para-teal/20 text-para-teal' : 'bg-sacred-gold/20 text-sacred-gold'
              }`}
            >
              {Math.round(message.confidence * 100)}% confident
            </span>
          </div>
        )}

        {message.cited_sources && message.cited_sources.length > 0 && (
          <div className="mt-2 text-xs text-gray-500">
            {message.cited_sources.length} source{message.cited_sources.length > 1 ? 's' : ''} cited
          </div>
        )}
      </div>
    </div>
  );
}
