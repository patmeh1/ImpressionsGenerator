'use client';

import React from 'react';
import type { UsageStatsData } from '@/lib/types';
import { BarChart3, Clock, FileCheck, Activity } from 'lucide-react';

interface UsageStatsProps {
  stats: UsageStatsData;
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="card p-4 flex items-center gap-3">
      <div className={`p-2.5 rounded-lg ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{value}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      </div>
    </div>
  );
}

export default function UsageStats({ stats }: UsageStatsProps) {
  const maxCount = Math.max(...stats.daily_usage.map((d) => d.count), 1);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          icon={FileCheck}
          label="Total Generations"
          value={stats.total_generations.toLocaleString()}
          color="bg-primary-600"
        />
        <StatCard
          icon={Clock}
          label="Avg Response Time"
          value={`${(stats.avg_response_time_ms / 1000).toFixed(1)}s`}
          color="bg-teal-600"
        />
        <StatCard
          icon={Activity}
          label="Reports This Week"
          value={stats.reports_this_week.toLocaleString()}
          color="bg-amber-500"
        />
      </div>

      <div className="card p-5">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
          <BarChart3 size={16} />
          Daily Usage (Last 7 Days)
        </h4>
        <div className="flex items-end gap-2 h-32">
          {stats.daily_usage.map((day, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-[10px] text-slate-500">{day.count}</span>
              <div
                className="w-full bg-primary-500 dark:bg-primary-400 rounded-t-sm transition-all"
                style={{
                  height: `${(day.count / maxCount) * 100}%`,
                  minHeight: day.count > 0 ? '4px' : '0px',
                }}
              />
              <span className="text-[10px] text-slate-400">
                {new Date(day.date).toLocaleDateString(undefined, { weekday: 'short' })}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
