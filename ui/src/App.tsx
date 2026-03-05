import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { useCloneProfile } from './hooks/useCloneProfile';
import { useChat } from './hooks/useChat';
import { useState } from 'react';

import ErrorBoundary from './components/ErrorBoundary';
import ParaGPTLanding from './pages/paragpt/Landing';
import ParaGPTChat from './pages/paragpt/Chat';
import SacredArchiveLanding from './pages/sacred-archive/Landing';
import SacredArchiveChat from './pages/sacred-archive/Chat';
import ReviewDashboard from './pages/review/Dashboard';
import AnalyticsDashboard from './pages/analytics/Dashboard';

function ClonePage() {
  const { slug } = useParams<{ slug: string }>();
  const { profile, loading, error } = useCloneProfile(slug || '');
  const { messages, isLoading, currentNode, error: chatError, sendMessage } = useChat(slug || '');
  const [chatActive, setChatActive] = useState(false);
  const [accessTier, setAccessTier] = useState('public');

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
        <div className="text-center">
          <p className="text-red-400 mb-2">Failed to load clone profile</p>
          <p className="text-gray-500 text-sm">{error || 'Clone not found'}</p>
        </div>
      </div>
    );
  }

  const isSacredArchive = profile.generation_mode === 'mirror_only';

  const handleSend = (query: string) => {
    if (!chatActive) setChatActive(true);
    sendMessage(query, 'anonymous', accessTier);
  };

  const handleQuestionClick = (question: string) => {
    setChatActive(true);
    sendMessage(question, 'anonymous', accessTier);
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
          accessTier={accessTier}
          profile={profile}
          error={chatError}
        />
      </div>
    );
  }

  if (!chatActive) {
    return (
      <div className="h-full bg-para-navy">
        <ParaGPTLanding profile={profile} onSendMessage={handleSend} onQuestionClick={handleQuestionClick} />
      </div>
    );
  }

  return (
    <div className="h-full bg-para-navy">
      <ParaGPTChat messages={messages} isLoading={isLoading} currentNode={currentNode} onSendMessage={handleSend} profile={profile} error={chatError} />
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
