// TypeScript type definitions for Price-Change Email data

export interface EmailMetadata {
  subject: string;
  sender: string;
  date: string;
  message_id: string;
}

export interface SupplierInfo {
  supplier_id: string | null;
  supplier_name: string | null;
  contact_person: string | null;
  contact_email: string | null;
  contact_phone: string | null;
}

export interface PriceChangeSummary {
  change_type: string | null;
  effective_date: string | null;
  notification_date: string | null;
  reason: string | null;
  overall_impact: string | null;
}

export interface AffectedProduct {
  product_name: string | null;
  product_id: string | null;
  product_code: string | null;
  old_price: number | null;
  new_price: number | null;
  price_change_amount: number | null;
  price_change_percentage: number | null;
  currency: string | null;
  unit_of_measure: string | null;
}

export interface AdditionalDetails {
  terms_and_conditions: string | null;
  payment_terms: string | null;
  minimum_order_quantity: string | null;
  notes: string | null;
}

export interface EmailData {
  email_metadata: EmailMetadata;
  supplier_info: SupplierInfo;
  price_change_summary: PriceChangeSummary;
  affected_products: AffectedProduct[];
  additional_details: AdditionalDetails;
}

export interface MissingField {
  field: string;
  label: string;
  section: string;
  severity?: 'required' | 'recommended';
  product_index?: number;
}

export interface ValidationResult {
  is_valid: boolean;
  missing_fields: MissingField[];
  recommended_fields: MissingField[];
  all_missing_fields: MissingField[];
  needs_info: boolean;
  validation_errors: string[];
  is_price_change: boolean;
}

export interface VendorInfo {
  vendor_id: string;
  vendor_name: string;
}

export interface EmailState {
  message_id: string;
  processed: boolean;
  is_price_change: boolean;
  needs_info: boolean;
  selected_missing_fields: string[];
  followup_draft: string | null;
  last_updated: string | null;
  processed_at: string | null;
  processed_by: string | null;
  vendor_verified: boolean;
  verification_status: 'verified' | 'unverified' | 'manually_approved' | 'pending_review' | 'rejected';
  verification_method: 'exact_email' | 'domain_match' | 'manual_approval' | null;
  vendor_info: VendorInfo | null;
  manually_approved_by: string | null;
  manually_approved_at: string | null;
  flagged_reason: string | null;
}

export interface EpicorUpdateDetail {
  part_num: string;
  product: string;
  status: 'success' | 'failed' | 'skipped';
  old_price: number;
  new_price: number;
  message: string;
  effective_date?: string;
  supplier_id?: string;
  vendor_name?: string;
  list_code?: string;
}

export interface EpicorWorkflowSteps {
  step_a_complete: boolean;  // Supplier Verification
  step_b_complete: boolean;  // Price List Creation
  step_b_path: 'created_new' | 'updated_existing' | null;
  step_c_complete: boolean;  // Effective Date Management
  step_d_complete: boolean;  // Price Update
}

export interface EpicorStatus {
  total: number;
  successful: number;
  failed: number;
  skipped: number;
  details: EpicorUpdateDetail[];
  workflow_used: string;
  workflow_steps?: EpicorWorkflowSteps;  // Optional for backward compatibility
}

// API Response types
export interface EmailListItem {
  message_id: string;
  subject: string;
  sender: string;
  date: string;
  supplier_name: string;
  is_price_change: boolean;
  processed: boolean;
  needs_info: boolean;
  missing_fields_count: number;
  products_count: number;
  has_epicor_sync: boolean;
  epicor_success_count: number;
  file_path: string;
  verification_status: string;
  vendor_verified: boolean;
  verification_method?: string | null;
  flagged_reason?: string | null;
  received_time?: string;
}

export interface EmailListResponse {
  emails: EmailListItem[];
  total: number;
}

export interface EmailDetailResponse {
  email_data: EmailData;
  state: EmailState;
  validation: ValidationResult;
  epicor_status: EpicorStatus | null;
}

export interface FollowupRequest {
  missing_fields: MissingField[];
}

export interface FollowupResponse {
  success: boolean;
  followup_draft: string;
  generated_at: string;
}

export interface UserInfo {
  authenticated: boolean;
  email: string | null;
  name: string | null;
}

export interface VendorCacheStatus {
  last_updated: string | null;
  vendor_count: number;
  email_count: number;
  domain_count: number;
  is_stale: boolean;
  ttl_hours: number;
  next_refresh: string | null;
  domain_matching_enabled: boolean;
}

// Filter types
export type EmailFilter = 'all' | 'price_change' | 'non_price_change' | 'processed' | 'unprocessed' | 'pending_verification';
