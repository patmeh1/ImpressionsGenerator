'use client';

import React from 'react';
import { useIsAuthenticated } from '@azure/msal-react';
import { loginPopup } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import { Stethoscope, ShieldCheck, Sparkles, Users, LogIn } from 'lucide-react';

const features = [
  {
    icon: Sparkles,
    title: 'Style-Matched Reports',
    description:
      'AI learns each radiologist\'s unique dictation style, abbreviations, and phrasing to generate reports that sound like you wrote them.',
  },
  {
    icon: ShieldCheck,
    title: 'Grounding Safety',
    description:
      'Every generated impression is grounded in the original dictation. Nothing is hallucinated — only findings you dictated appear in the report.',
  },
  {
    icon: Users,
    title: 'Multi-Doctor Support',
    description:
      'Each physician has their own style profile built from their past notes, ensuring personalized output for every member of the practice.',
  },
];

export default function LandingPage() {
  const isAuthenticated = useIsAuthenticated();
  const router = useRouter();

  React.useEffect(() => {
    if (isAuthenticated) router.push('/dashboard');
  }, [isAuthenticated, router]);

  const handleLogin = async () => {
    const account = await loginPopup();
    if (account) router.push('/dashboard');
  };

  return (
    <div className="max-w-5xl mx-auto py-12 px-4">
      {/* Hero */}
      <div className="text-center mb-16">
        <div className="flex justify-center mb-4">
          <div className="p-4 bg-teal-100 dark:bg-teal-900/40 rounded-2xl">
            <Stethoscope size={48} className="text-teal-600" />
          </div>
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 dark:text-slate-50 mb-4">
          Impressions Generator
        </h1>
        <p className="text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto mb-8">
          AI-powered radiology report generation that matches your personal dictation style.
          Paste your findings, get polished impressions in seconds.
        </p>
        <button
          onClick={handleLogin}
          className="btn-primary text-lg px-8 py-3 inline-flex items-center gap-2"
        >
          <LogIn size={20} />
          Sign In with Microsoft
        </button>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((feature) => (
          <div
            key={feature.title}
            className="card p-6 text-center hover:shadow-md transition-shadow"
          >
            <div className="inline-flex p-3 bg-primary-50 dark:bg-primary-900/30 rounded-xl mb-4">
              <feature.icon size={28} className="text-primary-600 dark:text-primary-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-2">
              {feature.title}
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              {feature.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
