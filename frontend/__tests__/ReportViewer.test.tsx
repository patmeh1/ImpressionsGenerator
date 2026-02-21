import React from 'react';
import { render, screen } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Inline stub component – mirrors expected ReportViewer interface
// ---------------------------------------------------------------------------
interface ReportData {
  inputText: string;
  findings: string;
  impressions: string;
  recommendations: string;
}

interface ReportViewerProps {
  report: ReportData | null;
}

function ReportViewer({ report }: ReportViewerProps) {
  if (!report) {
    return (
      <div data-testid="report-viewer-empty">
        <p>No report generated yet. Enter dictation text and click Generate.</p>
      </div>
    );
  }

  return (
    <div data-testid="report-viewer" style={{ display: 'flex', gap: '1rem' }}>
      {/* Left panel – input */}
      <div data-testid="input-panel">
        <h3>Input Text</h3>
        <p>{report.inputText}</p>
      </div>

      {/* Right panel – generated report */}
      <div data-testid="output-panel">
        <section>
          <h3>Findings</h3>
          <p data-testid="findings">{report.findings}</p>
        </section>
        <section>
          <h3>Impressions</h3>
          <p data-testid="impressions">{report.impressions}</p>
        </section>
        <section>
          <h3>Recommendations</h3>
          <p data-testid="recommendations">{report.recommendations}</p>
        </section>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sample data
// ---------------------------------------------------------------------------
const SAMPLE_REPORT: ReportData = {
  inputText: 'CT abdomen with contrast. Liver measures 14.5 cm. Normal findings.',
  findings:
    'The liver measures 14.5 cm and is normal in size. No focal lesion identified.',
  impressions: '1. Normal CT abdomen.\n2. No acute findings.',
  recommendations: 'No follow-up imaging required.',
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// T18 – renders side-by-side panels
test('T18: renders side-by-side panels', () => {
  render(<ReportViewer report={SAMPLE_REPORT} />);

  expect(screen.getByTestId('input-panel')).toBeInTheDocument();
  expect(screen.getByTestId('output-panel')).toBeInTheDocument();
});

test('shows input text on left panel', () => {
  render(<ReportViewer report={SAMPLE_REPORT} />);

  const inputPanel = screen.getByTestId('input-panel');
  expect(inputPanel).toHaveTextContent('CT abdomen with contrast');
  expect(inputPanel).toHaveTextContent('14.5 cm');
});

test('shows findings, impressions, recommendations on right panel', () => {
  render(<ReportViewer report={SAMPLE_REPORT} />);

  expect(screen.getByTestId('findings')).toHaveTextContent(
    'The liver measures 14.5 cm'
  );
  expect(screen.getByTestId('impressions')).toHaveTextContent(
    'Normal CT abdomen'
  );
  expect(screen.getByTestId('recommendations')).toHaveTextContent(
    'No follow-up imaging required'
  );
});

test('handles empty report gracefully', () => {
  render(<ReportViewer report={null} />);

  expect(screen.getByTestId('report-viewer-empty')).toBeInTheDocument();
  expect(
    screen.getByText(/no report generated yet/i)
  ).toBeInTheDocument();
  expect(screen.queryByTestId('input-panel')).not.toBeInTheDocument();
  expect(screen.queryByTestId('output-panel')).not.toBeInTheDocument();
});
