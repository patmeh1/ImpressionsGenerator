'use client';

import React from 'react';
import type { Report } from '@/lib/types';
import { FileText, ClipboardList, Lightbulb } from 'lucide-react';

interface ReportViewerProps {
  inputText: string;
  report: Report;
}

function SectionCard({
  title,
  content,
  icon: Icon,
  color,
}: {
  title: string;
  content: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className={`border-l-4 ${color} bg-white dark:bg-slate-800 rounded-r-lg p-4`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon size={16} className="text-slate-500" />
        <h4 className="font-semibold text-sm uppercase tracking-wide text-slate-600 dark:text-slate-300">
          {title}
        </h4>
      </div>
      <p className="text-slate-800 dark:text-slate-200 text-sm whitespace-pre-wrap leading-relaxed">
        {content}
      </p>
    </div>
  );
}

export default function ReportViewer({ inputText, report }: ReportViewerProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: Original Dictation */}
      <div className="card p-5">
        <h3 className="section-heading mb-3 flex items-center gap-2">
          <FileText size={20} className="text-primary-600" />
          Original Dictation
        </h3>
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4 text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed font-mono max-h-[500px] overflow-y-auto">
          {inputText}
        </div>
        <div className="mt-2 text-xs text-slate-500">
          {inputText.split(/\s+/).filter(Boolean).length} words •{' '}
          {report.report_type} • {report.body_region}
        </div>
      </div>

      {/* Right: Generated Report */}
      <div className="card p-5">
        <h3 className="section-heading mb-4 flex items-center gap-2">
          <ClipboardList size={20} className="text-teal-600" />
          Generated Report
        </h3>
        <div className="space-y-4">
          <SectionCard
            title="Findings"
            content={report.findings}
            icon={FileText}
            color="border-primary-500"
          />
          <SectionCard
            title="Impressions"
            content={report.impressions}
            icon={Lightbulb}
            color="border-teal-500"
          />
          <SectionCard
            title="Recommendations"
            content={report.recommendations}
            icon={ClipboardList}
            color="border-amber-500"
          />
        </div>
        <div className="mt-3 flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              report.status === 'approved' || report.status === 'final'
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : report.status === 'rejected'
                  ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  : report.status === 'edited'
                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
            }`}
          >
            {report.status}
          </span>
        </div>
      </div>
    </div>
  );
}
