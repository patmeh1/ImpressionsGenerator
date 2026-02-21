'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getDoctors, getAdminStats } from '@/lib/api';
import type { Doctor, UsageStatsData } from '@/lib/types';
import UsageStats from '@/components/UsageStats';
import {
  ShieldCheck,
  Users,
  Search,
  CheckCircle,
  AlertTriangle,
  Server,
} from 'lucide-react';

export default function AdminPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [stats, setStats] = useState<UsageStatsData | null>(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [docs, s] = await Promise.all([getDoctors(), getAdminStats()]);
        setDoctors(docs);
        setStats(s);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = doctors.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
        <ShieldCheck size={24} className="text-primary-500" />
        Admin Dashboard
      </h1>

      {/* System Health */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
            <CheckCircle size={20} className="text-green-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">API Service</p>
            <p className="text-xs text-green-600">Healthy</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
            <Server size={20} className="text-green-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">AI Model</p>
            <p className="text-xs text-green-600">Online</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-yellow-100 dark:bg-yellow-900/30">
            <AlertTriangle size={20} className="text-yellow-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">Storage</p>
            <p className="text-xs text-yellow-600">72% used</p>
          </div>
        </div>
      </div>

      {/* Usage Stats */}
      {stats && <UsageStats stats={stats} />}

      {/* Doctors Table */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="section-heading flex items-center gap-2">
            <Users size={18} />
            Doctors ({doctors.length})
          </h2>
          <div className="relative w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search doctors..."
              className="input-field pl-8 py-1.5 text-sm"
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-400">Name</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-400">Email</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-400">Specialty</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-400">Role</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 dark:text-slate-400">Joined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500">Loading...</td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500">No doctors found</td>
                </tr>
              ) : (
                filtered.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/doctors/${doc.id}`}
                        className="font-medium text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        {doc.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{doc.email}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{doc.specialty}</td>
                    <td className="px-4 py-3">
                      {doc.is_admin ? (
                        <span className="px-2 py-0.5 bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 rounded-full text-xs font-medium">
                          Admin
                        </span>
                      ) : (
                        <span className="text-slate-500 text-xs">User</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
