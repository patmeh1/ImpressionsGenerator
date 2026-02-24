'use client';

import React, { useState } from 'react';
import { Star, Send, CheckCircle } from 'lucide-react';
import { submitFeedback } from '@/lib/api';

interface StyleFeedbackProps {
  reportId: string;
}

export default function StyleFeedback({ reportId }: StyleFeedbackProps) {
  const [rating, setRating] = useState(0);
  const [hoveredStar, setHoveredStar] = useState(0);
  const [feedbackText, setFeedbackText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (rating === 0) return;
    setSubmitting(true);
    setError('');
    try {
      await submitFeedback(reportId, {
        rating,
        feedback_text: feedbackText,
      });
      setSubmitted(true);
    } catch (err) {
      setError('Failed to submit feedback. Please try again.');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="card p-4" data-testid="feedback-success">
        <div className="flex items-center gap-2 text-green-600">
          <CheckCircle size={20} />
          <span className="font-medium text-sm">Thank you for your feedback!</span>
        </div>
        <div className="flex items-center gap-1 mt-2">
          {[1, 2, 3, 4, 5].map((star) => (
            <Star
              key={star}
              size={16}
              className={star <= rating ? 'text-yellow-400 fill-yellow-400' : 'text-slate-300'}
            />
          ))}
          <span className="text-xs text-slate-500 ml-1">({rating}/5)</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-4" data-testid="style-feedback">
      <h3 className="font-semibold text-sm text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
        <Star size={16} className="text-yellow-500" />
        Rate Style Accuracy
      </h3>

      {/* Star Rating */}
      <div className="flex items-center gap-1 mb-3" data-testid="star-rating">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => setRating(star)}
            onMouseEnter={() => setHoveredStar(star)}
            onMouseLeave={() => setHoveredStar(0)}
            className="p-0.5 transition-transform hover:scale-110"
            aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
            data-testid={`star-${star}`}
          >
            <Star
              size={24}
              className={
                star <= (hoveredStar || rating)
                  ? 'text-yellow-400 fill-yellow-400'
                  : 'text-slate-300 dark:text-slate-600'
              }
            />
          </button>
        ))}
        {rating > 0 && (
          <span className="text-xs text-slate-500 ml-2">{rating}/5</span>
        )}
      </div>

      {/* Feedback Text */}
      <textarea
        value={feedbackText}
        onChange={(e) => setFeedbackText(e.target.value)}
        placeholder="Optional: describe what matched or didn't match your style..."
        className="input-field w-full text-sm mb-3"
        rows={2}
        data-testid="feedback-text"
      />

      {error && (
        <p className="text-xs text-red-500 mb-2">{error}</p>
      )}

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={rating === 0 || submitting}
        className="btn-primary flex items-center gap-1.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid="submit-feedback"
      >
        <Send size={14} />
        {submitting ? 'Submitting...' : 'Submit Feedback'}
      </button>
    </div>
  );
}
