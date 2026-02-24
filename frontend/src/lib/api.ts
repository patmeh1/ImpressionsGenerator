import { getAccessToken } from '@/lib/auth';
import type {
  Doctor,
  Note,
  Report,
  StyleProfile,
  GenerateRequest,
  GenerateResponse,
  ReportVersion,
  UsageStatsData,
  PaginatedResponse,
  Feedback,
  FeedbackScores,
} from '@/lib/types';

const BASE_URL = '/api';

async function authHeaders(): Promise<HeadersInit> {
  const token = await getAccessToken();
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

// Doctors
export async function getDoctors(): Promise<Doctor[]> {
  return request<Doctor[]>('/doctors');
}

export async function getDoctor(id: string): Promise<Doctor> {
  return request<Doctor>(`/doctors/${id}`);
}

export async function createDoctor(
  data: Omit<Doctor, 'id' | 'created_at' | 'updated_at'>
): Promise<Doctor> {
  return request<Doctor>('/doctors', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateDoctor(
  id: string,
  data: Partial<Doctor>
): Promise<Doctor> {
  return request<Doctor>(`/doctors/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteDoctor(id: string): Promise<void> {
  await request<void>(`/doctors/${id}`, { method: 'DELETE' });
}

// Notes
export async function getNotes(
  doctorId: string,
  page = 1,
  pageSize = 20
): Promise<PaginatedResponse<Note>> {
  return request<PaginatedResponse<Note>>(
    `/doctors/${doctorId}/notes?page=${page}&page_size=${pageSize}`
  );
}

export async function uploadNote(
  doctorId: string,
  file: File
): Promise<Note> {
  const token = await getAccessToken();
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${BASE_URL}/doctors/${doctorId}/notes`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function uploadNoteText(
  doctorId: string,
  content: string
): Promise<Note> {
  const token = await getAccessToken();
  const formData = new FormData();
  formData.append('content', content);

  const res = await fetch(`${BASE_URL}/doctors/${doctorId}/notes`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error(`Failed to save note: ${res.status}`);
  return res.json();
}

export async function deleteNote(
  doctorId: string,
  noteId: string
): Promise<void> {
  await request<void>(`/doctors/${doctorId}/notes/${noteId}`, {
    method: 'DELETE',
  });
}

// Report Generation
export async function generateReport(
  data: GenerateRequest
): Promise<GenerateResponse> {
  return request<GenerateResponse>('/generate', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Reports
export async function getReports(
  doctorId?: string,
  page = 1,
  pageSize = 20,
  filters?: { status?: string; report_type?: string; search?: string }
): Promise<PaginatedResponse<Report>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (doctorId) params.set('doctor_id', doctorId);
  if (filters?.status) params.set('status', filters.status);
  if (filters?.report_type) params.set('report_type', filters.report_type);
  if (filters?.search) params.set('search', filters.search);
  return request<PaginatedResponse<Report>>(`/reports?${params}`);
}

export async function getReport(id: string): Promise<Report> {
  return request<Report>(`/reports/${id}`);
}

export async function updateReport(
  id: string,
  data: Partial<Report>
): Promise<Report> {
  return request<Report>(`/reports/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function approveReport(id: string): Promise<Report> {
  return request<Report>(`/reports/${id}/approve`, {
    method: 'POST',
  });
}

export async function rejectReport(id: string): Promise<Report> {
  return request<Report>(`/reports/${id}/reject`, {
    method: 'POST',
  });
}

export async function getReportVersions(
  reportId: string
): Promise<ReportVersion[]> {
  return request<ReportVersion[]>(`/reports/${reportId}/versions`);
}

// Style Profile
export async function getStyleProfile(
  doctorId: string
): Promise<StyleProfile> {
  return request<StyleProfile>(`/doctors/${doctorId}/style-profile`);
}

// Admin
export async function getAdminStats(): Promise<UsageStatsData> {
  return request<UsageStatsData>('/admin/stats');
}

export async function getDoctorStats(
  doctorId: string
): Promise<UsageStatsData> {
  return request<UsageStatsData>(`/admin/doctors/${doctorId}/stats`);
}

export async function getDoctorFeedbackScores(
  doctorId: string
): Promise<FeedbackScores> {
  return request<FeedbackScores>(`/admin/doctors/${doctorId}/feedback-scores`);
}

// Feedback
export async function submitFeedback(
  reportId: string,
  data: { rating: number; feedback_text?: string }
): Promise<Feedback> {
  return request<Feedback>(`/reports/${reportId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getReportFeedback(
  reportId: string
): Promise<Feedback[]> {
  return request<Feedback[]>(`/reports/${reportId}/feedback`);
}
