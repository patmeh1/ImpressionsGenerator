'use client';

import React, { useState, useRef, useEffect } from 'react';
import type { Doctor } from '@/lib/types';
import { Search, ChevronDown, User } from 'lucide-react';

interface DoctorSelectorProps {
  doctors: Doctor[];
  selectedId: string | null;
  onChange: (doctorId: string) => void;
}

export default function DoctorSelector({
  doctors,
  selectedId,
  onChange,
}: DoctorSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  const selected = doctors.find((d) => d.id === selectedId);
  const filtered = doctors.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.specialty.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="input-field flex items-center justify-between gap-2 text-left"
      >
        <div className="flex items-center gap-2 truncate">
          <User size={16} className="text-slate-400 shrink-0" />
          {selected ? (
            <span>
              {selected.name}
              <span className="text-slate-400 ml-1 text-xs">({selected.specialty})</span>
            </span>
          ) : (
            <span className="text-slate-400">Select a doctor...</span>
          )}
        </div>
        <ChevronDown size={16} className="text-slate-400 shrink-0" />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg max-h-64 overflow-hidden">
          <div className="p-2 border-b border-slate-200 dark:border-slate-700">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search doctors..."
                className="input-field pl-8 py-1.5 text-sm"
                autoFocus
              />
            </div>
          </div>
          <ul className="overflow-y-auto max-h-48">
            {filtered.length === 0 ? (
              <li className="px-3 py-2 text-sm text-slate-500">No doctors found</li>
            ) : (
              filtered.map((doctor) => (
                <li key={doctor.id}>
                  <button
                    onClick={() => {
                      onChange(doctor.id);
                      setOpen(false);
                      setSearch('');
                    }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors ${
                      doctor.id === selectedId
                        ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                        : 'text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="font-medium">{doctor.name}</div>
                    <div className="text-xs text-slate-400">{doctor.specialty}</div>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
