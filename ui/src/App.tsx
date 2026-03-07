import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { useCloneProfile } from './hooks/useCloneProfile';
import { useChat } from './hooks/useChat';
import { useReviewPolling } from './hooks/useReviewPolling';
import { useState, useEffect } from 'react';

import ErrorBoundary from './components/ErrorBoundary';
import ParaGPTLanding from './pages/paragpt/Landing';
import ParaGPTChat from './pages/paragpt/Chat';
import SacredArchiveLanding from './pages/sacred-archive/Landing';
import SacredArchiveChat from './pages/sacred-archive/Chat';
import ReviewDashboard from './pages/review/Dashboard';
import AnalyticsDashboard from './pages/analytics/Dashboard';

function ClonePage() {
  const { slug } = useParams<{ slug: string }>();
  const { profile, loading, error, retry } = useCloneProfile(slug || '');
  const { messages, setMessages, isLoading, currentNode, error: chatError, sendMessage, clearMessages } = useChat(slug || '');
  const [chatActive, setChatActive] = useState(false);
  const [accessTier, setAccessTier] = useState('public');
  const [selectedModel, setSelectedModel] = useState('');

  // Reset local state when slug changes (navigating between clones)
  useEffect(() => {
    setChatActive(false);
    setAccessTier('public');
    setSelectedModel('');
  }, [slug]);

  // Persistent anonymous user ID for conversation history & Mem0 scoping
  const [userId] = useState(() => {
    const stored = localStorage.getItem('dce_user_id');
    if (stored) return stored;
    const newId = crypto.randomUUID();
    localStorage.setItem('dce_user_id', newId);
    return newId;
  });

  const handleNewConversation = () => {
    clearMessages();
    setChatActive(false);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-para-navy">
        <div className="flex gap-1">
          <span className="w-3 h-3 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-3 h-3 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-3 h-3 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="h-full flex items-center justify-center bg-para-navy text-white">
        <div className="text-center max-w-md px-6">
          <div className="text-6xl mb-4 opacity-30">404</div>
          <h1 className="text-xl font-semibold mb-2">Clone not found</h1>
          <p className="text-gray-500 text-sm mb-6">{error || `No clone profile exists for "/${slug}". Check the URL and try again.`}</p>
          <div className="flex items-center justify-center gap-3">
            {error && (
              <button
                onClick={retry}
                className="px-5 py-2.5 rounded-full bg-para-teal text-white text-sm font-medium hover:opacity-90 transition-opacity"
              >
                Retry
              </button>
            )}
            <a
              href="/paragpt-client"
              className="inline-block px-5 py-2.5 rounded-full bg-gray-700 text-white text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Go to ParaGPT
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Poll for review status updates (Sacred Archive: replaces rejected responses with silence)
  // No-op for ParaGPT (no messages will have review_id)
  useReviewPolling(
    slug || '',
    messages,
    setMessages,
    profile.silence_message || 'This response has been retracted by a reviewer.',
  );

  const isSacredArchive = profile.generation_mode === 'mirror_only';

  const handleSend = (query: string) => {
    if (!chatActive) setChatActive(true);
    sendMessage(query, userId, accessTier, selectedModel);
  };

  const handleQuestionClick = (question: string) => {
    setChatActive(true);
    sendMessage(question, userId, accessTier, selectedModel);
  };

  if (isSacredArchive) {
    if (!chatActive) {
      return (
        <div className="h-full bg-sacred-brown">
          <SacredArchiveLanding
            profile={profile}
            onSelectTier={(tier) => setAccessTier(tier)}
            onSendMessage={handleSend}
            onQuestionClick={handleQuestionClick}
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
          />
        </div>
      );
    }
    return (
      <div className="h-full bg-sacred-brown">
        <SacredArchiveChat
          messages={messages}
          isLoading={isLoading}
          currentNode={currentNode}
          onSendMessage={handleSend}
          onNewConversation={handleNewConversation}
          accessTier={accessTier}
          profile={profile}
          error={chatError}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
        />
      </div>
    );
  }

  if (!chatActive) {
    return (
      <div className="h-full bg-para-navy">
        <ParaGPTLanding profile={profile} onSendMessage={handleSend} onQuestionClick={handleQuestionClick} selectedModel={selectedModel} onModelChange={setSelectedModel} />
      </div>
    );
  }

  return (
    <div className="h-full bg-para-navy">
      <ParaGPTChat messages={messages} isLoading={isLoading} currentNode={currentNode} onSendMessage={handleSend} onNewConversation={handleNewConversation} profile={profile} error={chatError} selectedModel={selectedModel} onModelChange={setSelectedModel} />
    </div>
  );
}

function ReviewPage() {
  const { slug } = useParams<{ slug: string }>();
  return (
    <div className="h-full bg-sacred-brown">
      <ReviewDashboard slug={slug || ''} />
    </div>
  );
}

function AnalyticsPage() {
  const { slug } = useParams<{ slug: string }>();
  return <AnalyticsDashboard slug={slug || ''} />;
}

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Navigate to="/paragpt-client" replace />} />
          <Route path="/:slug" element={<ClonePage />} />
          <Route path="/:slug/review" element={<ReviewPage />} />
          <Route path="/:slug/analytics" element={<AnalyticsPage />} />
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
