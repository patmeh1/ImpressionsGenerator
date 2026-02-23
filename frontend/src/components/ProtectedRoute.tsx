'use client';

import React from 'react';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
}

export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const isAuthenticated = useIsAuthenticated();
  const { accounts, inProgress } = useMsal();
  const router = useRouter();

  React.useEffect(() => {
    if (inProgress === 'none' && !isAuthenticated) {
      router.replace('/');
    }
  }, [isAuthenticated, inProgress, router]);

  if (inProgress !== 'none') {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="animate-spin text-primary-500" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requiredRole) {
    const claims = accounts[0]?.idTokenClaims as Record<string, unknown> | undefined;
    const roles = (claims?.roles as string[]) || [];
    if (!roles.includes(requiredRole)) {
      return (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <p className="text-lg font-semibold text-red-600">Access Denied</p>
            <p className="text-sm text-slate-500 mt-1">
              You do not have the required &apos;{requiredRole}&apos; role to access this page.
            </p>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
}
