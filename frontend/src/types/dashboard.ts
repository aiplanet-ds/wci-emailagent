export interface DashboardStats {
  total_emails: number;
  processed_count: number;
  unprocessed_count: number;
  needs_followup_count: number;
  price_change_count: number;
  non_price_change_count: number;
  epicor_sync_success: number;
  epicor_sync_failed: number;
  epicor_sync_pending: number;
  processing_rate: number;
  unprocessed_percentage: number;
  followup_percentage: number;
  epicor_success_rate: number;
  emails_with_missing_fields: number;
  recent_activity: RecentActivity[];
}

export interface RecentActivity {
  message_id: string;
  subject: string;
  processed_at: string;
  processed_by: string | null;
  action: string;
}

export type DateRangeOption = 'today' | 'last7days' | 'last30days' | 'all';

export interface DateRange {
  start_date?: string;
  end_date?: string;
}
