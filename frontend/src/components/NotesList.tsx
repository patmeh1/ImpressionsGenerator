'use client';

import React, { useState } from 'react';
import type { Note } from '@/lib/types';
import { FileText, FileType, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';

interface NotesListProps {
  doctorId: string;
  notes: Note[];
  onDelete: (noteId: string) => void;
  totalPages?: number;
  currentPage?: number;
  onPageChange?: (page: number) => void;
}

function noteIcon(sourceType: string) {
  switch (sourceType) {
    case 'upload':
      return <FileType size={18} className="text-blue-500" />;
    case 'paste':
      return <FileText size={18} className="text-slate-500" />;
    default:
      return <FileText size={18} className="text-slate-500" />;
  }
}

export default function NotesList({
  notes,
  onDelete,
  totalPages = 1,
  currentPage = 1,
  onPageChange,
}: NotesListProps) {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleDelete = (noteId: string) => {
    if (confirmDeleteId === noteId) {
      onDelete(noteId);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(noteId);
      setTimeout(() => setConfirmDeleteId(null), 3000);
    }
  };

  if (notes.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500 dark:text-slate-400">
        <FileText size={40} className="mx-auto mb-3 opacity-40" />
        <p className="text-sm">No notes uploaded yet</p>
      </div>
    );
  }

  return (
    <div>
      <ul className="divide-y divide-slate-200 dark:divide-slate-700">
        {notes.map((note) => (
          <li key={note.id} className="py-3 flex items-start gap-3 group">
            <div className="mt-0.5">{noteIcon(note.source_type)}</div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                {note.file_name || 'Pasted note'}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                {note.content.slice(0, 200)}
                {note.content.length > 200 ? '...' : ''}
              </p>
              <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                <span>{note.source_type}</span>
                <span>{new Date(note.created_at).toLocaleDateString()}</span>
              </div>
            </div>
            <button
              onClick={() => handleDelete(note.id)}
              className={`p-1.5 rounded-md transition-colors ${
                confirmDeleteId === note.id
                  ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                  : 'text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100'
              }`}
              title={confirmDeleteId === note.id ? 'Click again to confirm' : 'Delete'}
            >
              <Trash2 size={14} />
            </button>
          </li>
        ))}
      </ul>

      {totalPages > 1 && onPageChange && (
        <div className="flex items-center justify-center gap-2 mt-4 pt-3 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="btn-secondary p-1.5 disabled:opacity-30"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-sm text-slate-600 dark:text-slate-400">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="btn-secondary p-1.5 disabled:opacity-30"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
