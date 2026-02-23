'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getReport, updateReport, getReportVersions, approveReport, rejectReport } from '@/lib/api';
import type { Report, ReportVersion } from '@/lib/types';
import ReportViewer from '@/components/ReportViewer';
import ReportEditor from '@/components/ReportEditor';
import { CheckCircle, XCircle, Edit3, History, Loader2 } from 'lucide-react';

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params.id as string;

  const [report, setReport] = useState<Report | null>(null);
  const [versions, setVersions] = useState<ReportVersion[]>([]);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [r, v] = await Promise.all([
          getReport(reportId),
          getReportVersions(reportId).catch(() => []),
        ]);
        setReport(r);
        setVersions(v);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [reportId]);

  const handleStatusChange = async (status: 'final' | 'rejected') => {
    if (!report) return;
    setSaving(true);
    try {
      const updated = status === 'final'
        ? await approveReport(report.id)
        : await rejectReport(report.id);
      setReport(updated);
      const v = await getReportVersions(reportId).catch(() => []);
      setVersions(v);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async (data: { findings: string; impressions: string; recommendations: string }) => {
    if (!report) return;
    setSaving(true);
    try {
      const updated = await updateReport(report.id, data);
      setReport(updated);
      setEditing(false);
      const v = await getReportVersions(reportId).catch(() => []);
      setVersions(v);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="animate-spin text-primary-500" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="text-center py-20 text-slate-500">Report not found.</div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
          Review Report
        </h1>
        <div className="flex items-center gap-2">
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="btn-secondary flex items-center gap-1.5 text-sm"
            >
              <Edit3 size={14} /> Edit
            </button>
          )}
          <button
            onClick={() => handleStatusChange('final')}
            disabled={saving || report.status === 'final'}
            className="btn-primary flex items-center gap-1.5 text-sm bg-green-600 hover:bg-green-700"
          >
            <CheckCircle size={14} /> Approve
          </button>
          <button
            onClick={() => handleStatusChange('rejected')}
            disabled={saving || report.status === 'rejected'}
            className="btn-danger flex items-center gap-1.5 text-sm"
          >
            <XCircle size={14} /> Reject
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Main content */}
        <div className="xl:col-span-3">
          {editing ? (
            <div className="card p-5">
              <ReportEditor
                report={report}
                onSave={handleSave}
                onCancel={() => setEditing(false)}
              />
            </div>
          ) : (
            <ReportViewer inputText={report.input_text} report={report} />
          )}
        </div>

        {/* Version History Sidebar */}
        <div className="xl:col-span-1">
          <div className="card p-4">
            <h3 className="font-semibold text-sm text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
              <History size={16} /> Version History
            </h3>
            {versions.length === 0 ? (
              <p className="text-xs text-slate-500">No previous versions</p>
            ) : (
              <ul className="space-y-2">
                {versions.map((v, idx) => (
                  <li
                    key={idx}
                    className="text-xs bg-slate-50 dark:bg-slate-900 rounded-lg p-2.5"
                  >
                    <div className="flex justify-between mb-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        v{v.version}
                      </span>
                      <span className="text-slate-400">
                        {new Date(v.edited_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-slate-500 truncate">{v.edited_by}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
