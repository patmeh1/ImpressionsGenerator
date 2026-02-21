'use client';

import React, { useState, useCallback, useRef } from 'react';
import { Upload, File, CheckCircle, AlertCircle } from 'lucide-react';

interface FileUploaderProps {
  doctorId: string;
  onUploadComplete: () => void;
}

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
];
const ACCEPTED_EXTENSIONS = '.pdf,.docx,.txt';
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export default function FileUploader({ doctorId, onUploadComplete }: FileUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type) && !file.name.match(/\.(pdf|docx|txt)$/i)) {
      return 'Invalid file type. Please upload PDF, DOCX, or TXT files.';
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `File too large. Maximum size is ${MAX_SIZE_MB}MB.`;
    }
    return null;
  };

  const uploadFile = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      setUploading(true);
      setError(null);
      setSuccess(false);
      setProgress(0);

      try {
        const { uploadNote } = await import('@/lib/api');
        // Simulate progress
        const progressInterval = setInterval(() => {
          setProgress((prev) => Math.min(prev + 15, 90));
        }, 200);

        await uploadNote(doctorId, file);

        clearInterval(progressInterval);
        setProgress(100);
        setSuccess(true);
        onUploadComplete();

        setTimeout(() => {
          setSuccess(false);
          setProgress(0);
        }, 3000);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [doctorId, onUploadComplete]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) uploadFile(file);
    },
    [uploadFile]
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragOver
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-slate-300 dark:border-slate-600 hover:border-primary-400 hover:bg-slate-50 dark:hover:bg-slate-800'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          onChange={handleFileSelect}
          className="hidden"
        />
        <Upload size={36} className="mx-auto mb-3 text-slate-400" />
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Drag & drop a file here, or click to browse
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          PDF, DOCX, or TXT • Max {MAX_SIZE_MB}MB
        </p>
      </div>

      {uploading && (
        <div className="flex items-center gap-3">
          <File size={16} className="text-primary-500" />
          <div className="flex-1">
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
          <span className="text-xs text-slate-500">{progress}%</span>
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm">
          <CheckCircle size={16} />
          File uploaded successfully
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}
    </div>
  );
}
