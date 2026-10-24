import {
  BcsCampaignOverview,
  BcsCaseDetail,
  BcsCaseListItem,
  ScoreboardResponse,
  ScoreboardItem,
  AppealDetailItem,
  Campaign,
  Criterion,
  Meeting,
  CaseStatus,
  CampaignStatus,
  SupplementKind,
  AppealResolution,
} from '../../api/types';

export interface GvcnScoreRecord {
  stt: number;
  student_code: string;
  student_name: string;
  claimed_total: string;
  proposed_total: string;
  final_total: string | null;
  status: CaseStatus;
  note: string;
}

const STORAGE_KEY = 'drl_staff_mock_store_v1';

// Seed criteria
export const SEED_CRITERIA: Criterion[] = [
  {
    id: '44444444-4444-4444-4444-444444444001',
    campaign_id: '33333333-3333-3333-3333-333333333333',
    code: 'TC01',
    title: 'Ý thức tham gia học tập',
    description: 'Dữ liệu minh họa — không dùng để ra quyết định thật. Tối đa 10 điểm.',
    max_score: '10.00',
    requires_evidence: true,
    sort_order: 1,
  },
  {
    id: '44444444-4444-4444-4444-444444444002',
    campaign_id: '33333333-3333-3333-3333-333333333333',
    code: 'TC02',
    title: 'Ý thức chấp hành nội quy, quy chế',
    description: 'Dữ liệu minh họa — không dùng để ra quyết định thật. Tối đa 10 điểm.',
    max_score: '10.00',
    requires_evidence: false,
    sort_order: 2,
  },
  {
    id: '44444444-4444-4444-4444-444444444003',
    campaign_id: '33333333-3333-3333-3333-333333333333',
    code: 'TC03',
    title: 'Ý thức tham gia hoạt động phong trào',
    description: 'Dữ liệu minh họa — không dùng để ra quyết định thật. Tối đa 10 điểm.',
    max_score: '10.00',
    requires_evidence: true,
    sort_order: 3,
  },
];

export interface StaffMockStore {
  campaign: Campaign;
  cases: Record<string, BcsCaseDetail>;
  meetings: Meeting[];
  appeals: AppealDetailItem[];
}

function createInitialStore(): StaffMockStore {
  return {
    campaign: {
      id: '33333333-3333-3333-3333-333333333333',
      class_id: '11111111-1111-1111-1111-111111111111',
      title: 'Đợt đánh giá ĐRL Học kỳ 1 2026-2027 (Minh họa)',
      term: 'HK1-2026-2027',
      status: 'REVIEW',
      open_at: '2026-10-25T01:00:00Z',
      submission_deadline_at: '2026-10-30T17:00:00Z',
      supplement_period_hours: 48,
      appeal_period_hours: 72,
      reminder_after_hours: 48,
      max_info_rounds: 2,
      max_proof_rounds: 2,
      criteria: SEED_CRITERIA,
    },
    cases: {
      '55555555-5555-5555-5555-555555555001': {
        id: '55555555-5555-5555-5555-555555555001',
        version: 4,
        status: 'BCS_REVIEW',
        student: {
          id: '22222222-2222-2222-2222-222222222001',
          code: 'SV001',
          full_name: 'Nguyễn Văn An',
        },
        deadlines: {
          submission_at: '2026-10-27T17:00:00Z',
          supplement_at: null,
        },
        rounds: {
          info: 1,
          info_max: 2,
          proof: 0,
          proof_max: 2,
        },
        claims: [
          {
            criterion: SEED_CRITERIA[0],
            self_score: '8.00',
            student_note: 'GPA 3.4/4.0',
            approved_score: '8.00',
            bcs_reason: 'BCS xác nhận theo bảng điểm',
            evidence: [
              {
                id: '77777777-7777-7777-7777-777777777002',
                original_name: 'bang-diem.pdf',
                mime_type: 'application/pdf',
                size_bytes: 1048576,
                uploaded_at: '2026-10-25T11:00:00Z',
                is_current: true,
              },
            ],
          },
          {
            criterion: SEED_CRITERIA[1],
            self_score: '10.00',
            student_note: 'Không vi phạm nội quy',
            approved_score: '10.00',
            bcs_reason: null,
            evidence: [],
          },
          {
            criterion: SEED_CRITERIA[2],
            self_score: '8.00',
            student_note: 'Tham gia chiến dịch tiếp sức mùa thi',
            approved_score: '6.00',
            bcs_reason: 'Hoạt động cấp khoa chỉ tính 6.00 điểm theo thang điểm nội bộ',
            evidence: [
              {
                id: '77777777-7777-7777-7777-777777777001',
                original_name: 'chung-nhan-tinh-nguyen.jpg',
                mime_type: 'image/jpeg',
                size_bytes: 524288,
                uploaded_at: '2026-10-24T09:45:00Z',
                is_current: true,
              },
            ],
          },
        ],
        supplement_requests: [],
        review_mode: 'MANUAL',
        history: [
          {
            action: 'CASE_CREATED',
            at: '2026-10-24T00:00:00Z',
            actor: 'SYSTEM',
          },
          {
            action: 'CASE_SUBMITTED',
            at: '2026-10-24T10:00:00Z',
            actor: 'SV001',
          },
          {
            action: 'INFO_REQUESTED',
            at: '2026-10-24T10:05:00Z',
            actor: 'SYSTEM',
          },
          {
            action: 'INFO_FULFILLED',
            at: '2026-10-25T11:00:00Z',
            actor: 'SV001',
          },
        ],
      },
      '55555555-5555-5555-5555-555555555002': {
        id: '55555555-5555-5555-5555-555555555002',
        version: 5,
        status: 'PROPOSED',
        student: {
          id: '22222222-2222-2222-2222-222222222002',
          code: 'SV002',
          full_name: 'Trần Thị Bình',
        },
        deadlines: {
          submission_at: '2026-10-27T17:00:00Z',
          supplement_at: null,
        },
        rounds: {
          info: 0,
          info_max: 2,
          proof: 0,
          proof_max: 2,
        },
        claims: [
          {
            criterion: SEED_CRITERIA[0],
            self_score: '9.00',
            student_note: 'GPA 3.6/4.0',
            approved_score: '9.00',
            bcs_reason: 'Minh chứng đầy đủ',
            evidence: [
              {
                id: '77777777-7777-7777-7777-777777777003',
                original_name: 'bang-diem-sv002.pdf',
                mime_type: 'application/pdf',
                size_bytes: 840000,
                uploaded_at: '2026-10-25T08:00:00Z',
                is_current: true,
              },
            ],
          },
          {
            criterion: SEED_CRITERIA[1],
            self_score: '10.00',
            student_note: 'Chấp hành tốt mọi quy chế',
            approved_score: '10.00',
            bcs_reason: null,
            evidence: [],
          },
          {
            criterion: SEED_CRITERIA[2],
            self_score: '9.00',
            student_note: 'Ban tổ chức hội thao trường',
            approved_score: '9.00',
            bcs_reason: 'Đầy đủ chứng nhận',
            evidence: [
              {
                id: '77777777-7777-7777-7777-777777777004',
                original_name: 'chung-nhan-hoi-thao.png',
                mime_type: 'image/png',
                size_bytes: 620000,
                uploaded_at: '2026-10-25T09:30:00Z',
                is_current: true,
              },
            ],
          },
        ],
        supplement_requests: [],
        review_mode: 'MANUAL',
        history: [
          { action: 'CASE_CREATED', at: '2026-10-24T00:00:00Z', actor: 'SYSTEM' },
          { action: 'CASE_SUBMITTED', at: '2026-10-25T10:00:00Z', actor: 'SV002' },
          { action: 'REVIEW_COMPLETED', at: '2026-10-26T14:00:00Z', actor: 'bcs001' },
        ],
      },
      '55555555-5555-5555-5555-555555555003': {
        id: '55555555-5555-5555-5555-555555555003',
        version: 3,
        status: 'NEEDS_INFO',
        student: {
          id: '22222222-2222-2222-2222-222222222003',
          code: 'SV003',
          full_name: 'Lê Văn Cường',
        },
        deadlines: {
          submission_at: '2026-10-27T17:00:00Z',
          supplement_at: '2026-10-29T17:00:00Z',
        },
        rounds: {
          info: 1,
          info_max: 2,
          proof: 0,
          proof_max: 2,
        },
        claims: [
          {
            criterion: SEED_CRITERIA[0],
            self_score: '7.00',
            student_note: 'GPA 2.9/4.0',
            approved_score: null,
            bcs_reason: null,
            evidence: [],
          },
          {
            criterion: SEED_CRITERIA[1],
            self_score: '8.00',
            student_note: 'Có 1 lần đi trễ',
            approved_score: null,
            bcs_reason: null,
            evidence: [],
          },
          {
            criterion: SEED_CRITERIA[2],
            self_score: '7.00',
            student_note: 'Tham gia ngày chủ nhật xanh',
            approved_score: null,
            bcs_reason: null,
            evidence: [],
          },
        ],
        supplement_requests: [
          {
            id: '66666666-6666-6666-6666-666666666001',
            case_id: '55555555-5555-5555-5555-555555555003',
            kind: 'INFO',
            criterion_id: '44444444-4444-4444-4444-444444444001',
            round_no: 1,
            reason: 'Thiếu minh chứng bảng điểm cho tiêu chí TC01',
            deadline_at: '2026-10-29T17:00:00Z',
          },
        ],
        review_mode: 'MANUAL',
        history: [
          { action: 'CASE_CREATED', at: '2026-10-24T00:00:00Z', actor: 'SYSTEM' },
          { action: 'CASE_SUBMITTED', at: '2026-10-24T18:00:00Z', actor: 'SV003' },
          { action: 'INFO_REQUESTED', at: '2026-10-25T08:00:00Z', actor: 'SYSTEM' },
        ],
      },
    },
    meetings: [
      {
        id: '99999999-9999-9999-9999-999999999001',
        campaign_id: '33333333-3333-3333-3333-333333333333',
        kind: 'BCS',
        held_at: '2026-10-27T14:00:00Z',
        note: 'Ban cán sự lớp đã họp kiểm tra rà soát 100% hồ sơ',
      },
      {
        id: '99999999-9999-9999-9999-999999999002',
        campaign_id: '33333333-3333-3333-3333-333333333333',
        kind: 'CLASS',
        held_at: '2026-10-27T16:00:00Z',
        note: 'Sinh hoạt lớp biểu quyết thông qua danh sách dự kiến',
      },
    ],
    appeals: [
      {
        id: '88888888-8888-8888-8888-888888888001',
        case_id: '55555555-5555-5555-5555-555555555001',
        student_code: 'SV001',
        student_name: 'Nguyễn Văn An',
        criterion_code: 'TC03',
        criterion_title: 'Ý thức tham gia hoạt động phong trào',
        self_score: '8.00',
        proposed_score: '6.00',
        student_reason: 'Em có giấy khen chiến dịch cấp trường, kính mong BCS xem xét lại để đạt 8.00 điểm.',
        status: 'OPEN',
        resolution: null,
        new_score: null,
        bcs_reason: null,
        evidence: [
          {
            id: '77777777-7777-7777-7777-777777777001',
            original_name: 'chung-nhan-tinh-nguyen.jpg',
            mime_type: 'image/jpeg',
            size_bytes: 524288,
            uploaded_at: '2026-10-24T09:45:00Z',
            is_current: true,
          },
        ],
      },
    ],
  };
}

class StaffStoreService {
  private store: StaffMockStore;

  constructor() {
    this.store = this.loadStore();
  }

  private loadStore(): StaffMockStore {
    try {
      if (typeof window !== 'undefined' && window.sessionStorage) {
        const raw = window.sessionStorage.getItem(STORAGE_KEY);
        if (raw) {
          return JSON.parse(raw);
        }
      }
    } catch {
      // ignore
    }
    return createInitialStore();
  }

  private saveStore() {
    try {
      if (typeof window !== 'undefined' && window.sessionStorage) {
        window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(this.store));
      }
    } catch {
      // ignore
    }
  }

  public resetStore() {
    this.store = createInitialStore();
    this.saveStore();
  }

  // --- Campaign ---
  public getCampaign(): Campaign {
    return this.store.campaign;
  }

  public updateCampaign(updated: Partial<Campaign>): Campaign {
    this.store.campaign = { ...this.store.campaign, ...updated };
    this.saveStore();
    return this.store.campaign;
  }

  public openCampaign(): { id: string; status: CampaignStatus } {
    const now = new Date();
    const openAt = new Date(this.store.campaign.open_at);
    const newStatus: CampaignStatus = openAt > now ? 'SCHEDULED' : 'OPEN';
    this.store.campaign.status = newStatus;
    this.saveStore();
    return { id: this.store.campaign.id, status: newStatus };
  }

  // --- Overview ---
  public getOverview(): BcsCampaignOverview {
    const allCases = Object.values(this.store.cases);
    const openAppeals = this.store.appeals.filter((a) => a.status === 'OPEN').length;

    let notSubmitted = 0;
    let bcsReview = 0;
    let needsInfo = 0;
    let needsProof = 0;
    let proposed = 0;
    let published = 0;
    let finalized = 0;

    for (const c of allCases) {
      if (c.status === 'DRAFT' || c.status === 'CLOSED_NO_SUBMIT') notSubmitted++;
      else if (c.status === 'BCS_REVIEW') bcsReview++;
      else if (c.status === 'NEEDS_INFO') needsInfo++;
      else if (c.status === 'NEEDS_PROOF') needsProof++;
      else if (c.status === 'PROPOSED') proposed++;
      else if (['PUBLISHED', 'ACCEPTED', 'ACCEPTED_AUTO', 'APPEALED', 'RESOLVED'].includes(c.status)) published++;
      else if (c.status === 'FINALIZED') finalized++;
    }

    return {
      campaign_id: this.store.campaign.id,
      total_students: allCases.length,
      not_submitted_count: notSubmitted,
      bcs_review_count: bcsReview,
      needs_info_count: needsInfo,
      needs_proof_count: needsProof,
      proposed_count: proposed,
      published_count: published,
      open_appeals_count: openAppeals,
      finalized_count: finalized,
    };
  }

  // --- Cases List ---
  public getCases(status?: string, q?: string, page = 1, pageSize = 20): { total: number; page: number; page_size: number; items: BcsCaseListItem[] } {
    let list = Object.values(this.store.cases);

    if (status && status !== 'ALL') {
      list = list.filter((c) => c.status === status);
    }

    if (q && q.trim()) {
      const lower = q.trim().toLowerCase();
      list = list.filter(
        (c) =>
          c.student.code.toLowerCase().includes(lower) ||
          c.student.full_name.toLowerCase().includes(lower)
      );
    }

    const total = list.length;
    const startIndex = (page - 1) * pageSize;
    const paged = list.slice(startIndex, startIndex + pageSize);

    const items: BcsCaseListItem[] = paged.map((c) => {
      const claimedTotal = c.claims
        .reduce((sum, item) => sum + (parseFloat(item.self_score || '0') || 0), 0)
        .toFixed(2);
      
      const allApproved = c.claims.every((item) => item.approved_score !== null);
      const proposedTotal = allApproved
        ? c.claims.reduce((sum, item) => sum + (parseFloat(item.approved_score || '0') || 0), 0).toFixed(2)
        : null;

      return {
        id: c.id,
        student_code: c.student.code,
        student_name: c.student.full_name,
        status: c.status,
        claimed_total: claimedTotal,
        proposed_total: proposedTotal,
        info_round: c.rounds.info,
        proof_round: c.rounds.proof,
        updated_at: c.history[c.history.length - 1]?.at || '2026-10-25T11:00:00Z',
      };
    });

    return {
      total,
      page,
      page_size: pageSize,
      items,
    };
  }

  // --- Case Detail ---
  public getCaseDetail(caseId: string): BcsCaseDetail | null {
    return this.store.cases[caseId] || null;
  }

  public reviewClaim(
    caseId: string,
    criterionId: string,
    approvedScore: string,
    reason: string | null,
    expectedVersion: number
  ): { case_id: string; version: number } {
    const c = this.store.cases[caseId];
    if (!c) throw { error: { code: 'NOT_FOUND', message: 'Không tìm thấy hồ sơ' } };
    if (c.version !== expectedVersion) {
      throw {
        error: {
          code: 'CASE_CHANGED',
          message: 'Hồ sơ đã được cập nhật bởi thao tác khác. Vui lòng tải lại trang.',
        },
      };
    }

    const claim = c.claims.find((cl) => cl.criterion.id === criterionId);
    if (!claim) throw { error: { code: 'CRITERION_NOT_FOUND', message: 'Không tìm thấy tiêu chí' } };

    const scoreNum = parseFloat(approvedScore);
    const maxNum = parseFloat(claim.criterion.max_score);
    if (isNaN(scoreNum) || scoreNum < 0 || scoreNum > maxNum) {
      throw {
        error: {
          code: 'INVALID_SCORE',
          message: `Điểm duyệt phải từ 0 đến ${claim.criterion.max_score}`,
        },
      };
    }

    // Reason required if different from self_score
    if (claim.self_score !== approvedScore && (!reason || !reason.trim())) {
      throw {
        error: {
          code: 'REASON_REQUIRED',
          message: 'Bắt buộc nhập lý do khi điểm duyệt khác điểm tự khai của sinh viên.',
        },
      };
    }

    claim.approved_score = approvedScore;
    claim.bcs_reason = reason;
    c.version += 1;
    c.history.push({
      action: 'CLAIM_REVIEWED',
      at: new Date().toISOString(),
      actor: 'BCS (Lớp trưởng)',
    });

    this.saveStore();
    return { case_id: c.id, version: c.version };
  }

  public createSupplementRequest(
    caseId: string,
    kind: SupplementKind,
    criterionId: string | null,
    reason: string,
    expectedVersion: number
  ): { case_id: string; version: number; new_status: CaseStatus } {
    const c = this.store.cases[caseId];
    if (!c) throw { error: { code: 'NOT_FOUND', message: 'Không tìm thấy hồ sơ' } };
    if (c.version !== expectedVersion) {
      throw {
        error: {
          code: 'CASE_CHANGED',
          message: 'Hồ sơ đã thay đổi. Vui lòng tải lại trang.',
        },
      };
    }

    if (kind === 'INFO') {
      if (c.rounds.info >= c.rounds.info_max) {
        throw {
          error: {
            code: 'MAX_ROUNDS_REACHED',
            message: `Đã đạt giới hạn tối đa ${c.rounds.info_max} lượt bổ sung thông tin.`,
          },
        };
      }
      c.rounds.info += 1;
      c.status = 'NEEDS_INFO';
    } else {
      if (c.rounds.proof >= c.rounds.proof_max) {
        throw {
          error: {
            code: 'MAX_ROUNDS_REACHED',
            message: `Đã đạt giới hạn tối đa ${c.rounds.proof_max} lượt bổ sung minh chứng.`,
          },
        };
      }
      c.rounds.proof += 1;
      c.status = 'NEEDS_PROOF';
    }

    const deadline = new Date();
    deadline.setHours(deadline.getHours() + (this.store.campaign.supplement_period_hours || 48));
    c.deadlines.supplement_at = deadline.toISOString();

    c.supplement_requests.push({
      id: `supp-${Date.now()}`,
      case_id: c.id,
      kind,
      criterion_id: criterionId,
      round_no: kind === 'INFO' ? c.rounds.info : c.rounds.proof,
      reason,
      requested_by: 'bcs001',
      deadline_at: deadline.toISOString(),
    });

    c.version += 1;
    c.history.push({
      action: kind === 'INFO' ? 'INFO_REQUESTED' : 'PROOF_REQUESTED',
      at: new Date().toISOString(),
      actor: 'BCS (Lớp trưởng)',
    });

    this.saveStore();
    return { case_id: c.id, version: c.version, new_status: c.status };
  }

  public completeReview(caseId: string, expectedVersion: number): { case_id: string; status: CaseStatus; proposed_total: string; version: number } {
    const c = this.store.cases[caseId];
    if (!c) throw { error: { code: 'NOT_FOUND', message: 'Không tìm thấy hồ sơ' } };
    if (c.version !== expectedVersion) {
      throw {
        error: {
          code: 'CASE_CHANGED',
          message: 'Hồ sơ đã thay đổi. Vui lòng tải lại trang.',
        },
      };
    }

    // Check all criteria reviewed
    for (const claim of c.claims) {
      if (claim.approved_score === null || claim.approved_score === '') {
        throw {
          error: {
            code: 'UNREVIEWED_CRITERION',
            message: `Tiêu chí ${claim.criterion.code} (${claim.criterion.title}) chưa được chấm điểm.`,
          },
        };
      }
      if (claim.self_score !== claim.approved_score && (!claim.bcs_reason || !claim.bcs_reason.trim())) {
        throw {
          error: {
            code: 'REASON_REQUIRED',
            message: `Tiêu chí ${claim.criterion.code} có điểm duyệt khác tự khai nhưng chưa có lý do.`,
          },
        };
      }
    }

    const proposedTotal = c.claims
      .reduce((sum, item) => sum + (parseFloat(item.approved_score || '0') || 0), 0)
      .toFixed(2);

    c.status = 'PROPOSED';
    c.version += 1;
    c.history.push({
      action: 'REVIEW_COMPLETED',
      at: new Date().toISOString(),
      actor: 'BCS (Lớp trưởng)',
    });

    this.saveStore();
    return {
      case_id: c.id,
      status: c.status,
      proposed_total: proposedTotal,
      version: c.version,
    };
  }

  // --- Scoreboard & Meetings & Publish ---
  public getScoreboard(): ScoreboardResponse {
    const allCases = Object.values(this.store.cases);
    const hasBcsMeeting = this.store.meetings.some((m) => m.kind === 'BCS');
    const hasClassMeeting = this.store.meetings.some((m) => m.kind === 'CLASS');
    const allProposedOrClosed = allCases.every((c) =>
      ['PROPOSED', 'PUBLISHED', 'ACCEPTED', 'ACCEPTED_AUTO', 'APPEALED', 'RESOLVED', 'FINALIZED', 'CLOSED_INCOMPLETE', 'CLOSED_NO_SUBMIT'].includes(c.status)
    );

    const canPublish = hasBcsMeeting && hasClassMeeting && allProposedOrClosed && this.store.campaign.status === 'REVIEW';

    const items: ScoreboardItem[] = allCases.map((c) => {
      const claimedTotal = c.claims
        .reduce((sum, item) => sum + (parseFloat(item.self_score || '0') || 0), 0)
        .toFixed(2);
      
      const allApproved = c.claims.every((item) => item.approved_score !== null);
      const proposedTotal = allApproved
        ? c.claims.reduce((sum, item) => sum + (parseFloat(item.approved_score || '0') || 0), 0).toFixed(2)
        : null;

      return {
        case_id: c.id,
        student_code: c.student.code,
        student_name: c.student.full_name,
        status: c.status,
        claimed_total: claimedTotal,
        proposed_total: proposedTotal,
        final_total: c.status === 'FINALIZED' ? proposedTotal : null,
      };
    });

    return {
      campaign_id: this.store.campaign.id,
      can_publish: canPublish,
      meetings: this.store.meetings,
      items,
    };
  }

  public recordMeeting(kind: 'BCS' | 'CLASS', heldAt: string, note: string | null): Meeting {
    const existingIndex = this.store.meetings.findIndex((m) => m.kind === kind);
    const meeting: Meeting = {
      id: existingIndex >= 0 ? this.store.meetings[existingIndex].id : `meeting-${Date.now()}`,
      campaign_id: this.store.campaign.id,
      kind,
      held_at: heldAt,
      note,
    };

    if (existingIndex >= 0) {
      this.store.meetings[existingIndex] = meeting;
    } else {
      this.store.meetings.push(meeting);
    }

    this.saveStore();
    return meeting;
  }

  public publishScores(): { campaign_id: string; status: CampaignStatus; published_at: string; appeal_deadline_at: string } {
    const scoreboard = this.getScoreboard();
    if (!scoreboard.can_publish) {
      throw {
        error: {
          code: 'CANNOT_PUBLISH',
          message: 'Chưa đủ điều kiện công bố: cần hoàn tất kiểm tra 100% hồ sơ và có biên bản 2 cuộc họp.',
        },
      };
    }

    const publishedAt = new Date().toISOString();
    const appealDeadline = new Date();
    appealDeadline.setHours(appealDeadline.getHours() + (this.store.campaign.appeal_period_hours || 72));

    this.store.campaign.status = 'PUBLISHED';

    // Transition proposed cases to PUBLISHED
    for (const c of Object.values(this.store.cases)) {
      if (c.status === 'PROPOSED') {
        c.status = 'PUBLISHED';
        c.deadlines.submission_at = null;
        c.version += 1;
        c.history.push({
          action: 'SCORES_PUBLISHED',
          at: publishedAt,
          actor: 'BCS (Lớp trưởng)',
        });
      }
    }

    this.saveStore();
    return {
      campaign_id: this.store.campaign.id,
      status: 'PUBLISHED',
      published_at: publishedAt,
      appeal_deadline_at: appealDeadline.toISOString(),
    };
  }

  // --- Appeals ---
  public getAppeals(): AppealDetailItem[] {
    return this.store.appeals;
  }

  public resolveAppeal(
    appealId: string,
    resolution: AppealResolution,
    newScore: string | null,
    reason: string
  ): AppealDetailItem {
    const appeal = this.store.appeals.find((a) => a.id === appealId);
    if (!appeal) throw { error: { code: 'NOT_FOUND', message: 'Không tìm thấy khiếu nại' } };

    if (!reason || !reason.trim()) {
      throw { error: { code: 'REASON_REQUIRED', message: 'Bắt buộc nhập lý do giải quyết khiếu nại' } };
    }

    if (resolution === 'ADJUST') {
      if (!newScore || isNaN(parseFloat(newScore))) {
        throw { error: { code: 'INVALID_NEW_SCORE', message: 'Vui lòng nhập điểm mới hợp lệ khi điều chỉnh' } };
      }
      appeal.new_score = newScore;
    } else {
      appeal.new_score = null;
    }

    appeal.status = 'RESOLVED';
    appeal.resolution = resolution;
    appeal.bcs_reason = reason;

    // Update case if adjusted
    const c = this.store.cases[appeal.case_id];
    if (c) {
      if (resolution === 'ADJUST' && newScore) {
        const claim = c.claims.find((cl) => cl.criterion.code === appeal.criterion_code);
        if (claim) {
          claim.approved_score = newScore;
          claim.bcs_reason = `Khiếu nại được điều chỉnh: ${reason}`;
        }
      }
      c.status = 'RESOLVED';
      c.version += 1;
      c.history.push({
        action: `APPEAL_${resolution}`,
        at: new Date().toISOString(),
        actor: 'BCS (Lớp trưởng)',
      });
    }

    this.saveStore();
    return appeal;
  }

  public finalizeCampaign(): { campaign_id: string; status: CampaignStatus; finalized_at: string } {
    const openAppeals = this.store.appeals.filter((a) => a.status === 'OPEN');
    if (openAppeals.length > 0) {
      throw {
        error: {
          code: 'UNRESOLVED_APPEALS',
          message: `Còn ${openAppeals.length} khiếu nại chưa giải quyết. Phải giải quyết hết trước khi chốt điểm.`,
        },
      };
    }

    const finalizedAt = new Date().toISOString();
    this.store.campaign.status = 'FINALIZED';

    for (const c of Object.values(this.store.cases)) {
      if (['PUBLISHED', 'ACCEPTED', 'ACCEPTED_AUTO', 'RESOLVED', 'PROPOSED'].includes(c.status)) {
        c.status = 'FINALIZED';
        c.version += 1;
        c.history.push({
          action: 'CAMPAIGN_FINALIZED',
          at: finalizedAt,
          actor: 'BCS (Lớp trưởng)',
        });
      }
    }

    this.saveStore();
    return {
      campaign_id: this.store.campaign.id,
      status: 'FINALIZED',
      finalized_at: finalizedAt,
    };
  }

  // --- GVCN Final Scores ---
  public getGvcnFinalScores(): GvcnScoreRecord[] {
    const allCases = Object.values(this.store.cases);
    return allCases.map((c, idx) => {
      const claimedTotal = c.claims
        .reduce((sum, item) => sum + (parseFloat(item.self_score || '0') || 0), 0)
        .toFixed(2);
      
      const allApproved = c.claims.every((item) => item.approved_score !== null);
      const proposedTotal = allApproved
        ? c.claims.reduce((sum, item) => sum + (parseFloat(item.approved_score || '0') || 0), 0).toFixed(2)
        : '0.00';

      return {
        stt: idx + 1,
        student_code: c.student.code,
        student_name: c.student.full_name,
        claimed_total: claimedTotal,
        proposed_total: proposedTotal,
        final_total: proposedTotal,
        status: c.status,
        note: c.status === 'FINALIZED' ? 'Đã chốt chính thức' : 'Chưa chốt',
      };
    });
  }

  public exportGvcnCsvContent(): string {
    const records = this.getGvcnFinalScores();
    const headers = ['STT', 'Mã SV', 'Họ và tên', 'Điểm tự khai', 'Điểm dự kiến', 'Điểm chính thức', 'Trạng thái', 'Ghi chú'];
    const rows = records.map((r) => [
      r.stt,
      `"${r.student_code}"`,
      `"${r.student_name}"`,
      r.claimed_total,
      r.proposed_total,
      r.final_total || '',
      `"${r.status}"`,
      `"${r.note}"`,
    ]);

    // Include UTF-8 BOM for Excel compatibility
    return '\uFEFF' + [headers.join(','), ...rows.map((row) => row.join(','))].join('\r\n');
  }
}

export const staffStore = new StaffStoreService();
