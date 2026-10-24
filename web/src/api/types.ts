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
    evidence: EvidenceFile[];
  }[];
  supplement_requests: SupplementRequest[];
  review_mode: string;
  history: {
    action: string;
    at: string;
    actor: string;
  }[];
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
