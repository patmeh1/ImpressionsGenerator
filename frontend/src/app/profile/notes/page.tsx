'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { getNotes, deleteNote, uploadNoteText } from '@/lib/api';
import type { Note } from '@/lib/types';
import FileUploader from '@/components/FileUploader';
import NotesList from '@/components/NotesList';
import { FileText, ClipboardPaste, Loader2 } from 'lucide-react';

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [pasteText, setPasteText] = useState('');
  const [pasteName, setPasteName] = useState('');
  const [pasting, setPasting] = useState(false);
  const pageSize = 10;

  // Using a placeholder doctor ID; in production this comes from auth context
  const doctorId = 'current-doctor';

  const loadNotes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getNotes(doctorId, page, pageSize);
      setNotes(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  const handleDelete = async (noteId: string) => {
    try {
      await deleteNote(doctorId, noteId);
      loadNotes();
    } catch (err) {
      console.error(err);
    }
  };

  const handlePasteSubmit = async () => {
    if (!pasteText.trim()) return;
    setPasting(true);
    try {
      await uploadNoteText(doctorId, pasteText, pasteName || 'pasted-note.txt');
      setPasteText('');
      setPasteName('');
      loadNotes();
    } catch (err) {
      console.error(err);
    } finally {
      setPasting(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
        <FileText size={24} className="text-primary-500" />
        My Notes
      </h1>

      {/* File Upload */}
      <div className="card p-5">
        <h2 className="section-heading mb-3">Upload File</h2>
        <FileUploader doctorId={doctorId} onUploadComplete={loadNotes} />
      </div>

      {/* Paste Text */}
      <div className="card p-5">
        <h2 className="section-heading mb-3 flex items-center gap-2">
          <ClipboardPaste size={18} />
          Paste Text
        </h2>
        <div className="space-y-3">
          <input
            type="text"
            value={pasteName}
            onChange={(e) => setPasteName(e.target.value)}
            placeholder="Note name (optional)"
            className="input-field"
          />
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            rows={6}
            placeholder="Paste note content here..."
            className="input-field resize-y font-mono text-sm"
          />
          <button
            onClick={handlePasteSubmit}
            disabled={!pasteText.trim() || pasting}
            className="btn-primary flex items-center gap-2"
          >
            {pasting ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Saving...
              </>
            ) : (
              'Save Note'
            )}
          </button>
        </div>
      </div>

      {/* Notes List */}
      <div className="card p-5">
        <h2 className="section-heading mb-3">Uploaded Notes</h2>
        {loading ? (
          <div className="text-center py-8 text-slate-500">
            <Loader2 size={24} className="animate-spin mx-auto" />
          </div>
        ) : (
          <NotesList
            doctorId={doctorId}
            notes={notes}
            onDelete={handleDelete}
            totalPages={totalPages}
            currentPage={page}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  );
}
