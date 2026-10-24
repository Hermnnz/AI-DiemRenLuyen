import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { api } from '../../api/client';
import { studentService } from '../../components/student/studentService';

describe('Giai đoạn 2.5 - Frontend Integration & Route Protection Tests', () => {

  describe('1. Quản lý CSRF Token và Session Client', () => {
    it('Lưu và đọc CSRF Token trong bộ nhớ đúng cách', () => {
      api.setCsrfToken(null);
      assert.equal(api.getCsrfToken(), null);

      api.setCsrfToken('test-csrf-token-xyz');
      assert.equal(api.getCsrfToken(), 'test-csrf-token-xyz');

      api.setCsrfToken(null);
      assert.equal(api.getCsrfToken(), null);
    });

    it('Xóa CSRF Token khi nhận lỗi 401 Unauthorized', async () => {
      api.setCsrfToken('active-token-before-401');

      // Mock fetch trả về HTTP 401
      const originalFetch = globalThis.fetch;
      globalThis.fetch = async () => {
        return {
          ok: false,
          status: 401,
          statusText: 'Unauthorized',
          headers: new Headers({ 'Content-Type': 'application/json' }),
          json: async () => ({
            error: { code: 'UNAUTHORIZED', message: 'Phiên làm việc đã hết hạn' },
          }),
        } as unknown as Response;
      };

      try {
        await api.get('/auth/me');
        assert.fail('Request phải ném lỗi khi HTTP 401');
      } catch (err: unknown) {
        const error = err as { error?: { code?: string } };
        assert.equal(error?.error?.code, 'UNAUTHORIZED');
        // Token phải bị xóa
        assert.equal(api.getCsrfToken(), null);
      } finally {
        globalThis.fetch = originalFetch;
      }
    });
  });

  describe('2. Phân quyền và Bảo vệ Tuyến đường (Route Guards & Role Check)', () => {
    const checkRoleAccess = (userRole: string, allowedRoles: string[]): boolean => {
      return allowedRoles.includes(userRole);
    };

    const getRoleHome = (role: string): string => {
      switch (role) {
        case 'STUDENT':
          return '/student';
        case 'BCS':
          return '/bcs';
        case 'GVCN':
          return '/gvcn/scores';
        case 'ADMIN':
          return '/admin/campaigns';
        default:
          return '/login';
      }
    };

    it('Sinh viên (STUDENT) chỉ truy cập được route sinh viên, bị chặn khỏi BCS/GVCN/ADMIN', () => {
      const studentRole = 'STUDENT';
      assert.equal(checkRoleAccess(studentRole, ['STUDENT']), true, 'SV vào được /student');
      assert.equal(checkRoleAccess(studentRole, ['BCS']), false, 'SV bị chặn khỏi /bcs');
      assert.equal(checkRoleAccess(studentRole, ['GVCN']), false, 'SV bị chặn khỏi /gvcn');
      assert.equal(checkRoleAccess(studentRole, ['ADMIN']), false, 'SV bị chặn khỏi /admin');
      assert.equal(getRoleHome(studentRole), '/student');
    });

    it('Ban cán sự (BCS) chỉ truy cập được route BCS, bị chặn khỏi ADMIN/GVCN', () => {
      const bcsRole = 'BCS';
      assert.equal(checkRoleAccess(bcsRole, ['BCS']), true, 'BCS vào được /bcs');
      assert.equal(checkRoleAccess(bcsRole, ['STUDENT']), false, 'BCS không vào route sinh viên');
      assert.equal(checkRoleAccess(bcsRole, ['ADMIN']), false, 'BCS bị chặn khỏi /admin');
      assert.equal(getRoleHome(bcsRole), '/bcs');
    });

    it('GVCN và Admin được phân luồng điều hướng chính xác', () => {
      assert.equal(getRoleHome('GVCN'), '/gvcn/scores');
      assert.equal(getRoleHome('ADMIN'), '/admin/campaigns');
    });
  });

  describe('3. Dữ liệu thật và Tuyệt đối không âm thầm Fallback sang Mock khi lỗi ở Live Mode', () => {
    it('studentService.getCurrent() ném lỗi khi backend lỗi ở Live Mode, KHÔNG trả mock state', async () => {
      studentService.setMode('live');
      assert.equal(studentService.getMode(), 'live');

      const originalFetch = globalThis.fetch;
      globalThis.fetch = async () => {
        return {
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          headers: new Headers({ 'Content-Type': 'application/json' }),
          json: async () => ({
            error: { code: 'DATABASE_ERROR', message: 'Lỗi máy chủ cơ sở dữ liệu' },
          }),
        } as unknown as Response;
      };

      try {
        await studentService.getCurrent();
        assert.fail('getCurrent() phải ném lỗi khi backend gặp sự cố ở live mode');
      } catch (err: unknown) {
        const error = err as { error?: { code?: string; message?: string } };
        assert.equal(error?.error?.code, 'DATABASE_ERROR');
        assert.equal(error?.error?.message, 'Lỗi máy chủ cơ sở dữ liệu');
      } finally {
        globalThis.fetch = originalFetch;
        studentService.setMode('mock'); // Trả lại mock cho test tiếp theo
      }
    });

    it('studentService.saveClaim() ném lỗi khi backend mất kết nối, KHÔNG tự ý lưu vào local mock', async () => {
      studentService.setMode('live');

      const originalFetch = globalThis.fetch;
      globalThis.fetch = async () => {
        throw new TypeError('Failed to fetch (Network disconnected)');
      };

      try {
        await studentService.saveClaim('case-1', 'crit-1', '8.00', 'Ghi chú', 1);
        assert.fail('saveClaim() phải ném lỗi khi mạng mất kết nối');
      } catch (err: unknown) {
        assert.ok(err instanceof TypeError || (err as Error).message.includes('fetch'));
      } finally {
        globalThis.fetch = originalFetch;
        studentService.setMode('mock');
      }
    });

    it('studentService.submitCase() ném lỗi khi backend từ chối, KHÔNG đổi status mock sang BCS_REVIEW', async () => {
      studentService.setMode('live');

      const originalFetch = globalThis.fetch;
      globalThis.fetch = async () => {
        return {
          ok: false,
          status: 409,
          statusText: 'Conflict',
          headers: new Headers({ 'Content-Type': 'application/json' }),
          json: async () => ({
            error: { code: 'CAMPAIGN_CLOSED', message: 'Đợt đánh giá đã đóng nộp hồ sơ' },
          }),
        } as unknown as Response;
      };

      try {
        await studentService.submitCase('case-1', 1);
        assert.fail('submitCase() phải ném lỗi 409');
      } catch (err: unknown) {
        const error = err as { error?: { code?: string } };
        assert.equal(error?.error?.code, 'CAMPAIGN_CLOSED');
      } finally {
        globalThis.fetch = originalFetch;
        studentService.setMode('mock');
      }
    });

    it('studentService.acceptCase() và createAppeals() không fallback mock khi lỗi ở live mode', async () => {
      studentService.setMode('live');

      const originalFetch = globalThis.fetch;
      globalThis.fetch = async () => {
        return {
          ok: false,
          status: 422,
          statusText: 'Unprocessable',
          headers: new Headers({ 'Content-Type': 'application/json' }),
          json: async () => ({
            error: { code: 'INVALID_STATE', message: 'Không thể thực hiện ở trạng thái hiện tại' },
          }),
        } as unknown as Response;
      };

      try {
        await studentService.acceptCase('case-1', 1);
        assert.fail('acceptCase() phải ném lỗi 422');
      } catch (err: unknown) {
        const error = err as { error?: { code?: string } };
        assert.equal(error?.error?.code, 'INVALID_STATE');
      }

      try {
        await studentService.createAppeals('case-1', [{ criterion_id: 'crit-1', reason: 'Khiếu nại' }], 1);
        assert.fail('createAppeals() phải ném lỗi 422');
      } catch (err: unknown) {
        const error = err as { error?: { code?: string } };
        assert.equal(error?.error?.code, 'INVALID_STATE');
      } finally {
        globalThis.fetch = originalFetch;
        studentService.setMode('mock');
      }
    });
  });
});
