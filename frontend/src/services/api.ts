import axios from 'axios';
import type {
  EmailListResponse,
  EmailDetailResponse,
  FollowupRequest,
  FollowupResponse,
  UserInfo,
  EmailFilter,
  VendorCacheStatus
} from '../types/email';
import type { DashboardStats } from '../types/dashboard';

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

  // Get dashboard statistics
  async getDashboardStats(startDate?: string, endDate?: string): Promise<DashboardStats> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const { data } = await api.get<DashboardStats>('/api/dashboard/stats', { params });
    return data;
  },

  // Get pending verification emails
  async getPendingVerificationEmails(): Promise<EmailListResponse> {
    const { data } = await api.get<EmailListResponse>('/api/emails', {
      params: { filter: 'pending_verification' }
    });
    return data;
  },

  // Approve and process flagged email
  async approveAndProcessEmail(messageId: string): Promise<any> {
    const { data } = await api.post(`/api/emails/${messageId}/approve-and-process`);
    return data;
  },

  // Reject flagged email
  async rejectEmail(messageId: string): Promise<any> {
    const { data } = await api.post(`/api/emails/${messageId}/reject`);
    return data;
  },

  // Get vendor cache status
  async getVendorCacheStatus(): Promise<VendorCacheStatus> {
    const { data } = await api.get<VendorCacheStatus>('/api/emails/vendors/cache-status');
    return data;
  },

  // Refresh vendor cache
  async refreshVendorCache(): Promise<any> {
    const { data } = await api.post('/api/emails/vendors/refresh-cache');
    return data;
  },

  // Get raw email content (body and attachments)
  async getRawEmailContent(messageId: string): Promise<any> {
    const { data } = await api.get(`/api/emails/${messageId}/raw`);
    return data;
  },
};

export default api;
