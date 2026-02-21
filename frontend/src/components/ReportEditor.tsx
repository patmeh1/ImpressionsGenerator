'use client';

import React, { useState } from 'react';
import type { Report } from '@/lib/types';
import { Save, XCircle } from 'lucide-react';

interface ReportEditorProps {
  report: Report;
  onSave: (data: { findings: string; impressions: string; recommendations: string }) => void;
  onCancel: () => void;
}

export default function ReportEditor({ report, onSave, onCancel }: ReportEditorProps) {
  const [findings, setFindings] = useState(report.findings);
  const [impressions, setImpressions] = useState(report.impressions);
  const [recommendations, setRecommendations] = useState(report.recommendations);

  const handleSave = () => {
    onSave({ findings, impressions, recommendations });
  };

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wide">
          Findings
        </label>
        <textarea
          value={findings}
          onChange={(e) => setFindings(e.target.value)}
          rows={6}
          className="input-field font-mono text-sm resize-y"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wide">
          Impressions
        </label>
        <textarea
          value={impressions}
          onChange={(e) => setImpressions(e.target.value)}
          rows={4}
          className="input-field font-mono text-sm resize-y"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wide">
          Recommendations
        </label>
        <textarea
          value={recommendations}
          onChange={(e) => setRecommendations(e.target.value)}
          rows={3}
          className="input-field font-mono text-sm resize-y"
        />
      </div>

      <div className="flex gap-3 pt-2">
        <button onClick={handleSave} className="btn-primary flex items-center gap-2">
          <Save size={16} />
          Save Changes
        </button>
        <button onClick={onCancel} className="btn-secondary flex items-center gap-2">
          <XCircle size={16} />
          Cancel
        </button>
      </div>
    </div>
  );
}
