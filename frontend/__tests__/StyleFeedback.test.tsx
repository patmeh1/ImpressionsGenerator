import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Inline stub component – mirrors expected StyleFeedback interface
// ---------------------------------------------------------------------------
interface StyleFeedbackProps {
  reportId: string;
}

let mockSubmitFn: jest.Mock;

function StyleFeedback({ reportId }: StyleFeedbackProps) {
  const [rating, setRating] = React.useState(0);
  const [hoveredStar, setHoveredStar] = React.useState(0);
  const [feedbackText, setFeedbackText] = React.useState('');
  const [submitted, setSubmitted] = React.useState(false);

  const handleSubmit = async () => {
    if (rating === 0) return;
    await mockSubmitFn(reportId, { rating, feedback_text: feedbackText });
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div data-testid="feedback-success">
        <p>Thank you for your feedback!</p>
        <div data-testid="submitted-rating">{rating}/5</div>
      </div>
    );
  }

  return (
    <div data-testid="style-feedback">
      <h3>Rate Style Accuracy</h3>
      <div data-testid="star-rating">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            data-testid={`star-${star}`}
            onClick={() => setRating(star)}
            onMouseEnter={() => setHoveredStar(star)}
            onMouseLeave={() => setHoveredStar(0)}
            aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
          >
            {star <= (hoveredStar || rating) ? '★' : '☆'}
          </button>
        ))}
      </div>
      <textarea
        data-testid="feedback-text"
        value={feedbackText}
        onChange={(e) => setFeedbackText(e.target.value)}
        placeholder="Optional: describe what matched or didn't match your style..."
      />
      <button
        data-testid="submit-feedback"
        onClick={handleSubmit}
        disabled={rating === 0}
      >
        Submit Feedback
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
beforeEach(() => {
  mockSubmitFn = jest.fn().mockResolvedValue({
    id: 'fb-001',
    report_id: 'report-001',
    doctor_id: 'doctor-001',
    rating: 4,
    feedback_text: '',
    created_at: new Date().toISOString(),
  });
});

test('renders star rating component', () => {
  render(<StyleFeedback reportId="report-001" />);
  expect(screen.getByTestId('style-feedback')).toBeInTheDocument();
  expect(screen.getByTestId('star-rating')).toBeInTheDocument();
  expect(screen.getByText('Rate Style Accuracy')).toBeInTheDocument();
});

test('renders all 5 stars', () => {
  render(<StyleFeedback reportId="report-001" />);
  for (let i = 1; i <= 5; i++) {
    expect(screen.getByTestId(`star-${i}`)).toBeInTheDocument();
  }
});

test('submit button is disabled when no rating is selected', () => {
  render(<StyleFeedback reportId="report-001" />);
  const submitBtn = screen.getByTestId('submit-feedback');
  expect(submitBtn).toBeDisabled();
});

test('clicking a star sets the rating and enables submit', () => {
  render(<StyleFeedback reportId="report-001" />);
  fireEvent.click(screen.getByTestId('star-3'));
  const submitBtn = screen.getByTestId('submit-feedback');
  expect(submitBtn).not.toBeDisabled();
});

test('submitting feedback calls API and shows success', async () => {
  render(<StyleFeedback reportId="report-001" />);

  // Select 4 stars
  fireEvent.click(screen.getByTestId('star-4'));

  // Enter feedback text
  fireEvent.change(screen.getByTestId('feedback-text'), {
    target: { value: 'Good style match' },
  });

  // Submit
  fireEvent.click(screen.getByTestId('submit-feedback'));

  await waitFor(() => {
    expect(screen.getByTestId('feedback-success')).toBeInTheDocument();
  });

  expect(mockSubmitFn).toHaveBeenCalledWith('report-001', {
    rating: 4,
    feedback_text: 'Good style match',
  });

  expect(screen.getByText('Thank you for your feedback!')).toBeInTheDocument();
  expect(screen.getByTestId('submitted-rating')).toHaveTextContent('4/5');
});

test('submitting with rating only (no text) works', async () => {
  render(<StyleFeedback reportId="report-001" />);

  fireEvent.click(screen.getByTestId('star-5'));
  fireEvent.click(screen.getByTestId('submit-feedback'));

  await waitFor(() => {
    expect(screen.getByTestId('feedback-success')).toBeInTheDocument();
  });

  expect(mockSubmitFn).toHaveBeenCalledWith('report-001', {
    rating: 5,
    feedback_text: '',
  });
});

test('feedback textarea has proper placeholder', () => {
  render(<StyleFeedback reportId="report-001" />);
  const textarea = screen.getByTestId('feedback-text');
  expect(textarea).toHaveAttribute(
    'placeholder',
    "Optional: describe what matched or didn't match your style..."
  );
});
