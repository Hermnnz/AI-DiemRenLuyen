import { StudentCurrentResponse, NotificationItem } from '../../api/types';

/**
 * Dữ liệu Mock chuẩn khớp contracts/seed-fixtures.json và contracts/openapi.yaml
 * Dành riêng cho Gói B - Frontend Sinh viên
 */

export const MOCK_CRITERIA = [
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

export const MOCK_CAMPAIGN_OPEN = {
  id: '33333333-3333-3333-3333-333333333333',
  class_id: '11111111-1111-1111-1111-111111111111',
  title: 'Đợt đánh giá ĐRL Học kỳ 1 2026-2027 (Minh họa)',
  term: 'HK1-2026-2027',
  status: 'OPEN' as const,
  open_at: '2026-10-24T00:00:00Z',
  submission_deadline_at: '2026-10-30T17:00:00Z',
  supplement_period_hours: 48,
  appeal_period_hours: 72,
  reminder_after_hours: 48,
  max_info_rounds: 2,
  max_proof_rounds: 2,
};

export const MOCK_CAMPAIGN_PUBLISHED = {
  ...MOCK_CAMPAIGN_OPEN,
  status: 'PUBLISHED' as const,
};

export const MOCK_CAMPAIGN_FINALIZED = {
  ...MOCK_CAMPAIGN_OPEN,
  status: 'FINALIZED' as const,
};

// 1. Trạng thái DRAFT (Khởi tạo ban đầu, sinh viên tự chấm)
export const MOCK_STUDENT_DRAFT: StudentCurrentResponse = {
  campaign: MOCK_CAMPAIGN_OPEN,
  case: {
    id: '55555555-5555-5555-5555-555555555001',
    version: 1,
    status: 'DRAFT',
    claimed_total: '0.00',
    proposed_total: null,
    final_total: null,
    submitted_at: null,
    published_at: null,
    appeal_deadline_at: null,
    info_round: 0,
    proof_round: 0,
  },
  criteria: MOCK_CRITERIA,
  claims: [
    {
      id: '66666666-6666-6666-6666-666666666001',
      criterion_id: '44444444-4444-4444-4444-444444444001',
      self_score: null,
      student_note: null,
      approved_score: null,
      bcs_reason: null,
      evidence: [],
    },
    {
      id: '66666666-6666-6666-6666-666666666002',
      criterion_id: '44444444-4444-4444-4444-444444444002',
      self_score: null,
      student_note: null,
      approved_score: null,
      bcs_reason: null,
      evidence: [],
    },
    {
      id: '66666666-6666-6666-6666-666666666003',
      criterion_id: '44444444-4444-4444-4444-444444444003',
      self_score: null,
      student_note: null,
      approved_score: null,
      bcs_reason: null,
      evidence: [],
    },
  ],
  supplement_requests: [],
  appeals: [],
  unread_notifications_count: 0,
};

// 2. Trạng thái NEEDS_INFO (Hệ thống yêu cầu bổ sung thông tin/minh chứng bắt buộc)
export const MOCK_STUDENT_NEEDS_INFO: StudentCurrentResponse = {
  campaign: MOCK_CAMPAIGN_OPEN,
  case: {
    id: '55555555-5555-5555-5555-555555555001',
    version: 2,
    status: 'NEEDS_INFO',
    claimed_total: '26.00',
    proposed_total: null,
    final_total: null,
    submitted_at: '2026-10-24T10:00:00Z',
    published_at: null,
    appeal_deadline_at: null,
    info_round: 1,
    proof_round: 0,
  },
  criteria: MOCK_CRITERIA,
  claims: [
    {
      id: '66666666-6666-6666-6666-666666666001',
      criterion_id: '44444444-4444-4444-4444-444444444001',
      self_score: '8.00',
      student_note: 'GPA 3.4/4.0',
      approved_score: null,
      bcs_reason: null,
      evidence: [], // Thiếu tệp minh chứng
    },
    {
      id: '66666666-6666-6666-6666-666666666002',
      criterion_id: '44444444-4444-4444-4444-444444444002',
      self_score: '10.00',
      student_note: 'Không vi phạm quy chế',
      approved_score: null,
      bcs_reason: null,
      evidence: [],
    },
    {
      id: '66666666-6666-6666-6666-666666666003',
      criterion_id: '44444444-4444-4444-4444-444444444003',
      self_score: '8.00',
      student_note: 'Tham gia tiếp sức mùa thi',
      approved_score: null,
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
  supplement_requests: [
    {
      id: '88888888-8888-8888-8888-888888888001',
      case_id: '55555555-5555-5555-5555-555555555001',
      kind: 'INFO',
      criterion_id: '44444444-4444-4444-4444-444444444001',
      round_no: 1,
      reason: 'Tiêu chí TC01 yêu cầu minh chứng bảng điểm nhưng chưa tải tệp',
      requested_by: null,
      deadline_at: '2026-10-26T10:00:00Z',
      fulfilled_at: null,
    },
  ],
  appeals: [],
  unread_notifications_count: 1,
};

// 3. Trạng thái NEEDS_PROOF (BCS yêu cầu bổ sung minh chứng)
export const MOCK_STUDENT_NEEDS_PROOF: StudentCurrentResponse = {
  ...MOCK_STUDENT_NEEDS_INFO,
  case: {
    ...MOCK_STUDENT_NEEDS_INFO.case,
    version: 3,
    status: 'NEEDS_PROOF',
    info_round: 1,
    proof_round: 1,
  },
  supplement_requests: [
    {
      id: '88888888-8888-8888-8888-888888888002',
      case_id: '55555555-5555-5555-5555-555555555001',
      kind: 'PROOF',
      criterion_id: '44444444-4444-4444-4444-444444444003',
      round_no: 1,
      reason: 'Ảnh chứng nhận tình nguyện mờ, đề nghị chụp lại rõ nét hoặc tải file scan PDF.',
      requested_by: '22222222-2222-2222-2222-222222222010',
      deadline_at: '2026-10-27T10:00:00Z',
      fulfilled_at: null,
    },
  ],
};

// 4. Trạng thái BCS_REVIEW (Đang chờ Ban cán sự kiểm tra, chưa công bố)
export const MOCK_STUDENT_BCS_REVIEW: StudentCurrentResponse = {
  campaign: MOCK_CAMPAIGN_OPEN,
  case: {
    id: '55555555-5555-5555-5555-555555555001',
    version: 3,
    status: 'BCS_REVIEW',
    claimed_total: '26.00',
    proposed_total: null, // BẮT BUỘC null trước PUBLISHED
    final_total: null,
    submitted_at: '2026-10-24T10:00:00Z',
    published_at: null,
    appeal_deadline_at: null,
    info_round: 0,
    proof_round: 0,
  },
  criteria: MOCK_CRITERIA,
  claims: [
    {
      id: '66666666-6666-6666-6666-666666666001',
      criterion_id: '44444444-4444-4444-4444-444444444001',
      self_score: '8.00',
      student_note: 'GPA 3.4/4.0',
      approved_score: null, // BẮT BUỘC ẩn
      bcs_reason: null,     // BẮT BUỘC ẩn
      evidence: [
        {
          id: '77777777-7777-7777-7777-777777777002',
          original_name: 'bang-diem.pdf',
          mime_type: 'application/pdf',
          size_bytes: 1048576,
          uploaded_at: '2026-10-24T09:30:00Z',
          is_current: true,
        },
      ],
    },
    {
      id: '66666666-6666-6666-6666-666666666002',
      criterion_id: '44444444-4444-4444-4444-444444444002',
      self_score: '10.00',
      student_note: 'Không vi phạm nội quy',
      approved_score: null,
      bcs_reason: null,
      evidence: [],
    },
    {
      id: '66666666-6666-6666-6666-666666666003',
      criterion_id: '44444444-4444-4444-4444-444444444003',
      self_score: '8.00',
      student_note: 'Chiến dịch tiếp sức mùa thi',
      approved_score: null,
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
  supplement_requests: [],
  appeals: [],
  unread_notifications_count: 0,
};

// 5. Trạng thái PUBLISHED (Đã công bố điểm dự kiến, SV có thể đồng ý hoặc khiếu nại)
export const MOCK_STUDENT_PUBLISHED: StudentCurrentResponse = {
  campaign: MOCK_CAMPAIGN_PUBLISHED,
  case: {
    id: '55555555-5555-5555-5555-555555555001',
    version: 4,
    status: 'PUBLISHED',
    claimed_total: '26.00',
    proposed_total: '24.00',
    final_total: null,
    submitted_at: '2026-10-24T10:00:00Z',
    published_at: '2026-10-28T09:00:00Z',
    appeal_deadline_at: '2026-10-31T09:00:00Z',
    info_round: 1,
    proof_round: 0,
  },
  criteria: MOCK_CRITERIA,
  claims: [
    {
      id: '66666666-6666-6666-6666-666666666001',
      criterion_id: '44444444-4444-4444-4444-444444444001',
      self_score: '8.00',
      student_note: 'GPA 3.4/4.0',
      approved_score: '8.00',
      bcs_reason: 'Minh chứng bảng điểm hợp lệ',
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
      id: '66666666-6666-6666-6666-666666666002',
      criterion_id: '44444444-4444-4444-4444-444444444002',
      self_score: '10.00',
      student_note: 'Không vi phạm quy chế',
      approved_score: '10.00',
      bcs_reason: 'BCS xác nhận',
      evidence: [],
    },
    {
      id: '66666666-6666-6666-6666-666666666003',
      criterion_id: '44444444-4444-4444-4444-444444444003',
      self_score: '8.00',
      student_note: 'Tham gia tiếp sức mùa thi',
      approved_score: '6.00',
      bcs_reason: 'Hoạt động cấp khoa chỉ tính tối đa 6.00 điểm theo thang điểm nội bộ',
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
  appeals: [],
  unread_notifications_count: 1,
};

// 6. Trạng thái ACCEPTED (Sinh viên đã đồng ý với kết quả)
export const MOCK_STUDENT_ACCEPTED: StudentCurrentResponse = {
  ...MOCK_STUDENT_PUBLISHED,
  case: {
    ...MOCK_STUDENT_PUBLISHED.case,
    version: 5,
    status: 'ACCEPTED',
  },
};

// 7. Trạng thái APPEALED (Sinh viên đã gửi khiếu nại, đang chờ BCS xử lý)
export const MOCK_STUDENT_APPEALED: StudentCurrentResponse = {
  ...MOCK_STUDENT_PUBLISHED,
  case: {
    ...MOCK_STUDENT_PUBLISHED.case,
    version: 5,
    status: 'APPEALED',
  },
  appeals: [
    {
      id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      case_id: '55555555-5555-5555-5555-555555555001',
      criterion_id: '44444444-4444-4444-4444-444444444003',
      student_reason: 'Em tham gia Ban tổ chức cấp Trường của chương trình tiếp sức mùa thi, có giấy khen trường.',
      status: 'OPEN',
      resolution: null,
      new_score: null,
      bcs_reason: null,
      submitted_at: '2026-10-28T14:30:00Z',
      resolved_at: null,
    },
  ],
};

// 8. Trạng thái RESOLVED (BCS đã giải quyết khiếu nại)
export const MOCK_STUDENT_RESOLVED: StudentCurrentResponse = {
  ...MOCK_STUDENT_PUBLISHED,
  case: {
    ...MOCK_STUDENT_PUBLISHED.case,
    version: 6,
    status: 'RESOLVED',
    proposed_total: '26.00',
  },
  claims: [
    MOCK_STUDENT_PUBLISHED.claims[0],
    MOCK_STUDENT_PUBLISHED.claims[1],
    {
      ...MOCK_STUDENT_PUBLISHED.claims[2],
      approved_score: '8.00',
      bcs_reason: 'BCS chấp thuận khiếu nại: xác minh có giấy khen cấp Trường, điều chỉnh thành 8.00 điểm',
    },
  ],
  appeals: [
    {
      id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      case_id: '55555555-5555-5555-5555-555555555001',
      criterion_id: '44444444-4444-4444-4444-444444444003',
      student_reason: 'Em tham gia Ban tổ chức cấp Trường của chương trình tiếp sức mùa thi, có giấy khen trường.',
      status: 'RESOLVED',
      resolution: 'ADJUST',
      new_score: '8.00',
      bcs_reason: 'BCS chấp thuận khiếu nại: xác minh có giấy khen cấp Trường, điều chỉnh thành 8.00 điểm',
      submitted_at: '2026-10-28T14:30:00Z',
      resolved_at: '2026-10-29T10:00:00Z',
    },
  ],
};

// 9. Trạng thái FINALIZED (Đã chốt chính thức toàn khóa)
export const MOCK_STUDENT_FINALIZED: StudentCurrentResponse = {
  campaign: MOCK_CAMPAIGN_FINALIZED,
  case: {
    ...MOCK_STUDENT_RESOLVED.case,
    version: 7,
    status: 'FINALIZED',
    final_total: '26.00',
  },
  criteria: MOCK_CRITERIA,
  claims: MOCK_STUDENT_RESOLVED.claims,
  appeals: MOCK_STUDENT_RESOLVED.appeals,
  unread_notifications_count: 0,
};

// 10. Trạng thái CLOSED_NO_SUBMIT (Quá hạn nộp mà không nộp)
export const MOCK_STUDENT_CLOSED_NO_SUBMIT: StudentCurrentResponse = {
  campaign: MOCK_CAMPAIGN_OPEN,
  case: {
    id: '55555555-5555-5555-5555-555555555001',
    version: 2,
    status: 'CLOSED_NO_SUBMIT',
    claimed_total: '0.00',
    proposed_total: null,
    final_total: null,
    submitted_at: null,
    published_at: null,
    appeal_deadline_at: null,
    info_round: 0,
    proof_round: 0,
  },
  criteria: MOCK_CRITERIA,
  claims: MOCK_STUDENT_DRAFT.claims,
  supplement_requests: [],
  appeals: [],
  unread_notifications_count: 0,
};

// Danh sách thông báo mẫu
export const MOCK_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 'notif-001',
    case_id: '55555555-5555-5555-5555-555555555001',
    title: 'Đợt đánh giá rèn luyện đã mở',
    body: 'Vui lòng hoàn thành tự chấm và nộp minh chứng trước 17:00 ngày 30/10/2026.',
    type: 'CAMPAIGN_OPENED',
    read_at: '2026-10-24T08:00:00Z',
    created_at: '2026-10-24T00:00:00Z',
  },
  {
    id: 'notif-002',
    case_id: '55555555-5555-5555-5555-555555555001',
    title: 'Yêu cầu bổ sung thông tin hồ sơ',
    body: 'Tiêu chí TC01 yêu cầu minh chứng bảng điểm nhưng chưa tải tệp. Hạn bổ sung: 10:00 ngày 26/10/2026.',
    type: 'INFO_REQUESTED',
    read_at: null,
    created_at: '2026-10-24T10:05:00Z',
  },
  {
    id: 'notif-003',
    case_id: '55555555-5555-5555-5555-555555555001',
    title: 'Điểm rèn luyện dự kiến đã công bố',
    body: 'Điểm dự kiến của bạn là 24.00/30.00. Bạn có thời hạn đến 09:00 ngày 31/10/2026 để xác nhận đồng ý hoặc khiếu nại.',
    type: 'SCORES_PUBLISHED',
    read_at: null,
    created_at: '2026-10-28T09:00:00Z',
  },
];

export const SCENARIO_DICTIONARY: Record<string, { label: string; data: StudentCurrentResponse }> = {
  DRAFT: { label: 'Bản nháp (DRAFT)', data: MOCK_STUDENT_DRAFT },
  NEEDS_INFO: { label: 'Cần bổ sung thông tin (NEEDS_INFO)', data: MOCK_STUDENT_NEEDS_INFO },
  NEEDS_PROOF: { label: 'Cần bổ sung minh chứng (NEEDS_PROOF)', data: MOCK_STUDENT_NEEDS_PROOF },
  BCS_REVIEW: { label: 'BCS đang kiểm tra (BCS_REVIEW)', data: MOCK_STUDENT_BCS_REVIEW },
  PUBLISHED: { label: 'Đã công bố điểm (PUBLISHED)', data: MOCK_STUDENT_PUBLISHED },
  ACCEPTED: { label: 'Đã đồng ý điểm (ACCEPTED)', data: MOCK_STUDENT_ACCEPTED },
  APPEALED: { label: 'Đang khiếu nại (APPEALED)', data: MOCK_STUDENT_APPEALED },
  RESOLVED: { label: 'Đã giải quyết khiếu nại (RESOLVED)', data: MOCK_STUDENT_RESOLVED },
  FINALIZED: { label: 'Đã chốt chính thức (FINALIZED)', data: MOCK_STUDENT_FINALIZED },
  CLOSED_NO_SUBMIT: { label: 'Đóng do không nộp (CLOSED_NO_SUBMIT)', data: MOCK_STUDENT_CLOSED_NO_SUBMIT },
};
