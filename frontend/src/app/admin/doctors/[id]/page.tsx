'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import {
  getDoctor,
  updateDoctor,
  getNotes,
  deleteNote,
  getStyleProfile,
  getDoctorStats,
} from '@/lib/api';
import type { Doctor, Note, StyleProfile as StyleProfileType, UsageStatsData } from '@/lib/types';
import NotesList from '@/components/NotesList';
import StylePreview from '@/components/StylePreview';
import UsageStats from '@/components/UsageStats';
import { User, Save, Loader2 } from 'lucide-react';

export default function DoctorDetailPage() {
  const params = useParams();
  const doctorId = params.id as string;

  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [styleProfile, setStyleProfile] = useState<StyleProfileType | null>(null);
  const [stats, setStats] = useState<UsageStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Editable fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [doc, notesRes, sp, st] = await Promise.all([
          getDoctor(doctorId),
          getNotes(doctorId, 1, 10),
          getStyleProfile(doctorId).catch(() => null),
          getDoctorStats(doctorId).catch(() => null),
        ]);
        setDoctor(doc);
        setName(doc.name);
        setEmail(doc.email);
        setSpecialty(doc.specialty);
        setIsAdmin(doc.is_admin);
        setNotes(notesRes.items);
        setStyleProfile(sp);
        setStats(st);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [doctorId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateDoctor(doctorId, { name, email, specialty, is_admin: isAdmin });
      setDoctor(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    try {
      await deleteNote(doctorId, noteId);
      const res = await getNotes(doctorId, 1, 10);
      setNotes(res.items);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute requiredRole="Admin">
        <div className="flex items-center justify-center py-20">
          <Loader2 size={32} className="animate-spin text-primary-500" />
        </div>
      </ProtectedRoute>
    );
  }

  if (!doctor) {
    return (
      <ProtectedRoute requiredRole="Admin">
        <div className="text-center py-20 text-slate-500">Doctor not found.</div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute requiredRole="Admin">
    <div className="max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
        <User size={24} className="text-primary-500" />
        {doctor.name}
      </h1>

      {/* Profile Edit */}
      <div className="card p-5">
        <h2 className="section-heading mb-4">Profile</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Specialty</label>
            <input
              type="text"
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
              className="input-field"
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
                className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              Admin role
            </label>
          </div>
        </div>
        <div className="mt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary flex items-center gap-2"
          >
            {saving ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Save size={14} />
            )}
            Save Profile
          </button>
        </div>
      </div>

      {/* Usage Stats */}
      {stats && <UsageStats stats={stats} />}

      {/* Style Profile */}
      {styleProfile && <StylePreview styleProfile={styleProfile} />}

      {/* Notes */}
      <div className="card p-5">
        <h2 className="section-heading mb-3">Notes</h2>
        <NotesList doctorId={doctorId} notes={notes} onDelete={handleDeleteNote} />
      </div>
    </div>
    </ProtectedRoute>
  );
}
