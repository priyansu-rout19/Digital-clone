import { useState } from 'react';
import { submitFeedback } from '../api/client';

interface FeedbackWidgetProps {
  slug: string;
  sessionId?: string;
  onClose?: () => void;
}

export default function FeedbackWidget({ slug, sessionId, onClose }: FeedbackWidgetProps) {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (rating === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitFeedback(slug, rating, comment || undefined, sessionId);
      setSubmitted(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 text-center max-w-sm">
        <p className="text-amber-400 text-lg font-semibold mb-2">Thank you!</p>
        <p className="text-gray-400 text-sm">Your feedback helps us improve.</p>
        {onClose && (
          <button
            onClick={onClose}
            className="mt-4 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Close
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-sm">
      <h4 className="text-white text-sm font-semibold mb-4">How was your experience?</h4>

      {/* Star rating */}
      <div className="flex gap-1 mb-4 justify-center">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => setRating(star)}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            className="text-2xl transition-colors focus:outline-none"
            aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
          >
            <span className={star <= (hovered || rating) ? 'text-amber-400' : 'text-gray-600'}>
              ★
            </span>
          </button>
        ))}
      </div>

      {/* Comment */}
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Any additional comments? (optional)"
        maxLength={1000}
        className="w-full h-20 bg-gray-800 border border-gray-700 rounded-xl p-3 text-sm text-white placeholder-gray-500 outline-none resize-none mb-3"
      />

      {error && <p className="text-red-400 text-xs mb-2">{error}</p>}

      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={rating === 0 || submitting}
          className="flex-1 py-2 rounded-xl bg-amber-500 text-gray-900 font-semibold text-sm hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? 'Sending...' : 'Submit'}
        </button>
        {onClose && (
          <button
            onClick={onClose}
            disabled={submitting}
            className="px-4 py-2 rounded-xl bg-gray-800 text-gray-400 text-sm hover:bg-gray-700 transition-colors disabled:opacity-40"
          >
            Skip
          </button>
        )}
      </div>
    </div>
  );
}
