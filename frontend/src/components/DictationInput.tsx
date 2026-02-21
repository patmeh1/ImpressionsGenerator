'use client';

import React from 'react';
import { X } from 'lucide-react';

interface DictationInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function DictationInput({
  value,
  onChange,
  disabled = false,
}: DictationInputProps) {
  const maxChars = 10000;

  return (
    <div className="relative">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        maxLength={maxChars}
        rows={12}
        placeholder="Paste or type dictation text here... e.g., 'CT abdomen and pelvis with contrast. Comparison: Prior CT dated 01/15/2024. Findings: The liver is normal in size and attenuation...'"
        className="input-field resize-y min-h-[200px] font-mono text-sm leading-relaxed pr-10"
      />
      {value && !disabled && (
        <button
          onClick={() => onChange('')}
          className="absolute top-3 right-3 p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          title="Clear"
        >
          <X size={16} />
        </button>
      )}
      <div className="flex justify-between mt-1 text-xs text-slate-500 dark:text-slate-400">
        <span>
          {value.length > 0 ? `${value.split(/\s+/).filter(Boolean).length} words` : 'No text entered'}
        </span>
        <span>
          {value.length.toLocaleString()} / {maxChars.toLocaleString()} characters
        </span>
      </div>
    </div>
  );
}
