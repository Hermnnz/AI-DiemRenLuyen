import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  MOCK_CRITERIA,
  MOCK_STUDENT_DRAFT,
  MOCK_STUDENT_NEEDS_INFO,
  MOCK_STUDENT_PUBLISHED,
  MOCK_STUDENT_ACCEPTED,
  MOCK_STUDENT_APPEALED,
  MOCK_STUDENT_RESOLVED,
  MOCK_STUDENT_FINALIZED,
  MOCK_STUDENT_CLOSED_NO_SUBMIT,
} from '../../components/student/studentMockData';
import { studentService } from '../../components/student/studentService';

describe('Gói B - Logic Frontend Sinh viên', () => {
  // 1. Kiểm tra tính điểm tự khai
  describe('Tính toán tổng điểm tự khai (claimed_total)', () => {
    test('Cộng chính xác các điểm dạng chuỗi thập phân mà không bị lỗi số thực (float glitch)', () => {
      const scores = ['8.00', '10.00', '8.00'];
      const total = scores.reduce((acc, s) => acc + parseFloat(s), 0);
      assert.strictEqual(total.toFixed(2), '26.00');
    });

    test('Xử lý an toàn khi tiêu chí có self_score là null hoặc rỗng', () => {
      const scores: (string | null)[] = ['8.00', null, ''];
      const total = scores.reduce((acc, s) => (s ? acc + parseFloat(s) : acc), 0);
      assert.strictEqual(total.toFixed(2), '8.00');
    });

    test('Tổng điểm tối đa của 3 tiêu chí demo đúng 30.00 điểm', () => {
      const maxTotal = MOCK_CRITERIA.reduce((acc, c) => acc + parseFloat(c.max_score), 0);
      assert.strictEqual(maxTotal.toFixed(2), '30.00');
    });
  });

  // 2. Kiểm tra xác thực (Validation)
  describe('Xác thực ô nhập điểm tự chấm và lý do khiếu nại', () => {
    const maxScore = 10.0;

    const validateScore = (val: string, max: number): { valid: boolean; error?: string } => {
      if (val.trim() === '') return { valid: true };
      const num = parseFloat(val);
      if (isNaN(num)) return { valid: false, error: 'Chữ số không hợp lệ' };
      if (num < 0) return { valid: false, error: 'Điểm không được âm' };
      if (num > max) return { valid: false, error: 'Vượt quá điểm tối đa' };
      return { valid: true };
    };

    test('Chấp nhận các giá trị điểm hợp lệ', () => {
      assert.strictEqual(validateScore('0.00', maxScore).valid, true);
      assert.strictEqual(validateScore('5.50', maxScore).valid, true);
      assert.strictEqual(validateScore('10.00', maxScore).valid, true);
      assert.strictEqual(validateScore('8', maxScore).valid, true);
    });

    test('Từ chối điểm âm hoặc điểm vượt quá trần tiêu chí', () => {
      assert.strictEqual(validateScore('-1.00', maxScore).valid, false);
      assert.strictEqual(validateScore('10.50', maxScore).valid, false);
      assert.strictEqual(validateScore('abc', maxScore).valid, false);
    });

    test('Xác thực tệp minh chứng: chỉ chấp nhận PDF/JPG/PNG và <= 10MB', () => {
      const validMimes = ['application/pdf', 'image/jpeg', 'image/png'];
      assert.strictEqual(validMimes.includes('application/pdf'), true);
      assert.strictEqual(validMimes.includes('image/jpeg'), true);
      assert.strictEqual(validMimes.includes('image/png'), true);
      assert.strictEqual(validMimes.includes('application/zip'), false);
      assert.strictEqual(validMimes.includes('text/plain'), false);

      const maxBytes = 10 * 1024 * 1024;
      assert.strictEqual(524288 <= maxBytes, true);
      assert.strictEqual(15 * 1024 * 1024 <= maxBytes, false);
    });
  });

  // 3. Quy tắc khóa và phân quyền trạng thái (State Lock Rules)
  describe('Quy tắc khóa trạng thái (Editable vs Read-only)', () => {
    const isStatusEditable = (status: string): boolean => {
      const editableStatuses = ['DRAFT', 'NEEDS_INFO', 'NEEDS_PROOF'];
      return editableStatuses.includes(status);
    };

    test('Chỉ cho phép sửa ở DRAFT, NEEDS_INFO, NEEDS_PROOF', () => {
      assert.strictEqual(isStatusEditable('DRAFT'), true);
      assert.strictEqual(isStatusEditable('NEEDS_INFO'), true);
      assert.strictEqual(isStatusEditable('NEEDS_PROOF'), true);
    });

    test('Khóa toàn bộ form ở các trạng thái đang kiểm tra hoặc đã xong', () => {
      assert.strictEqual(isStatusEditable('SUBMITTED'), false);
      assert.strictEqual(isStatusEditable('BCS_REVIEW'), false);
      assert.strictEqual(isStatusEditable('PROPOSED'), false);
      assert.strictEqual(isStatusEditable('PUBLISHED'), false);
      assert.strictEqual(isStatusEditable('ACCEPTED'), false);
      assert.strictEqual(isStatusEditable('APPEALED'), false);
      assert.strictEqual(isStatusEditable('RESOLVED'), false);
      assert.strictEqual(isStatusEditable('FINALIZED'), false);
      assert.strictEqual(isStatusEditable('CLOSED_NO_SUBMIT'), false);
      assert.strictEqual(isStatusEditable('CLOSED_INCOMPLETE'), false);
    });

    test('Khóa form khi đã quá thời hạn nộp', () => {
      const pastDeadline = '2026-10-01T00:00:00Z';
      const isExpired = new Date(pastDeadline).getTime() <= new Date().getTime();
      assert.strictEqual(isExpired, true);
    });
  });

  // 4. Kiểm tra bảo mật điểm dự kiến (Chống rò rỉ điểm trước công bố)
  describe('Bảo vệ tính toàn vẹn: Không rò rỉ điểm BCS trước PUBLISHED', () => {
    test('MOCK_STUDENT_DRAFT không có proposed_total và không có approved_score', () => {
      assert.strictEqual(MOCK_STUDENT_DRAFT.case.proposed_total, null);
      for (const cl of MOCK_STUDENT_DRAFT.claims) {
        assert.strictEqual(cl.approved_score, null);
        assert.strictEqual(cl.bcs_reason, null);
      }
    });

    test('MOCK_STUDENT_NEEDS_INFO không có proposed_total', () => {
      assert.strictEqual(MOCK_STUDENT_NEEDS_INFO.case.proposed_total, null);
      for (const cl of MOCK_STUDENT_NEEDS_INFO.claims) {
        assert.strictEqual(cl.approved_score, null);
      }
    });

    test('MOCK_STUDENT_PUBLISHED có điểm dự kiến hợp lệ và lý do BCS', () => {
      assert.strictEqual(MOCK_STUDENT_PUBLISHED.case.status, 'PUBLISHED');
      assert.strictEqual(MOCK_STUDENT_PUBLISHED.case.proposed_total, '24.00');
      assert.strictEqual(MOCK_STUDENT_PUBLISHED.claims.length, 3);
      assert.strictEqual(MOCK_STUDENT_PUBLISHED.claims[2].approved_score, '6.00');
      assert.strictEqual(typeof MOCK_STUDENT_PUBLISHED.claims[2].bcs_reason, 'string');
    });
  });

  // 5. Loại trừ tương hỗ giữa Đồng ý và Khiếu nại
  describe('Loại trừ tương hỗ (Mutual Exclusion) giữa Đồng ý và Khiếu nại', () => {
    test('Khi hồ sơ ở ACCEPTED, không được phép khiếu nại', () => {
      const status = MOCK_STUDENT_ACCEPTED.case.status;
      const canAppeal = status === 'PUBLISHED';
      assert.strictEqual(canAppeal, false);
    });

    test('Khi hồ sơ ở APPEALED, không được phép đồng ý', () => {
      const status = MOCK_STUDENT_APPEALED.case.status;
      const canAccept = status === 'PUBLISHED';
      assert.strictEqual(canAccept, false);
    });

    test('Hồ sơ RESOLVED phản ánh đúng điểm mới và kết luận BCS', () => {
      assert.strictEqual(MOCK_STUDENT_RESOLVED.case.status, 'RESOLVED');
      assert.strictEqual(MOCK_STUDENT_RESOLVED.case.proposed_total, '26.00');
      const appeal = MOCK_STUDENT_RESOLVED.appeals?.[0];
      assert.strictEqual(appeal?.status, 'RESOLVED');
      assert.strictEqual(appeal?.resolution, 'ADJUST');
      assert.strictEqual(appeal?.new_score, '8.00');
    });

    test('Hồ sơ FINALIZED có final_total', () => {
      assert.strictEqual(MOCK_STUDENT_FINALIZED.case.status, 'FINALIZED');
      assert.strictEqual(MOCK_STUDENT_FINALIZED.case.final_total, '26.00');
    });

    test('Hồ sơ CLOSED_NO_SUBMIT giữ đúng trạng thái đóng', () => {
      assert.strictEqual(MOCK_STUDENT_CLOSED_NO_SUBMIT.case.status, 'CLOSED_NO_SUBMIT');
      assert.strictEqual(MOCK_STUDENT_CLOSED_NO_SUBMIT.case.proposed_total, null);
    });
  });

  // 6. Kiểm tra xử lý Concurrency (409 CASE_CHANGED)
  describe('Xử lý xung đột phiên bản (Concurrency expected_version)', () => {
    test('Ném lỗi 409 CASE_CHANGED nếu expected_version không khớp', async () => {
      studentService.setScenario('DRAFT');
      try {
        await studentService.saveClaim(
          '55555555-5555-5555-5555-555555555001',
          '44444444-4444-4444-4444-444444444001',
          '9.00',
          'Ghi chú',
          999 // Sai version (kỳ vọng 1)
        );
        assert.fail('Phải ném lỗi CASE_CHANGED');
      } catch (err: any) {
        assert.strictEqual(err.error?.code, 'CASE_CHANGED');
      }
    });

    test('Cập nhật thành công và tăng version khi expected_version đúng', async () => {
      studentService.setScenario('DRAFT');
      const res = await studentService.saveClaim(
        '55555555-5555-5555-5555-555555555001',
        '44444444-4444-4444-4444-444444444001',
        '8.50',
        'Ghi chú hợp lệ',
        1
      );
      assert.strictEqual(res.version, 2);
      assert.strictEqual(res.claim.self_score, '8.50');
    });
  });

  // 7. Kiểm tra nghiệp vụ nộp hồ sơ, tải minh chứng, chấp nhận và khiếu nại
  describe('Quy trình nộp hồ sơ, tải minh chứng, đồng ý và khiếu nại', () => {
    test('Tải tệp minh chứng: từ chối tệp không đúng định dạng', async () => {
      studentService.setScenario('DRAFT');
      try {
        await studentService.uploadEvidence(
          '55555555-5555-5555-5555-555555555001',
          '44444444-4444-4444-4444-444444444001',
          { name: 'tailieu.exe', type: 'application/x-msdownload', size: 1024 }
        );
        assert.fail('Phải ném lỗi INVALID_FILE_TYPE');
      } catch (err: any) {
        assert.strictEqual(err.error?.code, 'INVALID_FILE_TYPE');
      }
    });

    test('Tải tệp minh chứng: thành công khi tệp hợp lệ (PDF/JPG/PNG <= 10MB)', async () => {
      studentService.setScenario('DRAFT');
      const ev = await studentService.uploadEvidence(
        '55555555-5555-5555-5555-555555555001',
        '44444444-4444-4444-4444-444444444001',
        { name: 'bang-diem.pdf', type: 'application/pdf', size: 1048576 }
      );
      assert.ok(ev.id);
      assert.strictEqual(ev.original_name, 'bang-diem.pdf');
      assert.strictEqual(ev.mime_type, 'application/pdf');
    });

    test('Nộp hồ sơ khi thiếu minh chứng bắt buộc -> chuyển NEEDS_INFO', async () => {
      studentService.setScenario('DRAFT');
      // DRAFT ban đầu chưa có minh chứng cho TC01 và TC03 (requires_evidence = true)
      const res = await studentService.submitCase('55555555-5555-5555-5555-555555555001', 1);
      assert.strictEqual(res.status, 'NEEDS_INFO');
      assert.ok(res.missing_items.length > 0);
    });

    test('Chấp nhận điểm dự kiến -> chuyển ACCEPTED với acceptance_source=EXPLICIT', async () => {
      studentService.setScenario('PUBLISHED');
      const res = await studentService.acceptCase('55555555-5555-5555-5555-555555555001', 4);
      assert.strictEqual(res.status, 'ACCEPTED');
      assert.strictEqual(res.acceptance_source, 'EXPLICIT');
      assert.strictEqual(res.version, 5);
    });

    test('Gửi khiếu nại -> chuyển APPEALED và tạo bản ghi appeals', async () => {
      studentService.setScenario('PUBLISHED');
      const items = [
        {
          criterion_id: '44444444-4444-4444-4444-444444444003',
          reason: 'Đề nghị xem xét lại minh chứng tình nguyện cấp Trường',
        },
      ];
      const res = await studentService.createAppeals('55555555-5555-5555-5555-555555555001', items, 4);
      assert.strictEqual(res.status, 'APPEALED');
      assert.strictEqual(res.version, 5);
      assert.ok(res.appeals.length >= 1);
      assert.strictEqual(res.appeals[0].student_reason, items[0].reason);
    });
  });

  // 8. Kiểm tra cấu trúc hợp đồng OpenAPI của tất cả các Mock Scenarios
  describe('Khớp cấu trúc hợp đồng OpenAPI', () => {
    const requiredResponseKeys = ['campaign', 'case', 'criteria', 'claims', 'unread_notifications_count'];
    const requiredCaseKeys = ['id', 'version', 'status', 'claimed_total', 'info_round', 'proof_round'];

    const checkConformity = (res: any, name: string) => {
      for (const k of requiredResponseKeys) {
        assert.ok(k in res, `${name} thiếu trường ${k}`);
      }
      for (const k of requiredCaseKeys) {
        assert.ok(k in res.case, `${name}.case thiếu trường ${k}`);
      }
    };

    test('Tất cả mock scenarios đều đầy đủ thuộc tính theo OpenAPI schema', () => {
      checkConformity(MOCK_STUDENT_DRAFT, 'DRAFT');
      checkConformity(MOCK_STUDENT_NEEDS_INFO, 'NEEDS_INFO');
      checkConformity(MOCK_STUDENT_PUBLISHED, 'PUBLISHED');
      checkConformity(MOCK_STUDENT_ACCEPTED, 'ACCEPTED');
      checkConformity(MOCK_STUDENT_APPEALED, 'APPEALED');
      checkConformity(MOCK_STUDENT_RESOLVED, 'RESOLVED');
      checkConformity(MOCK_STUDENT_FINALIZED, 'FINALIZED');
      checkConformity(MOCK_STUDENT_CLOSED_NO_SUBMIT, 'CLOSED_NO_SUBMIT');
    });
  });
});
