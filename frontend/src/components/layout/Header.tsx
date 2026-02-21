'use client';

import React from 'react';
import { useMsal } from '@azure/msal-react';
import { Moon, Sun, LogOut, Stethoscope } from 'lucide-react';

export default function Header() {
  const { instance, accounts } = useMsal();
  const account = accounts[0];

  const [dark, setDark] = React.useState(false);

  React.useEffect(() => {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = saved === 'dark' || (!saved && prefersDark);
    setDark(isDark);
    document.documentElement.classList.toggle('dark', isDark);
  }, []);

  const toggleDark = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };

  const handleLogout = () => {
    instance.logoutRedirect();
  };

  return (
    <header className="sticky top-0 z-30 h-14 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between px-4 lg:px-6">
      <div className="flex items-center gap-2.5">
        <Stethoscope size={24} className="text-teal-600" />
        <span className="text-lg font-bold text-slate-800 dark:text-slate-100 hidden sm:inline">
          Impressions Generator
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={toggleDark}
          className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          title="Toggle dark mode"
        >
          {dark ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {account && (
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-sm font-semibold">
              {(account.name || account.username || '?').charAt(0).toUpperCase()}
            </div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300 hidden md:inline">
              {account.name || account.username}
            </span>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
