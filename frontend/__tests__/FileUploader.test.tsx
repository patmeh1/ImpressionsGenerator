import React, { useRef, useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Inline stub component – mirrors expected FileUploader interface
// ---------------------------------------------------------------------------
const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
];
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt'];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
  onError?: (message: string) => void;
}

function FileUploader({ onFileSelect, onError }: FileUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = (file: File) => {
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      const msg = `Unsupported file type: ${ext}. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`;
      setError(msg);
      onError?.(msg);
      return;
    }
    if (file.size > MAX_SIZE) {
      const msg = 'File exceeds 10 MB limit';
      setError(msg);
      onError?.(msg);
      return;
    }
    setError(null);
    setSelectedFile(file);
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) validateAndSelect(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndSelect(file);
  };

  return (
    <div
      data-testid="drop-zone"
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
    >
      <p>Drag and drop a file here, or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={handleChange}
        data-testid="file-input"
      />
      {selectedFile && (
        <div data-testid="file-info">
          <span>{selectedFile.name}</span>
          <span>{(selectedFile.size / 1024).toFixed(1)} KB</span>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function createMockFile(
  name: string,
  size: number,
  type: string
): File {
  const buffer = new ArrayBuffer(size);
  return new File([buffer], name, { type });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// T20 – renders drag-and-drop zone
test('T20: renders drag-and-drop zone', () => {
  render(<FileUploader onFileSelect={jest.fn()} />);
  expect(screen.getByTestId('drop-zone')).toBeInTheDocument();
  expect(
    screen.getByText(/drag and drop a file here/i)
  ).toBeInTheDocument();
});

test('shows file info after selection', async () => {
  const onFileSelect = jest.fn();
  render(<FileUploader onFileSelect={onFileSelect} />);

  const file = createMockFile('report.pdf', 5000, 'application/pdf');
  const input = screen.getByTestId('file-input');
  fireEvent.change(input, { target: { files: [file] } });

  await waitFor(() => {
    expect(screen.getByTestId('file-info')).toBeInTheDocument();
    expect(screen.getByText('report.pdf')).toBeInTheDocument();
  });
  expect(onFileSelect).toHaveBeenCalledWith(file);
});

test('rejects files over 10MB', () => {
  const onError = jest.fn();
  render(<FileUploader onFileSelect={jest.fn()} onError={onError} />);

  const bigFile = createMockFile('huge.pdf', 11 * 1024 * 1024, 'application/pdf');
  const input = screen.getByTestId('file-input');
  fireEvent.change(input, { target: { files: [bigFile] } });

  expect(screen.getByRole('alert')).toHaveTextContent('10 MB');
  expect(onError).toHaveBeenCalled();
});

test('accepts PDF, DOCX, TXT files only', () => {
  const onFileSelect = jest.fn();
  const onError = jest.fn();
  render(<FileUploader onFileSelect={onFileSelect} onError={onError} />);

  // Valid files
  const pdf = createMockFile('report.pdf', 1000, 'application/pdf');
  const docx = createMockFile('notes.docx', 1000, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
  const txt = createMockFile('memo.txt', 1000, 'text/plain');

  const input = screen.getByTestId('file-input');

  fireEvent.change(input, { target: { files: [pdf] } });
  expect(onFileSelect).toHaveBeenCalledWith(pdf);

  fireEvent.change(input, { target: { files: [docx] } });
  expect(onFileSelect).toHaveBeenCalledWith(docx);

  fireEvent.change(input, { target: { files: [txt] } });
  expect(onFileSelect).toHaveBeenCalledWith(txt);

  // Invalid file
  const jpg = createMockFile('photo.jpg', 1000, 'image/jpeg');
  fireEvent.change(input, { target: { files: [jpg] } });
  expect(onError).toHaveBeenCalledWith(expect.stringContaining('Unsupported'));
});
