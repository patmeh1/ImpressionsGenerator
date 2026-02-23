'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getReport, updateReport, approveReport, rejectReport, getReportVersions } from '@/lib/api';
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

  const handleApprove = async () => {
    if (!report) return;
    setSaving(true);
    try {
      const updated = await approveReport(report.id);
      setReport(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    if (!report) return;
    setSaving(true);
    try {
      await rejectReport(report.id);
      router.push('/generate');
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleSave = useCallback(async (data: { findings: string; impressions: string; recommendations: string }) => {
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
  }, [report, reportId]);

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
            onClick={handleApprove}
            disabled={saving || report.status === 'final'}
            className="btn-primary flex items-center gap-1.5 text-sm bg-green-600 hover:bg-green-700"
          >
            <CheckCircle size={14} /> Approve
          </button>
          <button
            onClick={handleReject}
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
                {versions.map((v) => (
                  <li
                    key={v.id}
                    className="text-xs bg-slate-50 dark:bg-slate-900 rounded-lg p-2.5"
                  >
                    <div className="flex justify-between mb-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        v{v.version_number}
                      </span>
                      <span className="text-slate-400">
                        {new Date(v.created_at).toLocaleDateString()}
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
