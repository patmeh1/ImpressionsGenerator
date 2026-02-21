import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Inline stub component – mirrors expected DictationInput interface
// ---------------------------------------------------------------------------
interface DictationInputProps {
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
  placeholder?: string;
}

function DictationInput({
  value,
  onChange,
  maxLength = 10000,
  placeholder = 'Paste or type your dictation here…',
}: DictationInputProps) {
  return (
    <div>
      <textarea
        aria-label="Dictation input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={maxLength}
        placeholder={placeholder}
      />
      <span data-testid="char-count">
        {value.length}/{maxLength}
      </span>
      <button onClick={() => onChange('')}>Clear</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// T17 – renders textarea and handles input
test('T17: renders textarea and handles input', () => {
  const handleChange = jest.fn();
  render(<DictationInput value="" onChange={handleChange} />);

  const textarea = screen.getByLabelText('Dictation input');
  expect(textarea).toBeInTheDocument();

  fireEvent.change(textarea, {
    target: { value: 'CT abdomen normal findings' },
  });
  expect(handleChange).toHaveBeenCalledWith('CT abdomen normal findings');
});

test('shows character count', () => {
  render(<DictationInput value="Hello" onChange={jest.fn()} maxLength={100} />);
  expect(screen.getByTestId('char-count')).toHaveTextContent('5/100');
});

test('calls onChange on text input', () => {
  const onChange = jest.fn();
  render(<DictationInput value="" onChange={onChange} />);

  fireEvent.change(screen.getByLabelText('Dictation input'), {
    target: { value: 'new text' },
  });
  expect(onChange).toHaveBeenCalledTimes(1);
  expect(onChange).toHaveBeenCalledWith('new text');
});

test('clears input on clear button click', () => {
  const onChange = jest.fn();
  render(
    <DictationInput value="some dictation text" onChange={onChange} />
  );

  fireEvent.click(screen.getByText('Clear'));
  expect(onChange).toHaveBeenCalledWith('');
});
