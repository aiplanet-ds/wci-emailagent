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
  is_price_change: boolean | null;
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
  epicor_synced: boolean;
  llm_detection_performed: boolean;
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
  is_price_change: boolean | null;
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
  epicor_synced: boolean;
  llm_detection_performed: boolean;
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
export type EmailFilter = 'all' | 'price_change' | 'non_price_change' | 'processed' | 'unprocessed' | 'pending_verification' | 'rejected';

// ============================================================================
// BOM IMPACT ANALYSIS TYPES
// ============================================================================

export type BomImpactRiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'unknown';

export interface BomImpactRiskSummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  unknown: number;
}

export interface BomImpactSummary {
  total_assemblies_affected: number;
  risk_summary: BomImpactRiskSummary;
  total_annual_cost_impact: number;
  assemblies_with_demand_data: number;
  assemblies_without_demand_data: number;
  demand_from_forecast: number;
  assemblies_with_unknown_risk: number;
  has_data_quality_issues: boolean;
  requires_approval: boolean;
}

export interface BomImpactAssemblyDetail {
  assembly_part_num: string;
  assembly_description: string;
  revision: string;
  qty_per: number;
  cumulative_qty: number;
  level: number;
  path: string[];
  current_cost: number;
  selling_price: number;
  current_margin: number;
  current_margin_pct: number;
  new_cost: number;
  new_margin: number;
  new_margin_pct: number;
  margin_erosion: number;
  margin_erosion_pct: number;
  risk_level: BomImpactRiskLevel;
  weekly_demand: number;
  annual_cost_impact: number;
}

export interface BomImpactAnnualImpact {
  total_annual_cost_impact: number;
  assemblies_with_demand: number;
  assemblies_without_demand: number;
  breakdown: {
    assembly_part_num: string;
    weekly_demand: number;
    annual_demand: number;
    cost_impact_per_unit: number;
    annual_cost_impact: number;
  }[];
}

export interface BomImpactThresholds {
  critical: number;
  high: number;
  medium: number;
}

export type BomImpactActionType =
  | 'EXECUTIVE_APPROVAL_REQUIRED'
  | 'MANAGER_APPROVAL_REQUIRED'
  | 'REVIEW_RECOMMENDED'
  | 'AUTO_APPROVE_ELIGIBLE'
  | 'MANUAL_REVIEW_REQUIRED';

export interface BomImpactAction {
  action: BomImpactActionType;
  reason: string;
  assemblies?: string[];
}

export interface BomImpactResult {
  id: number;
  email_id: number;
  product_index: number;
  part_num: string | null;
  product_name: string | null;

  // Price change info
  old_price: number | null;
  new_price: number | null;
  price_delta: number | null;
  price_change_pct: number | null;

  // Component validation
  component_validated: boolean;
  component_description: string | null;

  // Supplier validation
  supplier_id: string | null;
  supplier_validated: boolean;
  supplier_name: string | null;
  vendor_num: number | null;

  // BOM impact analysis
  summary: BomImpactSummary | null;
  impact_details: BomImpactAssemblyDetail[];
  high_risk_assemblies: BomImpactAssemblyDetail[];
  annual_impact: BomImpactAnnualImpact | null;
  total_annual_cost_impact: number;

  // Actions and approval
  actions_required: BomImpactAction[];
  can_auto_approve: boolean;
  recommendation: string | null;
  thresholds_used: BomImpactThresholds | null;

  // Processing status
  status: 'pending' | 'success' | 'warning' | 'error';
  processing_errors: string[];

  // Approval tracking
  approved: boolean;
  approved_by_id: number | null;
  approved_at: string | null;
  approval_notes: string | null;

  // Timestamps
  created_at: string | null;
  updated_at: string | null;
}

export interface BomImpactResponse {
  email_id: number;
  message_id: string;
  total_products: number;
  impacts: BomImpactResult[];
}

export interface BomImpactApprovalRequest {
  approval_notes?: string;
}

export interface BomImpactApprovalResponse {
  success: boolean;
  message: string;
  impact?: BomImpactResult;
  approved_count?: number;
  already_approved?: number;
  total_products?: number;
}
