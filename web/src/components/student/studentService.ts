import {
  StudentCurrentResponse,
  Claim,
  EvidenceFile,
  NotificationItem,
  CaseStatus,
  Appeal,
  ErrorResponse,
} from '../../api/types';
import {
  MOCK_STUDENT_DRAFT,
  MOCK_NOTIFICATIONS,
  SCENARIO_DICTIONARY,
} from './studentMockData';

const STORAGE_KEY_MODE = 'drl_student_mode';
const STORAGE_KEY_SCENARIO = 'drl_student_scenario';
const STORAGE_KEY_STATE = 'drl_student_custom_state';
const STORAGE_KEY_NOTIFS = 'drl_student_notifications';

export type OperationMode = 'live' | 'mock';

// Lazy loader cho api client để an toàn khi chạy trong cả môi trường Vite lẫn Node test runner
let cachedApi: any = null;
async function getApi() {
  if (!cachedApi) {
    try {
      const module = await import('../../api/client');
      cachedApi = module.api;
    } catch (e) {
      console.warn('Không thể nạp ApiClient:', e);
      throw e;
    }
  }
  return cachedApi;
}

class StudentService {
  private mode: OperationMode = 'mock';
  private currentScenario: string = 'DRAFT';

  constructor() {
    // Tải cấu hình từ localStorage nếu có (và nếu đang chạy trong môi trường có localStorage)
    if (typeof localStorage !== 'undefined') {
      const savedMode = localStorage.getItem(STORAGE_KEY_MODE) as OperationMode | null;
      if (savedMode === 'live' || savedMode === 'mock') {
        this.mode = savedMode;
      }
      const savedScenario = localStorage.getItem(STORAGE_KEY_SCENARIO);
      if (savedScenario && SCENARIO_DICTIONARY[savedScenario]) {
        this.currentScenario = savedScenario;
      }
    }
  }

  public getMode(): OperationMode {
    return this.mode;
  }

  public setMode(mode: OperationMode) {
    this.mode = mode;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY_MODE, mode);
    }
  }

  public getCurrentScenarioKey(): string {
    return this.currentScenario;
  }

  public setScenario(scenarioKey: string) {
    if (SCENARIO_DICTIONARY[scenarioKey]) {
      this.currentScenario = scenarioKey;
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(STORAGE_KEY_SCENARIO, scenarioKey);
        // Xóa custom state để reset về dữ liệu gốc của kịch bản
        localStorage.removeItem(STORAGE_KEY_STATE);
      }
    }
  }

  public resetScenario() {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY_STATE);
      localStorage.removeItem(STORAGE_KEY_NOTIFS);
    }
  }

  private getMockState(): StudentCurrentResponse {
    if (typeof localStorage !== 'undefined') {
      const custom = localStorage.getItem(STORAGE_KEY_STATE);
      if (custom) {
        try {
          return JSON.parse(custom);
        } catch {
          // Fallback
        }
      }
    }
    const base = SCENARIO_DICTIONARY[this.currentScenario]?.data || MOCK_STUDENT_DRAFT;
    return JSON.parse(JSON.stringify(base));
  }

  private saveMockState(state: StudentCurrentResponse) {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY_STATE, JSON.stringify(state));
    }
  }

  /**
   * Lấy dữ liệu hồ sơ hiện tại
   */
  public async getCurrent(): Promise<StudentCurrentResponse> {
    if (this.mode === 'live') {
      try {
        const api = await getApi();
        return await api.get('/student/current');
      } catch (err) {
        console.warn('Backend API /student/current không khả dụng, chuyển sang chế độ Mock:', err);
        // Tự động fallback sang mock nếu backend chưa chạy
      }
    }
    return this.getMockState();
  }

  /**
   * Lưu nháp hoặc bổ sung tiêu chí (PUT /student/cases/{caseId}/claims/{criterionId})
   */
  public async saveClaim(
    caseId: string,
    criterionId: string,
    selfScore: string | null,
    studentNote: string | null,
    expectedVersion: number
  ): Promise<{ case_id: string; version: number; claim: Claim }> {
    if (this.mode === 'live') {
      try {
        const api = await getApi();
        return await api.put(
          `/student/cases/${caseId}/claims/${criterionId}`,
          {
            self_score: selfScore,
            student_note: studentNote,
            expected_version: expectedVersion,
          }
        );
      } catch (err) {
        if ((err as ErrorResponse)?.error?.code) throw err;
        console.warn('Backend chưa sẵn sàng, lưu nháp qua Mock State');
      }
    }

    // Xử lý Mock State
    const state = this.getMockState();
    if (state.case.version !== expectedVersion) {
      const err: ErrorResponse = {
        error: {
          code: 'CASE_CHANGED',
          message: 'Hồ sơ đã được cập nhật từ phiên khác. Vui lòng tải lại dữ liệu.',
          fields: {},
        },
      };
      throw err;
    }

    const claimIndex = state.claims.findIndex((c) => c.criterion_id === criterionId);
    if (claimIndex === -1) {
      const err: ErrorResponse = {
        error: {
          code: 'CRITERION_NOT_FOUND',
          message: 'Không tìm thấy tiêu chí trong hồ sơ',
          fields: {},
        },
      };
      throw err;
    }

    const newVersion = state.case.version + 1;
    state.claims[claimIndex].self_score = selfScore;
    state.claims[claimIndex].student_note = studentNote;
    state.case.version = newVersion;

    // Cập nhật claimed_total
    let total = 0;
    for (const c of state.claims) {
      if (c.self_score) {
        total += parseFloat(c.self_score) || 0;
      }
    }
    state.case.claimed_total = total.toFixed(2);

    this.saveMockState(state);

    return {
      case_id: caseId,
      version: newVersion,
      claim: state.claims[claimIndex],
    };
  }

  /**
   * Tải tệp minh chứng cho tiêu chí (POST /student/cases/{caseId}/evidence)
   */
  public async uploadEvidence(
    caseId: string,
    criterionId: string,
    file: { name: string; type: string; size: number }
  ): Promise<EvidenceFile> {
    // Validate phía client: PDF/JPG/PNG và <= 10MB
    const validMimes = ['application/pdf', 'image/jpeg', 'image/png'];
    if (!validMimes.includes(file.type)) {
      const err: ErrorResponse = {
        error: {
          code: 'INVALID_FILE_TYPE',
          message: 'Chỉ chấp nhận tệp định dạng PDF, JPG hoặc PNG.',
          fields: { file: 'Mime type không hợp lệ' },
        },
      };
      throw err;
    }

    const maxBytes = 10 * 1024 * 1024; // 10MB
    if (file.size > maxBytes) {
      const err: ErrorResponse = {
        error: {
          code: 'FILE_TOO_LARGE',
          message: 'Dung lượng tệp tối đa là 10 MB.',
          fields: { file: 'Kích thước vượt quá 10MB' },
        },
      };
      throw err;
    }

    if (this.mode === 'live') {
      try {
        const api = await getApi();
        const formData = new FormData();
        formData.append('criterion_id', criterionId);
        formData.append('file', file as any);
        return await api.upload(`/student/cases/${caseId}/evidence`, formData);
      } catch (err) {
        if ((err as ErrorResponse)?.error?.code) throw err;
        console.warn('Backend chưa sẵn sàng, tải tệp qua Mock State');
      }
    }

    // Mock upload
    const state = this.getMockState();
    const claim = state.claims.find((c) => c.criterion_id === criterionId);
    if (!claim) {
      throw {
        error: {
          code: 'CRITERION_NOT_FOUND',
          message: 'Không tìm thấy tiêu chí để đính kèm minh chứng',
        },
      };
    }

    const newEvidence: EvidenceFile = {
      id: `mock-file-${Date.now()}`,
      original_name: file.name,
      mime_type: file.type,
      size_bytes: file.size,
      uploaded_at: new Date().toISOString(),
      is_current: true,
    };

    claim.evidence = [...claim.evidence, newEvidence];
    this.saveMockState(state);

    return newEvidence;
  }

  /**
   * Xóa minh chứng (trong trạng thái còn cho phép sửa)
   */
  public async removeEvidence(
    caseId: string,
    criterionId: string,
    fileId: string
  ): Promise<void> {
    const state = this.getMockState();
    const claim = state.claims.find((c) => c.criterion_id === criterionId);
    if (claim) {
      claim.evidence = claim.evidence.filter((f) => f.id !== fileId);
      this.saveMockState(state);
    }
  }

  /**
   * Sinh viên nộp hồ sơ (POST /student/cases/{caseId}/submit)
   */
  public async submitCase(
    caseId: string,
    expectedVersion: number
  ): Promise<{
    case_id: string;
    status: CaseStatus;
    version: number;
    missing_items: string[];
  }> {
    if (this.mode === 'live') {
      try {
        const api = await getApi();
        return await api.post(
          `/student/cases/${caseId}/submit`,
          { expected_version: expectedVersion },
          `submit-${caseId}-${Date.now()}`
        );
      } catch (err) {
        if ((err as ErrorResponse)?.error?.code) throw err;
        console.warn('Backend chưa sẵn sàng, nộp qua Mock State');
      }
    }

    const state = this.getMockState();
    if (state.case.version !== expectedVersion) {
      throw {
        error: {
          code: 'CASE_CHANGED',
          message: 'Hồ sơ đã được thay đổi, vui lòng tải lại.',
          fields: {},
        },
      };
    }

    // Kiểm tra thiếu minh chứng bắt buộc
    const missing: string[] = [];
    for (const crit of state.criteria) {
      const claim = state.claims.find((c) => c.criterion_id === crit.id);
      if (crit.requires_evidence && (!claim || !claim.evidence || claim.evidence.length === 0)) {
        missing.push(`Tiêu chí ${crit.code}: thiếu minh chứng bắt buộc`);
      }
    }

    const newVersion = state.case.version + 1;
    let nextStatus: CaseStatus = 'BCS_REVIEW';

    // Theo đặc tả: nếu thiếu minh chứng bắt buộc -> chuyển NEEDS_INFO
    if (missing.length > 0) {
      nextStatus = 'NEEDS_INFO';
      state.case.info_round += 1;
      state.supplement_requests = [
        {
          id: `supp-${Date.now()}`,
          case_id: caseId,
          kind: 'INFO',
          round_no: state.case.info_round,
          reason: missing.join('; '),
          deadline_at: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
          fulfilled_at: null,
        },
      ];
    } else {
      // Đủ cấu trúc -> BCS_REVIEW
      state.supplement_requests = [];
    }

    state.case.status = nextStatus;
    state.case.version = newVersion;
    state.case.submitted_at = new Date().toISOString();
    this.saveMockState(state);

    return {
      case_id: caseId,
      status: nextStatus,
      version: newVersion,
      missing_items: missing,
    };
  }

  /**
   * Sinh viên chấp nhận điểm dự kiến (POST /student/cases/{caseId}/accept)
   */
  public async acceptCase(
    caseId: string,
    expectedVersion: number
  ): Promise<{
    case_id: string;
    status: CaseStatus;
    version: number;
    acceptance_source: string;
  }> {
    if (this.mode === 'live') {
      try {
        const api = await getApi();
        return await api.post(
          `/student/cases/${caseId}/accept`,
          { expected_version: expectedVersion },
          `accept-${caseId}-${Date.now()}`
        );
      } catch (err) {
        if ((err as ErrorResponse)?.error?.code) throw err;
        console.warn('Backend chưa sẵn sàng, chấp nhận qua Mock State');
      }
    }

    const state = this.getMockState();
    if (state.case.version !== expectedVersion) {
      throw {
        error: {
          code: 'CASE_CHANGED',
          message: 'Hồ sơ đã thay đổi, vui lòng tải lại.',
          fields: {},
        },
      };
    }

    const newVersion = state.case.version + 1;
    state.case.status = 'ACCEPTED';
    state.case.version = newVersion;
    this.saveMockState(state);

    return {
      case_id: caseId,
      status: 'ACCEPTED',
      version: newVersion,
      acceptance_source: 'EXPLICIT',
    };
  }

  /**
   * Sinh viên khiếu nại điểm (POST /student/cases/{caseId}/appeals)
   */
  public async createAppeals(
    caseId: string,
    items: { criterion_id: string; reason: string }[],
    expectedVersion: number
  ): Promise<{
    case_id: string;
    status: CaseStatus;
    version: number;
    appeals: Appeal[];
  }> {
    if (this.mode === 'live') {
      try {
        const api = await getApi();
        return await api.post(
          `/student/cases/${caseId}/appeals`,
          {
            expected_version: expectedVersion,
            items,
          },
          `appeal-${caseId}-${Date.now()}`
        );
      } catch (err) {
        if ((err as ErrorResponse)?.error?.code) throw err;
        console.warn('Backend chưa sẵn sàng, gửi khiếu nại qua Mock State');
      }
    }

    const state = this.getMockState();
    if (state.case.version !== expectedVersion) {
      throw {
        error: {
          code: 'CASE_CHANGED',
          message: 'Hồ sơ đã thay đổi, vui lòng tải lại.',
          fields: {},
        },
      };
    }

    const newVersion = state.case.version + 1;
    const createdAppeals: Appeal[] = items.map((it, idx) => ({
      id: `appeal-${Date.now()}-${idx}`,
      case_id: caseId,
      criterion_id: it.criterion_id,
      student_reason: it.reason,
      status: 'OPEN',
      resolution: null,
      new_score: null,
      bcs_reason: null,
      submitted_at: new Date().toISOString(),
      resolved_at: null,
    }));

    state.case.status = 'APPEALED';
    state.case.version = newVersion;
    state.appeals = [...(state.appeals || []), ...createdAppeals];
    this.saveMockState(state);

    return {
      case_id: caseId,
      status: 'APPEALED',
      version: newVersion,
      appeals: state.appeals,
    };
  }

  /**
   * Danh sách thông báo (GET /notifications)
   */
  public async getNotifications(): Promise<NotificationItem[]> {
    if (this.mode === 'live') {
      try {
        const api = await getApi();
        return await api.get('/notifications');
      } catch (err) {
        console.warn('Backend chưa sẵn sàng, lấy thông báo mock');
      }
    }

    if (typeof localStorage !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY_NOTIFS);
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {
          // Fallback
        }
      }
    }
    return MOCK_NOTIFICATIONS;
  }

  /**
   * Đánh dấu đã đọc thông báo (POST /notifications/{id}/read)
   */
  public async markNotificationRead(id: string): Promise<{ success: boolean }> {
    if (this.mode === 'live') {
      try {
        const api = await getApi();
        return await api.post(`/notifications/${id}/read`);
      } catch {
        // Fallback mock
      }
    }

    const notifs = await this.getNotifications();
    const updated = notifs.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n));
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY_NOTIFS, JSON.stringify(updated));
    }
    return { success: true };
  }
}

export const studentService = new StudentService();
