/**
 * Hợp đồng dữ liệu API - Khóa ở Giai đoạn 0
 * Nguồn: contracts/openapi.yaml và contracts/seed-fixtures.json
 */

export type Role = 'STUDENT' | 'BCS' | 'GVCN' | 'ADMIN';

export type CampaignStatus =
  | 'DRAFT'
  | 'SCHEDULED'
  | 'OPEN'
  | 'REVIEW'
  | 'PUBLISHED'
  | 'FINALIZED';

export type CaseStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'NEEDS_INFO'
  | 'BCS_REVIEW'
  | 'NEEDS_PROOF'
  | 'PROPOSED'
  | 'PUBLISHED'
  | 'ACCEPTED'
  | 'APPEALED'
  | 'ACCEPTED_AUTO'
  | 'RESOLVED'
  | 'FINALIZED'
  | 'CLOSED_INCOMPLETE'
  | 'CLOSED_NO_SUBMIT';

export type SupplementKind = 'INFO' | 'PROOF';

export type MeetingKind = 'BCS' | 'CLASS';

export type AppealStatus = 'OPEN' | 'RESOLVED';

export type AppealResolution = 'KEEP' | 'ADJUST';

export interface User {
  id: string;
  username: string;
  full_name: string;
  role: Role;
  class_ids: string[];
}

export interface AuthResponse {
  user: User;
  csrf_token: string;
}

export interface Criterion {
  id: string;
  campaign_id: string;
  code: string;
  title: string;
  description: string | null;
  max_score: string; // Chuỗi số thập phân e.g. "10.00"
  requires_evidence: boolean;
  sort_order: number;
  section_code?: string | null;
  section_title?: string | null;
  section_max_score?: string | null;
  evidence_notes?: string | null;
  allowed_input_roles?: string[] | null;
  rule_config?: {
    discrete_levels?: number[];
    min?: number;
    max?: number;
    options?: Array<{ label: string; score: number; note?: string }>;
    unit?: string;
    [key: string]: any;
  } | null;
}

export interface EvidenceFile {
  id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string; // ISO 8601 UTC
  is_current: boolean;
}

export interface Claim {
  id: string;
  criterion_id: string;
  self_score: string | null;
  student_note: string | null;
  approved_score: string | null;
  bcs_reason: string | null;
  academic_gpa?: string | null;
  evidence: EvidenceFile[];
}

export interface SupplementRequest {
  id: string;
  case_id: string;
  kind: SupplementKind;
  criterion_id?: string | null;
  round_no: number;
  reason: string;
  requested_by?: string | null;
  deadline_at: string;
  fulfilled_at?: string | null;
}

export interface Appeal {
  id: string;
  case_id: string;
  criterion_id: string;
  student_reason: string;
  status: AppealStatus;
  resolution: AppealResolution | null;
  new_score: string | null;
  bcs_reason: string | null;
  submitted_at: string;
  resolved_at: string | null;
}

export interface Meeting {
  id: string;
  campaign_id: string;
  kind: MeetingKind;
  held_at: string;
  note: string | null;
}

export interface Campaign {
  id: string;
  class_id: string;
  title: string;
  term: string;
  term_start_on?: string | null;
  term_end_on?: string | null;
  template_code?: string | null;
  status: CampaignStatus;
  open_at: string;
  submission_deadline_at: string;
  supplement_period_hours: number;
  appeal_period_hours: number;
  reminder_after_hours: number;
  max_info_rounds: number;
  max_proof_rounds: number;
  criteria?: Criterion[];
}

export interface EvaluationTemplate {
  id: string;
  code: string;
  name: string;
  version: string;
  description: string | null;
  total_max_score: string;
  is_active: boolean;
  criteria?: Array<{
    code: string;
    title: string;
    description?: string | null;
    section_code: string;
    section_title: string;
    section_max_score: string;
    max_score: string;
    requires_evidence: boolean;
    sort_order: number;
    allowed_input_roles: string[];
    evidence_notes?: string | null;
    rule_config?: Record<string, any> | null;
  }>;
}

export interface UserPosition {
  id: string;
  user_id: string;
  term: string;
  position_title: string;
  organization: string;
  is_confirmed: boolean;
  created_at?: string;
}

export interface AcademicScoreImportItem {
  student_id: string;
  gpa: number;
}

export interface StudentCaseSummary {
  id: string;
  version: number;
  status: CaseStatus;
  claimed_total: string | null;
  proposed_total: string | null; // Chỉ có khi >= PUBLISHED
  final_total: string | null;    // Chỉ có khi == FINALIZED
  submitted_at: string | null;
  published_at: string | null;
  appeal_deadline_at: string | null;
  info_round: number;
  proof_round: number;
}

export interface AiReadFact {
  kind: string;
  value: string;
  page: number;
  source_excerpt: string;
}

export interface AiReadFile {
  evidence_file_id: string;
  sha256: string;
  readable: boolean;
  unreadable_reason: string;
  facts: AiReadFact[];
}

export interface AiTransparencyAssessment {
  evidence_file_id: string;
  sha256: string;
  criterion_code: string;
  rule_clause_id: string;
  rule_text: string;
  evidence_requirements: string;
  verdict: 'SUPPORTED' | 'FLAGGED' | 'UNKNOWN';
  confidence?: number | null;
  reason: string;
  citations: Array<{ page: number; source_excerpt: string; kind: string; value: string }>;
  visual_signals: Array<{ page: number; description: string; concern: boolean }>;
  authenticity: 'UNVERIFIED' | 'SUSPICIOUS';
  limitations: string[];
  requires_human_review: boolean;
  model: string | null;
  prompt_version: string;
}

export interface RuleFinding {
  code: string;
  level: 'FLAGGED' | 'UNKNOWN';
  message: string;
  criterion_id: string | null;
  criterion_code: string | null;
  evidence_file_ids: string[];
  details: Record<string, unknown>;
}

export interface RuleCheckResponse {
  case_id: string;
  case_version: number;
  rule_version: string;
  term_window: { status: 'CONFIGURED' | 'NOT_CONFIGURED'; start_on: string | null; end_on: string | null };
  date_evidence_status: string;
  findings: RuleFinding[];
  counts: { flagged: number; unknown: number };
  evaluated_at: string;
}

export interface ScoreSuggestionResponse {
  case_id: string;
  case_version: number;
  rubric_version: string;
  decision_version: string;
  rule_version: string;
  source_run_id: string | null;
  items: Array<{
    criterion_id: string;
    criterion_code: string;
    clause_id: string;
    self_score: string | null;
    draft_score: string | null;
    status: 'READY' | 'REVIEW_REQUIRED';
    reason: string;
    calculation: string | null;
    evidence_file_ids: string[];
    finding_codes: string[];
  }>;
  section_checks: Array<{ section_code: string; draft_subtotal: string; max_score: string; over_cap: boolean }>;
  draft_total: string | null;
  ready_count: number;
  review_required_count: number;
  requires_bcs_approval: boolean;
  evaluated_at: string;
}

export interface AiReviewRun {
  id: string;
  case_id: string;
  case_version: number;
  rubric_version: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'NEEDS_HUMAN' | 'FAILED' | 'STALE';
  stale: boolean;
  attempt_count: number;
  provider: string | null;
  model: string | null;
  prompt_version: string | null;
  result: { mode?: string; summary?: string; needs_human_review?: boolean; rule_checks?: RuleCheckResponse; score_suggestions?: ScoreSuggestionResponse; auto_accepted_evidence?: Array<{ evidence_file_id: string; confidence: number; threshold: number }> } | null;
  error_code: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  steps: Array<{
    kind: 'AI_READ' | 'AI_TRANSPARENCY';
    status: string;
    error_code: string | null;
    output: { files?: AiReadFile[]; assessments?: AiTransparencyAssessment[] } | null;
  }>;
}

export interface StudentCurrentResponse {
  campaign: Campaign;
  case: StudentCaseSummary;
  criteria: Criterion[];
  claims: Claim[];
  supplement_requests?: SupplementRequest[];
  appeals?: Appeal[];
  unread_notifications_count: number;
}

export interface BcsCampaignOverview {
  campaign_id: string;
  total_students: number;
  not_submitted_count: number;
  bcs_review_count: number;
  needs_info_count: number;
  needs_proof_count: number;
  proposed_count: number;
  published_count: number;
  open_appeals_count: number;
  finalized_count: number;
}

export interface BcsCaseListItem {
  id: string;
  student_code: string;
  student_name: string;
  status: CaseStatus;
  claimed_total: string | null;
  proposed_total: string | null;
  info_round: number;
  proof_round: number;
  updated_at: string;
}

export interface BcsCaseDetail {
  id: string;
  version: number;
  status: CaseStatus;
  student: {
    id: string;
    code: string;
    full_name: string;
  };
  deadlines: {
    submission_at: string | null;
    supplement_at: string | null;
  };
  rounds: {
    info: number;
    info_max: number;
    proof: number;
    proof_max: number;
  };
  claims: {
    criterion: Criterion;
    self_score: string | null;
    student_note: string | null;
    approved_score: string | null;
    bcs_reason: string | null;
    academic_gpa?: string | null;
    evidence: EvidenceFile[];
  }[];
  evidence_decisions?: {
    evidence_file_id: string;
    decision: 'ACCEPT' | 'REQUEST_SUPPLEMENT' | 'REJECT_ITEM' | 'HOLD';
    reason: string;
    reviewed_by: string;
    reviewed_at: string;
  }[];
  evidence_review_required_ids?: string[];
  auto_accepted_evidence?: Array<{ evidence_file_id: string; sha256: string; version_no: number; criterion_code: string; run_id: string; confidence: number; threshold: number; status: string }>;
  draft_editable?: boolean;
  supplement_requests: SupplementRequest[];
  review_mode: string;
  history: {
    action: string;
    at: string;
    actor: string;
  }[];
}

export interface FinalHandoff {
  status: 'NOT_SENT' | 'SENT' | 'RECEIVED';
  snapshot_sha256: string | null;
  sent_by: string | null;
  sent_at: string | null;
  received_by: string | null;
  received_at: string | null;
}

export interface ScoreboardItem {
  case_id: string;
  student_code: string;
  student_name: string;
  status: CaseStatus;
  claimed_total: string | null;
  proposed_total: string | null;
  final_total: string | null;
}

export interface ScoreboardResponse {
  campaign_id: string;
  can_publish: boolean;
  draft_review?: { fingerprint: string; reviewed: boolean; reviewed_at: string | null };
  meetings: Meeting[];
  items: ScoreboardItem[];
}

export interface AppealDetailItem {
  id: string;
  case_id: string;
  student_code: string;
  student_name: string;
  criterion_code: string;
  criterion_title: string;
  self_score: string;
  proposed_score: string;
  student_reason: string;
  status: AppealStatus;
  resolution: AppealResolution | null;
  new_score: string | null;
  bcs_reason: string | null;
  evidence: EvidenceFile[];
}

export interface NotificationItem {
  id: string;
  case_id: string | null;
  title: string;
  body: string;
  type: string;
  read_at: string | null;
  created_at: string;
}

export interface ErrorPayload {
  code: string;
  message: string;
  fields?: Record<string, string>;
}

export interface ErrorResponse {
  error: ErrorPayload;
}

export type DiscrepancyStatus = 'NEEDS_REVIEW' | 'AGREED' | 'NON_FINAL_DECISION' | 'NO_AI_RESULT';
export type GroundTruthStatus = 'UNVERIFIED' | 'VERIFIED';
export type GroundTruthLabel = 'SUPPORTED' | 'FLAGGED' | 'UNKNOWN';

export interface BcsAiFeedbackItem {
  id: string;
  evidence_file_id: string;
  file_sha256: string;
  file_version_no: number;
  case_id: string;
  criterion_id: string;
  criterion_code: string;
  bcs_decision: 'ACCEPT' | 'REJECT_ITEM' | 'REQUEST_SUPPLEMENT' | 'HOLD';
  bcs_reason: string;
  reviewer_name?: string | null;
  reviewed_at: string;
  ai_run_id?: string | null;
  ai_model?: string | null;
  ai_prompt_version?: string | null;
  ai_verdict?: 'SUPPORTED' | 'FLAGGED' | 'UNKNOWN' | null;
  ai_reason?: string | null;
  matching_status: string;
  discrepancy_status: DiscrepancyStatus;
  ground_truth_status: GroundTruthStatus;
  ground_truth_label?: GroundTruthLabel | null;
  verification_reason?: string | null;
  verifier_name?: string | null;
  verified_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BcsAiFeedbackDetail extends BcsAiFeedbackItem {
  ai_assessment?: Record<string, any> | null;
  file_original_name?: string | null;
  file_mime_type?: string | null;
  audit_history: Array<{
    action: string;
    actor_name?: string | null;
    actor_role?: string | null;
    created_at?: string | null;
    before?: Record<string, any>;
    after?: Record<string, any>;
  }>;
}

export interface VerifyGroundTruthPayload {
  ground_truth_label: GroundTruthLabel;
  reason: string;
}

export interface AiFeedbackMetrics {
  total_count: number;
  matched_count: number;
  no_ai_count: number;
  stale_ai_count: number;
  agreed_count: number;
  discrepancy_count: number;
  non_final_count: number;
  unverified_count: number;
  verified_count: number;
  verified_matched_count: number;
  ai_accuracy: number | null;
  ai_precision_supported: number | null;
  ai_recall_supported: number | null;
  confusion_matrix: Record<string, Record<string, number>> | null;
  discrepancy_resolution?: {
    verified_discrepancy_count: number;
    ai_correct_in_discrepancy: number;
    bcs_correct_in_discrepancy: number;
  } | null;
  message?: string | null;
}

export interface AiFeedbackListResponse {
  items: BcsAiFeedbackItem[];
  total: number;
  page: number;
  limit: number;
}
