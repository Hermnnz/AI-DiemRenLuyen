import { api } from '../../api/client';
import { BcsCaseListItem } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';

export const EMPTY_PRIORITY_MESSAGE = 'Không có hồ sơ cần kiểm tra ngay.';
export const PARTIAL_ERROR_MESSAGE = 'Chưa thể tải hồ sơ ưu tiên. Bạn vẫn có thể mở hàng chờ để tiếp tục.';
export const PRIORITY_QUEUE_ROUTE = '/bcs/cases?status=BCS_REVIEW';

export interface PriorityCaseFetchResult {
  priorityCase: BcsCaseListItem | null;
  error: string | null;
}

/**
 * Lấy hồ sơ ưu tiên xử lý (trạng thái BCS_REVIEW, bản ghi đầu tiên) từ API thật hoặc mock store trong demo mode.
 */
export async function fetchPriorityCase(
  campaignId: string,
  isDemoMode: boolean
): Promise<PriorityCaseFetchResult> {
  if (isDemoMode) {
    const res = staffStore.getCases('BCS_REVIEW', '', 1, 1);
    return {
      priorityCase: res.items.length > 0 ? res.items[0] : null,
      error: null,
    };
  }

  try {
    const casesRes = await api.get<{
      total: number;
      page: number;
      page_size: number;
      items: BcsCaseListItem[];
    }>(`/bcs/campaigns/${campaignId}/cases?status=BCS_REVIEW&page=1&page_size=1`);

    if (casesRes?.items && casesRes.items.length > 0) {
      return { priorityCase: casesRes.items[0], error: null };
    }
    return { priorityCase: null, error: null };
  } catch (err: unknown) {
    const errObj = err as { error?: { message?: string }; message?: string };
    const msg =
      errObj?.error?.message ||
      errObj?.message ||
      PARTIAL_ERROR_MESSAGE;
    return { priorityCase: null, error: msg };
  }
}

/**
 * Tạo dữ liệu hiển thị động cho thẻ ưu tiên kiểm tra hồ sơ.
 */
export function formatPriorityTask(priorityCase: BcsCaseListItem) {
  return {
    title: `Kiểm tra minh chứng hồ sơ ${priorityCase.student_code} · ${priorityCase.student_name}`,
    subtitle: `Hồ sơ đang ở trạng thái ${priorityCase.status}, sinh viên đã nộp hồ sơ đánh giá`,
    route: `/bcs/cases/${priorityCase.id}`,
  };
}
