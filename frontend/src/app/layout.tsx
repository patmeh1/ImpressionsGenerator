'use client';

import React from 'react';
import { MsalProvider } from '@azure/msal-react';
import { msalInstance } from '@/lib/auth';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import Footer from '@/components/layout/Footer';
import '@/styles/globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>Impressions Generator</title>
        <meta name="description" content="AI-powered radiology report impressions generator" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased">
        <MsalProvider instance={msalInstance}>
          <div className="flex flex-col min-h-screen">
            <Header />
            <div className="flex flex-1">
              <Sidebar />
              <main className="flex-1 p-4 lg:p-6 overflow-y-auto">
                {children}
              </main>
            </div>
            <Footer />
          </div>
        </MsalProvider>
      </body>
    </html>
  );
}
