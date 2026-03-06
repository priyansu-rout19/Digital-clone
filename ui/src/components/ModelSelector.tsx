import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { ModelInfo } from '../api/types';
import { getModels } from '../api/client';

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  variant?: 'paragpt' | 'sacred-archive';
}

/** Strip provider prefix from model ID for compact display (e.g., "qwen/qwen3-32b" → "qwen3-32b") */
function displayName(id: string): string {
  const parts = id.split('/');
  return parts[parts.length - 1];
}

export default function ModelSelector({ selectedModel, onModelChange, variant = 'paragpt' }: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [defaultModel, setDefaultModel] = useState('qwen/qwen3-32b');
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({});

  // Fetch available models on mount
  useEffect(() => {
    getModels()
      .then((resp) => {
        setModels(resp.models);
        setDefaultModel(resp.default);
        if (!selectedModel) {
          onModelChange(resp.default);
        }
      })
      .catch(() => {
        // Silently fail — selector shows default model only
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Close dropdown on outside click
  const handleOutsideClick = useCallback((e: MouseEvent) => {
    const target = e.target as Node;
    if (
      buttonRef.current && !buttonRef.current.contains(target) &&
      dropdownRef.current && !dropdownRef.current.contains(target)
    ) {
      setIsOpen(false);
    }
  }, []);

  useEffect(() => {
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [handleOutsideClick]);

  const isParagpt = variant === 'paragpt';
  const accentColor = isParagpt ? '#d08050' : '#c4963c';

  const canOpen = models.length > 0;

  const handleToggle = () => {
    if (!canOpen) return;
    if (!isOpen && buttonRef.current) {
      // Compute fixed position from button's viewport rect
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownStyle({
        position: 'fixed',
        bottom: window.innerHeight - rect.top + 8,
        right: window.innerWidth - rect.right,
        zIndex: 9999,
      });
    }
    setIsOpen(!isOpen);
  };

  return (
    <div className="relative">
      {/* Trigger pill */}
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-colors cursor-pointer"
        style={{ color: accentColor }}
        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = `${accentColor}15`; }}
        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
        title="Select model"
      >
        {/* Model icon */}
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5 flex-shrink-0">
          <path fillRule="evenodd" d="M8.34 1.804A1 1 0 0 1 9.32 1h1.36a1 1 0 0 1 .98.804l.295 1.473c.497.144.971.342 1.416.587l1.25-.834a1 1 0 0 1 1.262.125l.962.962a1 1 0 0 1 .125 1.262l-.834 1.25c.245.445.443.919.587 1.416l1.473.295a1 1 0 0 1 .804.98v1.361a1 1 0 0 1-.804.98l-1.473.295a6.95 6.95 0 0 1-.587 1.416l.834 1.25a1 1 0 0 1-.125 1.262l-.962.962a1 1 0 0 1-1.262.125l-1.25-.834a6.953 6.953 0 0 1-1.416.587l-.295 1.473a1 1 0 0 1-.98.804H9.32a1 1 0 0 1-.98-.804l-.295-1.473a6.957 6.957 0 0 1-1.416-.587l-1.25.834a1 1 0 0 1-1.262-.125l-.962-.962a1 1 0 0 1-.125-1.262l.834-1.25a6.957 6.957 0 0 1-.587-1.416l-1.473-.295A1 1 0 0 1 1 10.68V9.32a1 1 0 0 1 .804-.98l1.473-.295c.144-.497.342-.971.587-1.416l-.834-1.25a1 1 0 0 1 .125-1.262l.962-.962A1 1 0 0 1 5.38 3.03l1.25.834a6.957 6.957 0 0 1 1.416-.587l.294-1.473ZM13 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" clipRule="evenodd" />
        </svg>
        <span className="truncate max-w-[120px]">{displayName(selectedModel || defaultModel)}</span>
        {/* Chevron */}
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3 flex-shrink-0">
          <path fillRule="evenodd" d="M9.47 6.47a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 1 1-1.06 1.06L10 8.06l-3.72 3.72a.75.75 0 0 1-1.06-1.06l4.25-4.25Z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Dropdown — portaled to document.body to escape backdrop-filter containing block */}
      {isOpen && createPortal(
        <div
          ref={dropdownRef}
          className={`w-64 rounded-xl py-1 max-h-60 overflow-y-auto hide-scrollbar ${
            isParagpt ? 'glass' : 'glass-sacred'
          }`}
          style={dropdownStyle}
        >
          {models.map((m) => (
            <button
              key={m.id}
              onClick={() => { onModelChange(m.id); setIsOpen(false); }}
              className="w-full text-left px-3 py-2 text-sm transition-colors cursor-pointer"
              style={{
                color: m.id === (selectedModel || defaultModel) ? accentColor : 'rgba(255,255,255,0.7)',
                backgroundColor: m.id === (selectedModel || defaultModel) ? `${accentColor}15` : 'transparent',
              }}
              onMouseEnter={(e) => { if (m.id !== (selectedModel || defaultModel)) e.currentTarget.style.backgroundColor = `${accentColor}10`; }}
              onMouseLeave={(e) => { if (m.id !== (selectedModel || defaultModel)) e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
              <span className="block truncate">
                {displayName(m.id)}
                {m.id === defaultModel && (
                  <span className="opacity-50 ml-1">(default)</span>
                )}
              </span>
            </button>
          ))}
        </div>,
        document.body
      )}
    </div>
  );
}
