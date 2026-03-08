import { useState, useEffect, useCallback } from 'react';
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
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(message.content)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      })
      .catch(() => {
        // Fallback for insecure contexts or denied clipboard permission
        try {
          const ta = document.createElement('textarea');
          ta.value = message.content;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          // Copy is a convenience — silently fail if both methods fail
        }
      });
  }, [message.content]);

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
            isParagpt
              ? 'bg-gradient-to-r from-para-teal to-para-teal-dark shadow-warm-glow'
              : 'bg-gray-700 shadow-sacred-glow'
          }`}
        >
          {message.content}
        </div>
      </div>
    );
  }

  const isSilence = message.silence_triggered;

  return (
    <div className="group flex justify-start mb-4">
      <div
        className={`relative w-full rounded-2xl text-sm leading-relaxed ${
          isParagpt ? 'glass px-4 py-3 text-gray-100' : 'glass-sacred px-5 py-4'
        }`}
      >
        {/* Copy button — visible on hover */}
        <button
          onClick={handleCopy}
          className={`absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${
            isParagpt ? 'hover:bg-white/10 text-gray-400 hover:text-white' : 'hover:bg-sacred-gold/10 text-gray-500 hover:text-sacred-gold'
          }`}
          title="Copy response"
          aria-label="Copy response"
        >
          {copied ? (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-green-400">
              <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M7 3.5A1.5 1.5 0 0 1 8.5 2h3.879a1.5 1.5 0 0 1 1.06.44l3.122 3.12A1.5 1.5 0 0 1 17 6.622V12.5a1.5 1.5 0 0 1-1.5 1.5h-1v-3.379a3 3 0 0 0-.879-2.121L10.5 5.379A3 3 0 0 0 8.379 4.5H7v-1Z" />
              <path d="M4.5 6A1.5 1.5 0 0 0 3 7.5v9A1.5 1.5 0 0 0 4.5 18h7a1.5 1.5 0 0 0 1.5-1.5v-5.879a1.5 1.5 0 0 0-.44-1.06L9.44 6.439A1.5 1.5 0 0 0 8.378 6H4.5Z" />
            </svg>
          )}
        </button>
        {isSilence && !isParagpt ? (
          <div className="text-sacred-ivory italic font-serif">
            <span className="text-sacred-gold text-2xl leading-none">&ldquo;</span>
            {shownText}
            <span className="text-sacred-gold text-2xl leading-none">&rdquo;</span>
          </div>
        ) : isParagpt ? (
          <div className="text-gray-100 markdown-body">
            <Markdown disallowedElements={['script', 'iframe', 'object', 'embed', 'form']} unwrapDisallowed>{shownText}</Markdown>
          </div>
        ) : (
          <div className="text-sacred-ivory font-serif">
            <span className="text-sacred-gold text-4xl leading-none font-serif">&ldquo;</span>
            <span className="italic">{shownText}</span>
            <span className="text-sacred-gold text-4xl leading-none font-serif">&rdquo;</span>
          </div>
        )}

        {message.confidence != null && !isSilence && message.intent_class !== 'persona' && (
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

      </div>
    </div>
  );
}
