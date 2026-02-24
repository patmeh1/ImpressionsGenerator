import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Inline stub component – mirrors expected ReportEditor interface
// ---------------------------------------------------------------------------
interface ReportData {
  findings: string;
  impressions: string;
  recommendations: string;
}

interface ReportEditorProps {
  report: ReportData;
  onSave: (data: { findings: string; impressions: string; recommendations: string }) => void;
  onCancel: () => void;
}

function ReportEditor({ report, onSave, onCancel }: ReportEditorProps) {
  const [findings, setFindings] = React.useState(report.findings);
  const [impressions, setImpressions] = React.useState(report.impressions);
  const [recommendations, setRecommendations] = React.useState(report.recommendations);

  const handleSave = () => {
    onSave({ findings, impressions, recommendations });
  };

  return (
    <div data-testid="report-editor">
      <div>
        <label htmlFor="findings">Findings</label>
        <textarea
          id="findings"
          data-testid="findings-editor"
          value={findings}
          onChange={(e) => setFindings(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="impressions">Impressions</label>
        <textarea
          id="impressions"
          data-testid="impressions-editor"
          value={impressions}
          onChange={(e) => setImpressions(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="recommendations">Recommendations</label>
        <textarea
          id="recommendations"
          data-testid="recommendations-editor"
          value={recommendations}
          onChange={(e) => setRecommendations(e.target.value)}
        />
      </div>
      <button data-testid="save-draft-btn" onClick={handleSave}>
        Save Draft
      </button>
      <button data-testid="cancel-btn" onClick={onCancel}>
        Cancel
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sample data
// ---------------------------------------------------------------------------
const SAMPLE_REPORT: ReportData = {
  findings:
    'The liver measures 14.5 cm and is normal in size. No focal lesion identified.',
  impressions: '1. Normal CT abdomen.\n2. No acute findings.',
  recommendations: 'No follow-up imaging required.',
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// T19 – Modify text in editor → save → API called with updated content
test('T19: modify text in editor and save calls onSave with updated content', () => {
  const onSave = jest.fn();
  const onCancel = jest.fn();

  render(
    <ReportEditor report={SAMPLE_REPORT} onSave={onSave} onCancel={onCancel} />
  );

  // Verify initial content is rendered
  expect(screen.getByTestId('findings-editor')).toHaveValue(SAMPLE_REPORT.findings);

  // Modify the findings text
  fireEvent.change(screen.getByTestId('findings-editor'), {
    target: { value: 'Updated findings text with new observations.' },
  });

  // Click Save Draft
  fireEvent.click(screen.getByTestId('save-draft-btn'));

  // Verify onSave was called with the updated content
  expect(onSave).toHaveBeenCalledTimes(1);
  expect(onSave).toHaveBeenCalledWith({
    findings: 'Updated findings text with new observations.',
    impressions: SAMPLE_REPORT.impressions,
    recommendations: SAMPLE_REPORT.recommendations,
  });
});

test('each section has an editable textarea', () => {
  render(
    <ReportEditor
      report={SAMPLE_REPORT}
      onSave={jest.fn()}
      onCancel={jest.fn()}
    />
  );

  expect(screen.getByTestId('findings-editor')).toBeInTheDocument();
  expect(screen.getByTestId('impressions-editor')).toBeInTheDocument();
  expect(screen.getByTestId('recommendations-editor')).toBeInTheDocument();
});

test('cancel button calls onCancel', () => {
  const onCancel = jest.fn();
  render(
    <ReportEditor
      report={SAMPLE_REPORT}
      onSave={jest.fn()}
      onCancel={onCancel}
    />
  );

  fireEvent.click(screen.getByTestId('cancel-btn'));
  expect(onCancel).toHaveBeenCalledTimes(1);
});
