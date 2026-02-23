'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getReports, getAdminStats } from '@/lib/api';
import type { Report, UsageStatsData } from '@/lib/types';
import {
  Sparkles,
  FileText,
  History,
  Upload,
  ArrowRight,
  FileCheck,
  Clock,
  Activity,
} from 'lucide-react';

const quickActions = [
  { href: '/generate', label: 'New Report', icon: Sparkles, color: 'bg-primary-600' },
  { href: '/profile/notes', label: 'Upload Notes', icon: Upload, color: 'bg-teal-600' },
  { href: '/history', label: 'View History', icon: History, color: 'bg-amber-500' },
];

export default function DashboardPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [stats, setStats] = useState<UsageStatsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [reportsRes, statsRes] = await Promise.all([
          getReports(undefined, 1, 5),
          getAdminStats().catch(() => null),
        ]);
        setReports(reportsRes.items);
        setStats(statsRes);
      } catch (err) {
        console.error('Failed to load dashboard:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Dashboard</h1>

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="card p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-primary-600">
              <FileCheck size={20} className="text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">
                {stats.total_generations.toLocaleString()}
              </p>
              <p className="text-xs text-slate-500">Total Generations</p>
            </div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-teal-600">
              <Clock size={20} className="text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">
                {(stats.avg_response_time_ms / 1000).toFixed(1)}s
              </p>
              <p className="text-xs text-slate-500">Avg Response Time</p>
            </div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-amber-500">
              <Activity size={20} className="text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">
                {stats.reports_this_week.toLocaleString()}
              </p>
              <p className="text-xs text-slate-500">Reports This Week</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {quickActions.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className="card p-5 hover:shadow-md transition-shadow group flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className={`p-2.5 rounded-lg ${action.color}`}>
                <action.icon size={20} className="text-white" />
              </div>
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                {action.label}
              </span>
            </div>
            <ArrowRight
              size={16}
              className="text-slate-400 group-hover:translate-x-1 transition-transform"
            />
          </Link>
        ))}
      </div>

      {/* Recent Reports */}
      <div className="card">
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="section-heading flex items-center gap-2">
            <FileText size={18} />
            Recent Reports
          </h2>
          <Link href="/history" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            View all
          </Link>
        </div>
        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading...</div>
        ) : reports.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <FileText size={32} className="mx-auto mb-2 opacity-40" />
            <p>No reports yet. Generate your first report!</p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-200 dark:divide-slate-700">
            {reports.map((report) => (
              <li key={report.id}>
                <Link
                  href={`/review/${report.id}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                      {report.report_type} — {report.body_region}
                    </p>
                    <p className="text-xs text-slate-500 truncate">
                      {report.input_text.slice(0, 80)}...
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-4 shrink-0">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        report.status === 'final'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                          : report.status === 'rejected'
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                            : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
                      }`}
                    >
                      {report.status}
                    </span>
                    <span className="text-xs text-slate-400">
                      {new Date(report.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
