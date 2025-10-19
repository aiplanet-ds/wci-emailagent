import axios from 'axios';
import type {
  EmailListResponse,
  EmailDetailResponse,
  FollowupRequest,
  FollowupResponse,
  UserInfo,
  EmailFilter
} from '../types/email';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with credentials
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,  // Important for session cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// API Client
export const emailApi = {
  // Get current user info
  async getCurrentUser(): Promise<UserInfo> {
    const { data } = await api.get<UserInfo>('/api/user');
    return data;
  },

  // Get list of emails
  async getEmails(filter?: EmailFilter, search?: string): Promise<EmailListResponse> {
    const params = new URLSearchParams();
    if (filter && filter !== 'all') params.append('filter', filter);
    if (search) params.append('search', search);

    const { data } = await api.get<EmailListResponse>('/api/emails', { params });
    return data;
  },

  // Get email detail
  async getEmailDetail(messageId: string): Promise<EmailDetailResponse> {
    const { data } = await api.get<EmailDetailResponse>(`/api/emails/${messageId}`);
    return data;
  },

  // Mark email as processed/unprocessed
  async updateEmailProcessed(messageId: string, processed: boolean, force: boolean = false): Promise<any> {
    const params = new URLSearchParams();
    if (force) params.append('force', 'true');

    const { data } = await api.patch(
      `/api/emails/${messageId}${params.toString() ? `?${params.toString()}` : ''}`,
      { processed }
    );
    return data;
  },

  // Generate follow-up email
  async generateFollowup(messageId: string, request: FollowupRequest): Promise<FollowupResponse> {
    const { data } = await api.post<FollowupResponse>(`/api/emails/${messageId}/followup`, request);
    return data;
  },
};

export default api;
