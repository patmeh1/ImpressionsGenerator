/**
 * Application Insights telemetry for the Impressions Generator frontend.
 *
 * Tracks page views, custom events, and exceptions in Azure Monitor.
 */

import { ApplicationInsights } from '@microsoft/applicationinsights-web';

const connectionString =
  process.env.NEXT_PUBLIC_APPINSIGHTS_CONNECTION_STRING || '';

let appInsights: ApplicationInsights | null = null;

/**
 * Initialize Application Insights.
 * Call once at app startup (e.g. in _app.tsx or a root layout).
 * No-ops when the connection string is not configured.
 */
export function initTelemetry(): void {
  if (!connectionString || appInsights) return;

  appInsights = new ApplicationInsights({
    config: {
      connectionString,
      enableAutoRouteTracking: true,
      disableFetchTracking: false,
      enableCorsCorrelation: true,
      enableRequestHeaderTracking: true,
      enableResponseHeaderTracking: true,
    },
  });

  appInsights.loadAppInsights();
  appInsights.trackPageView();
}

/** Track a custom event (e.g. "ReportGenerated"). */
export function trackEvent(
  name: string,
  properties?: Record<string, string>,
): void {
  appInsights?.trackEvent({ name }, properties);
}

/** Track an exception. */
export function trackException(error: Error): void {
  appInsights?.trackException({ exception: error });
}

/** Track a page view. */
export function trackPageView(name?: string): void {
  appInsights?.trackPageView({ name });
}

/** Track a custom metric (e.g. response-time). */
export function trackMetric(
  name: string,
  average: number,
  properties?: Record<string, string>,
): void {
  appInsights?.trackMetric({ name, average }, properties);
}

export { appInsights };
