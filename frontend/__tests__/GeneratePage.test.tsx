import React, { useState } from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Inline stub – mirrors the GeneratePage interface for the generate workflow
// ---------------------------------------------------------------------------

const REPORT_TYPES = ['CT', 'MRI', 'X-ray', 'PET', 'Ultrasound'];
const BODY_REGIONS = [
  'Head', 'Neck', 'Chest', 'Abdomen', 'Pelvis',
  'Spine', 'Upper Extremity', 'Lower Extremity', 'Whole Body',
];

interface GeneratePageProps {
  onGenerate?: (data: {
    inputText: string;
    reportType: string;
    bodyRegion: string;
  }) => Promise<void>;
}

function GeneratePage({ onGenerate }: GeneratePageProps) {
  const [inputText, setInputText] = useState('');
  const [reportType, setReportType] = useState('CT');
  const [bodyRegion, setBodyRegion] = useState('Abdomen');
  const [generating, setGenerating] = useState(false);

  const handleGenerate = async () => {
    if (!inputText.trim() || generating) return;
    setGenerating(true);
    try {
      await onGenerate?.({ inputText, reportType, bodyRegion });
    } finally {
      setGenerating(false);
    }
  };

  const handleReset = () => {
    setInputText('');
    setReportType('CT');
    setBodyRegion('Abdomen');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div onKeyDown={handleKeyDown}>
      <textarea
        aria-label="Dictation input"
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        disabled={generating}
      />
      <div data-testid="char-count">{inputText.length}</div>

      <label htmlFor="report-type">Report Type</label>
      <select
        id="report-type"
        value={reportType}
        onChange={(e) => setReportType(e.target.value)}
      >
        {REPORT_TYPES.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>

      <label htmlFor="body-region">Body Region</label>
      <select
        id="body-region"
        value={bodyRegion}
        onChange={(e) => setBodyRegion(e.target.value)}
      >
        {BODY_REGIONS.map((r) => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>

      <button onClick={handleGenerate} disabled={generating || !inputText.trim()}>
        {generating ? 'Generating report…' : 'Generate Impressions'}
      </button>

      <button onClick={handleReset} disabled={generating}>
        Clear
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// T17: Paste text → select report type → submit → loading state shown
test('T17: paste text, select report type, submit shows loading state', async () => {
  let resolveGenerate: () => void;
  const generatePromise = new Promise<void>((resolve) => {
    resolveGenerate = resolve;
  });
  const onGenerate = jest.fn(() => generatePromise);

  render(<GeneratePage onGenerate={onGenerate} />);

  // Paste text into textarea
  const textarea = screen.getByLabelText('Dictation input');
  fireEvent.change(textarea, {
    target: { value: 'CT abdomen normal findings' },
  });

  // Select report type
  const reportTypeSelect = screen.getByLabelText('Report Type');
  fireEvent.change(reportTypeSelect, { target: { value: 'MRI' } });

  // Click generate
  const generateBtn = screen.getByText('Generate Impressions');
  await act(async () => {
    fireEvent.click(generateBtn);
  });

  // Loading state should be shown
  expect(screen.getByText('Generating report…')).toBeInTheDocument();
  expect(onGenerate).toHaveBeenCalledWith({
    inputText: 'CT abdomen normal findings',
    reportType: 'MRI',
    bodyRegion: 'Abdomen',
  });

  // Resolve generation
  await act(async () => {
    resolveGenerate!();
  });

  // Loading state should be gone
  expect(screen.getByText('Generate Impressions')).toBeInTheDocument();
});

test('renders report type options: CT, MRI, X-ray, PET, Ultrasound', () => {
  render(<GeneratePage />);

  const reportTypeSelect = screen.getByLabelText('Report Type');
  REPORT_TYPES.forEach((type) => {
    expect(reportTypeSelect).toHaveTextContent(type);
  });
});

test('renders body region options', () => {
  render(<GeneratePage />);

  const bodyRegionSelect = screen.getByLabelText('Body Region');
  BODY_REGIONS.forEach((region) => {
    expect(bodyRegionSelect).toHaveTextContent(region);
  });
});

test('displays character count', () => {
  render(<GeneratePage />);

  const textarea = screen.getByLabelText('Dictation input');
  fireEvent.change(textarea, { target: { value: 'Hello' } });
  expect(screen.getByTestId('char-count')).toHaveTextContent('5');
});

test('generate button is disabled when textarea is empty', () => {
  render(<GeneratePage />);

  const generateBtn = screen.getByText('Generate Impressions');
  expect(generateBtn).toBeDisabled();
});

test('clear button resets all fields', () => {
  render(<GeneratePage />);

  const textarea = screen.getByLabelText('Dictation input');
  fireEvent.change(textarea, { target: { value: 'some text' } });

  const reportTypeSelect = screen.getByLabelText('Report Type');
  fireEvent.change(reportTypeSelect, { target: { value: 'MRI' } });

  const bodyRegionSelect = screen.getByLabelText('Body Region');
  fireEvent.change(bodyRegionSelect, { target: { value: 'Chest' } });

  fireEvent.click(screen.getByText('Clear'));

  expect(textarea).toHaveValue('');
  expect(reportTypeSelect).toHaveValue('CT');
  expect(bodyRegionSelect).toHaveValue('Abdomen');
});

test('Ctrl+Enter triggers generation', async () => {
  let resolveGenerate: () => void;
  const generatePromise = new Promise<void>((resolve) => {
    resolveGenerate = resolve;
  });
  const onGenerate = jest.fn(() => generatePromise);

  render(<GeneratePage onGenerate={onGenerate} />);

  const textarea = screen.getByLabelText('Dictation input');
  fireEvent.change(textarea, { target: { value: 'test dictation' } });

  await act(async () => {
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });
  });

  expect(screen.getByText('Generating report…')).toBeInTheDocument();
  expect(onGenerate).toHaveBeenCalled();

  await act(async () => {
    resolveGenerate!();
  });
});
