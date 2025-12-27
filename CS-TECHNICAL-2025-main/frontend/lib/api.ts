import axios, { AxiosInstance, AxiosError } from 'axios';

// ==========================================
// Types
// ==========================================

export interface AuthResponse {
  access_token: string;
  email: string;
}

export interface ResumeUploadResponse {
  resume_id: string;
}

export interface ParsedResume {
  name?: string;
  email?: string;
  phone?: string;
  region?: string;
  roles?: string[];
  summary?: string;
  experience?: Array<{
    title?: string;
    company?: string;
    duration?: string;
    description?: string;
  }>;
  education?: Array<{
    degree?: string;
    institution?: string;
    year?: string;
  }>;
  skills?: {
    hard?: string[];
    soft?: string[];
  };
  certifications?: string[];
  languages?: string[];
  raw_text?: string;
}

export interface ReviewOverall {
  score: number; // 0-100
  label: string; // Excellent | Good | Fair | Needs Improvement
  out_of: number; // 100
}

export interface ReviewBreakdown {
  skills_coverage: number; // 0-100
  structure_formatting: number; // 0-100
  clarity_impact: number; // 0-100
  regional_relevance: number; // 0-100
}

export interface ReviewResponse {
  overall: ReviewOverall;
  breakdown: ReviewBreakdown;
  strengths: string[];
  areas_for_improvement: string[];
  notes?: string;
}

export interface InterviewQuestion {
  id: string;
  text: string;
  category?: string;
}

export interface InterviewStartResponse {
  session_id: string;
  first: InterviewQuestion | null;
}

export interface InterviewInsights {
  overall_score?: number;
  strengths?: string[];
  improvements?: string[];
  communication?: string;
  technical_depth?: string;
  face_summary?: FaceSummary;
}

export interface FaceSummary {
  avg_attention?: number;
  avg_faces?: number;
  present_ratio?: number;
  smile_ratio?: number;
  total_frames?: number;
  nudges?: number;
}

export interface Job {
  title: string;
  company: string;
  location?: string;
  url?: string;
  description?: string;
  posted?: string;
  salary?: string;
  tags?: string[];
  score?: number;
  source?: string;
  snippet?: string;
  remote?: boolean;
  region_match?: boolean;
  explanation?: {
    summary?: string;
    gaps?: string[];
    fairness?: string;
    notes?: string[];
    matched_skills?: string[];
    title_tokens?: string[];
  };
}

export interface MatchResponse {
  region?: string;
  skills_used: string[];
  jobs: Job[];
}

export interface FootprintResponse {
  github?: {
    username?: string;
    public_repos?: number;
    followers?: number;
    contributions?: number;
    top_languages?: string[];
    popular_repos?: Array<{
      name?: string;
      stars?: number;
      language?: string;
    }>;
  };
  stackoverflow?: {
    user_id?: string;
    reputation?: number;
    badges?: {
      gold?: number;
      silver?: number;
      bronze?: number;
    };
    top_tags?: string[];
  };
  summary?: string;
}

// Career report is currently driven by the LLM "analysis" schema.
// Keep it loose enough to accommodate evolution but typed for UI usage.
export interface CareerReportResponse {
  structured?: {
    candidate?: { name?: string; email?: string; phone?: string };
    skills_hard?: string[];
    skills_soft?: string[];
    roles?: string[];
    location?: string;
    region?: string;
  };
  review?: {
    ats_score?: number;
    summary?: string;
    strengths?: string[];
    weaknesses?: string[];
    gaps?: string[];
    suggestions?: string[];
  };
  career_report?: {
    summary?: string;
    six_month_focus?: {
      headline?: string;
      themes?: string[];
      target_roles?: string[];
    };
    target_roles?: Array<{
      role: string;
      fit_score: number;
      why: string;
    }>;
    skills_to_double_down?: string[];
    skills_to_learn?: string[];
    certifications?: string[];
    learning_plan?: Array<{
      month: number;
      focus: string;
      actions: string[];
    }>;
    market_insights?: {
      target_regions?: string[];
      hot_skills?: string[];
      notes?: string;
    };
    interview_tips?: string[];
    narrative_summary?: string;
  };
  raw_response?: string;
}

export interface ApiError {
  error: string;
  message?: string;
}

// ==========================================
// API Configuration
// ==========================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    // Initialize token from localStorage if present (browser-only)
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }

    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 seconds
    });

    // Request interceptor to add token
    this.client.interceptors.request.use(
      (config) => {
        if (!config.headers) config.headers = {} as any;
        if (this.token) {
          (config.headers as any).Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          this.clearToken();
          if (typeof window !== 'undefined') {
            localStorage.removeItem('token');
            localStorage.removeItem('user_email');
          }
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('user_email');
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  // ==========================================
  // Auth Endpoints
  // ==========================================

  async register(email: string, password: string): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/register', {
      email,
      password,
    });
    this.setToken(response.data.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('user_email', response.data.email || email);
    }
    return response.data;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/login', {
      email,
      password,
    });
    this.setToken(response.data.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('user_email', response.data.email || email);
    }
    return response.data;
  }

  logout() {
    this.clearToken();
  }

  // ==========================================
  // Resume Endpoints
  // ==========================================

  async uploadResume(file: File): Promise<ResumeUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Ensure token header is present for multipart uploads
    const extraHeaders: Record<string, string> = {};
    const t = this.getToken();
    if (t) extraHeaders.Authorization = `Bearer ${t}`;

    const response = await this.client.post<ResumeUploadResponse>(
      '/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
          ...extraHeaders,
        },
      }
    );
    return response.data;
  }

  async getResume(resumeId: string): Promise<ParsedResume> {
    const response = await this.client.get<ParsedResume>(`/resume/${resumeId}`);
    return response.data;
  }

  async deleteResume(resumeId: string): Promise<{ ok: boolean; deleted: string }> {
    const response = await this.client.delete<{ ok: boolean; deleted: string }>(
      `/resume/${resumeId}`
    );
    return response.data;
  }

  async reviewResume(resumeId: string): Promise<ReviewResponse> {
    const response = await this.client.post<ReviewResponse>(
      `/review/${resumeId}`
    );
    return response.data;
  }

  // ==========================================
  // Interview Endpoints
  // ==========================================

  async startInterview(
    resumeId: string,
    role?: string
  ): Promise<InterviewStartResponse> {
    const response = await this.client.post<InterviewStartResponse>(
      '/interview/ai/start',
      {
        resume_id: resumeId,
        role: role || 'Software Engineer',
      }
    );
    return response.data;
  }

  // Note: Real-time interview interactions happen via Socket.IO
  // These would be handled separately in a socket client

  // ==========================================
  // Job Matching Endpoints
  // ==========================================

  async matchJobs(
    resumeId: string,
    opts?: {
      region?: string; // e.g., 'MENA' | 'SSA' | 'Any'
      workMode?: 'remote' | 'onsite' | 'hybrid' | 'any';
      countries?: string[];
      skillsOverride?: string[];
    }
  ): Promise<MatchResponse> {
    const payload: Record<string, any> = {
      region: opts?.region,
      skills_override: opts?.skillsOverride,
    };
    if (opts?.workMode) {
      // Map 'hybrid' to 'any' for backend compatibility
      payload.work_mode = opts.workMode === 'hybrid' ? 'any' : opts.workMode;
    }
    if (opts?.countries && opts.countries.length) {
      payload.countries = opts.countries;
    }
    const response = await this.client.post<MatchResponse>(
      `/match/${resumeId}`,
      payload
    );
    return response.data;
  }

  async autoMatchJobs(resumeId: string): Promise<MatchResponse> {
    const response = await this.client.post<MatchResponse>(
      `/match/auto/${resumeId}`
    );
    return response.data;
  }

  // ==========================================
  // Footprint Endpoint
  // ==========================================

  async getFootprint(
    resumeId: string,
    githubUsername?: string,
    stackoverflowUserId?: string
  ): Promise<FootprintResponse> {
    const response = await this.client.post<FootprintResponse>(
      `/footprint/${resumeId}`,
      {
        github_username: githubUsername,
        stackoverflow_user_id: stackoverflowUserId,
      }
    );
    return response.data;
  }

  // ==========================================
  // Career Report Endpoint
  // ==========================================

  async getCareerReport(resumeId: string): Promise<CareerReportResponse> {
    // Career report LLM calls can be slower; allow longer timeout here.
    const response = await this.client.post<CareerReportResponse>(
      `/report/${resumeId}`,
      undefined,
      { timeout: 90000 }
    );
    return response.data;
  }

  // ==========================================
  // AI Aids (Resume Tailoring & Cover Letter)
  // ==========================================

  async refineResumeForJob(resumeId: string, job: Job): Promise<{
    summary_suggestion?: string;
    keywords_to_emphasize?: string[];
    experience_bullets?: string[];
    skills_to_add?: string[];
    notes?: string;
    raw_response?: string;
  }> {
    const response = await this.client.post('/ai/refine_resume_for_job', {
      resume_id: resumeId,
      job,
    });
    return response.data;
  }

  async generateCoverLetter(resumeId: string, job: Job): Promise<{
    cover_letter?: string;
    raw_response?: string;
  }> {
    const response = await this.client.post('/ai/cover_letter', {
      resume_id: resumeId,
      job,
    });
    return response.data;
  }

  // ==========================================
  // Debug Endpoint (development only)
  // ==========================================

  async debugScrape(resumeId: string): Promise<any> {
    const response = await this.client.get(`/debug/scrape/${resumeId}`);
    return response.data;
  }
}

// ==========================================
// Export singleton instance
// ==========================================

const api = new ApiClient();

export default api;

// ==========================================
// Helper functions for error handling
// ==========================================

export function isApiError(error: unknown): error is AxiosError<ApiError> {
  return axios.isAxiosError(error);
}

export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    // Map common backend error codes to friendlier messages
    const status = error.response?.status;
    if (status === 409) return 'An account with that email already exists.';
    if (status === 401) return 'Unauthorized — please sign in again.';
    return (
      error.response?.data?.error ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred'
    );
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
}

// ==========================================
// Token management helpers
// ==========================================

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

export function getStoredUserEmail(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('user_email');
}

export function isAuthenticated(): boolean {
  return !!getStoredToken();
}
