export interface Doctor {
  id: string;
  name: string;
  specialty: string;
  department: string;
  created_at: string;
  updated_at: string | null;
}

export interface Note {
  id: string;
  doctor_id: string;
  content: string;
  source_type: 'upload' | 'paste';
  file_name: string | null;
  created_at: string;
}

export interface Report {
  id: string;
  doctor_id: string;
  input_text: string;
  report_type: string;
  body_region: string;
  findings: string;
  impressions: string;
  recommendations: string;
  status: 'draft' | 'edited' | 'final' | 'approved' | 'rejected';
  versions: ReportVersion[];
  created_at: string;
  updated_at: string;
}

export interface StyleProfile {
  doctor_id: string;
  abbreviations: string[];
  common_phrases: string[];
  section_order: string[];
  tone: string;
  avg_length: number;
  updated_at: string;
}

export interface GenerateRequest {
  doctor_id: string;
  input_text: string;
  report_type: string;
  body_region: string;
}

export interface GenerateResponse {
  report_id: string;
  findings: string;
  impressions: string;
  recommendations: string;
  grounding_score: number;
}

export interface ReportVersion {
  version: number;
  findings: string;
  impressions: string;
  recommendations: string;
  status: 'draft' | 'edited' | 'final' | 'rejected';
  edited_at: string;
  edited_by: string;
}

export interface UsageStatsData {
  total_generations: number;
  avg_response_time_ms: number;
  reports_this_week: number;
  daily_usage: { date: string; count: number }[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Feedback {
  id: string;
  report_id: string;
  doctor_id: string;
  rating: number;
  feedback_text: string;
  created_at: string;
}

export interface FeedbackScores {
  doctor_id: string;
  avg_rating: number;
  total_feedback: number;
}
