import React from 'react';

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-700 py-4 px-6 text-center text-xs text-slate-500 dark:text-slate-400">
      &copy; {new Date().getFullYear()} Impressions Generator &mdash; v1.0.0
    </footer>
  );
}
