import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { Link } from 'react-router-dom';
import { StudentCurrentResponse } from '../../api/types';
import { studentService } from '../../components/student/studentService';
import { StudentScenarioBar } from '../../components/student/StudentScenarioBar';
import '../../components/student/studentStyles.css';
import {
  FileQuestion,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowLeft,
  Send,
  Scale,
  Award,
  RefreshCw,
} from 'lucide-react';

export const StudentAppeal: React.FC = () => {
  const [data, setData] = useState<StudentCurrentResponse | null>(null);
  const [selectedCriteria, setSelectedCriteria] = useState<Record<string, boolean>>({});
  const [reasonsMap, setReasonsMap] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'danger' | 'info'; text: string } | null>(null);
  const [now, setNow] = useState(Date.now());

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setValidationError(null);
      setFeedbackMessage(null);
      const res = await studentService.getCurrent();
      setData(res);

      // Mặc định chọn tiêu chí có điểm duyệt khác điểm tự khai
      const initSelected: Record<string, boolean> = {};
      const initReasons: Record<string, string> = {};

      for (const crit of res.criteria) {
        const claim = res.claims.find((c) => c.criterion_id === crit.id);
        if (claim && claim.approved_score !== null && claim.self_score !== null) {
          if (parseFloat(claim.approved_score) !== parseFloat(claim.self_score)) {
            initSelected[crit.id] = true;
          }
        }
      }
      setSelectedCriteria(initSelected);
      setReasonsMap(initReasons);
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      setFeedbackMessage({
        type: 'danger',
        text: errObj?.error?.message || 'Không thể tải thông tin khiếu nại.',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const deadline = data?.case.appeal_deadline_at;
    if (data?.case.status !== 'PUBLISHED' || !deadline) return;
    const remaining = new Date(deadline).getTime() - Date.now();
    if (remaining <= 0) {
      setNow(Date.now());
      return;
    }
    const timer = window.setTimeout(() => {
      setNow(Date.now());
      setShowConfirm(false);
      void loadData();
    }, Math.min(remaining + 50, 2_147_483_647));
    return () => window.clearTimeout(timer);
  }, [data?.case.status, data?.case.appeal_deadline_at, loadData]);

  // Kiểm tra thời hạn khiếu nại
  const isAppealExpired = useMemo(() => {
    if (!data?.case.appeal_deadline_at) return false;
    return new Date(data.case.appeal_deadline_at).getTime() <= now;
  }, [data, now]);

  // Kiểm tra có đang được phép gửi khiếu nại mới không
  const canSubmitAppeal = useMemo(() => {
    if (!data) return false;
    return data.case.status === 'PUBLISHED' && !isAppealExpired;
  }, [data, isAppealExpired]);

  // Đã từng gửi khiếu nại
  const hasExistingAppeals = useMemo(() => {
    if (!data) return false;
    return (
      data.case.status === 'APPEALED' ||
      data.case.status === 'RESOLVED' ||
      (data.appeals && data.appeals.length > 0)
    );
  }, [data]);

  const handleToggleCriterion = (criterionId: string) => {
    setSelectedCriteria((prev) => ({
      ...prev,
      [criterionId]: !prev[criterionId],
    }));
  };

  const handleReasonChange = (criterionId: string, reason: string) => {
    setReasonsMap((prev) => ({
      ...prev,
      [criterionId]: reason,
    }));
  };

  const handlePreSubmit = () => {
    if (!canSubmitAppeal) {
      setValidationError('Đã hết hạn hoặc hồ sơ chưa được công bố. Hãy tải lại để xem trạng thái mới nhất.');
      return;
    }
    setValidationError(null);

    // 1. Kiểm tra ít nhất 1 tiêu chí được chọn
    const selectedIds = Object.keys(selectedCriteria).filter((id) => selectedCriteria[id]);
    if (selectedIds.length === 0) {
      setValidationError('Vui lòng chọn ít nhất một tiêu chí để khiếu nại.');
      return;
    }

    // 2. Kiểm tra lý do của từng tiêu chí đã chọn
    for (const id of selectedIds) {
      const reason = reasonsMap[id];
      if (!reason || reason.trim() === '') {
        const crit = data?.criteria.find((c) => c.id === id);
        setValidationError(`Vui lòng nhập lý do khiếu nại chi tiết cho tiêu chí ${crit?.code || ''}.`);
        return;
      }
    }

    setShowConfirm(true);
  };

  const handleConfirmSubmit = async () => {
    if (!data || !canSubmitAppeal || isSubmitting) return;
    setShowConfirm(false);
    setIsSubmitting(true);
    setValidationError(null);
    setFeedbackMessage(null);

    const selectedIds = Object.keys(selectedCriteria).filter((id) => selectedCriteria[id]);
    const items = selectedIds.map((id) => ({
      criterion_id: id,
      reason: reasonsMap[id].trim(),
    }));

    try {
      await studentService.createAppeals(data.case.id, items, data.case.version);
      const updated = await studentService.getCurrent();
      setData(updated);
      setFeedbackMessage({
        type: 'success',
        text: 'Gửi khiếu nại thành công! Ban cán sự sẽ xem xét và phản hồi trong thời gian sớm nhất.',
      });
    } catch (err: unknown) {
      const errObj = err as { error?: { code?: string; message?: string } };
      if (errObj?.error?.code === 'CASE_CHANGED') {
        setFeedbackMessage({
          type: 'danger',
          text: 'Hồ sơ đã thay đổi từ trước. Vui lòng tải lại dữ liệu.',
        });
      } else if (errObj?.error?.code === 'DEADLINE_EXPIRED') {
        setNow(Date.now());
        setFeedbackMessage({
          type: 'info',
          text: 'Đã hết hạn khiếu nại. Hãy tải lại kết quả để xem trạng thái ghi nhận mới nhất.',
        });
      } else {
        setFeedbackMessage({
          type: 'danger',
          text: errObj?.error?.message || 'Có lỗi xảy ra khi gửi khiếu nại.',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container" style={{ padding: '1.5rem' }}>
        <StudentScenarioBar onScenarioChange={loadData} />
        <div className="card" style={{ padding: '2rem' }}>
          <div className="skeleton-line" style={{ width: '40%', height: '1.5rem' }} />
          <div className="skeleton-line" style={{ width: '70%', height: '1rem' }} />
          <div style={{ marginTop: '2rem' }}>
            <div className="skeleton-line" style={{ height: '5rem' }} />
            <div className="skeleton-line" style={{ height: '5rem' }} />
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container" style={{ padding: '1.5rem' }}>
        <StudentScenarioBar onScenarioChange={loadData} />
        <div className="student-alert student-alert-danger" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '1rem' }}>
          <AlertTriangle size={20} />
          <div>
            <strong>Lỗi tải dữ liệu:</strong> {feedbackMessage?.text || 'Không thể tải thông tin khiếu nại.'}
            <div style={{ marginTop: '0.75rem' }}>
              <button className="btn btn-outline" onClick={loadData}>
                <RefreshCw size={14} style={{ marginRight: '0.5rem' }} /> Thử lại
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const { campaign, case: studentCase, criteria, claims, appeals } = data;

  return (
    <div>
      {/* 1. Thanh kịch bản hỗ trợ kiểm thử */}
      <StudentScenarioBar onScenarioChange={loadData} />

      {/* 2. Tiêu đề trang */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <Link to="/student/result" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem' }}>
              <ArrowLeft size={16} /> Quay lại kết quả
            </Link>
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
            Khiếu nại Điểm Đánh giá Rèn luyện
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            {campaign.title}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <StatusBadge status={studentCase.status} />
          {studentCase.appeal_deadline_at && (
            <Deadline isoString={studentCase.appeal_deadline_at} label="Hạn phản hồi" />
          )}
        </div>
      </div>

      {/* 3. Phản hồi hành động */}
      {feedbackMessage && (
        <div className={`student-alert student-alert-${feedbackMessage.type}`}>
          {feedbackMessage.type === 'success' && <CheckCircle2 size={18} style={{ flexShrink: 0 }} />}
          {feedbackMessage.type === 'danger' && <AlertTriangle size={18} style={{ flexShrink: 0 }} />}
          <div style={{ flex: 1 }}>{feedbackMessage.text}</div>
        </div>
      )}

      {/* 4. TRƯỜNG HỢP: ĐÃ CÓ KHIẾU NẠI (Hiển thị tiến độ và kết quả) */}
      {hasExistingAppeals ? (
        <div>
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <Scale size={20} color="#1e40af" />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                {studentCase.status === 'RESOLVED'
                  ? 'Kết quả giải quyết khiếu nại từ Ban cán sự'
                  : 'Tiến độ xử lý khiếu nại'}
              </h3>
            </div>

            <p style={{ fontSize: '0.875rem', color: '#475569', marginBottom: '1.25rem' }}>
              Sinh viên chỉ được gửi khiếu nại một lần trong đợt đánh giá. Dưới đây là danh sách các tiêu chí
              bạn đã khiếu nại và phản hồi từ Ban cán sự lớp:
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {appeals?.map((appeal) => {
                const crit = criteria.find((c) => c.id === appeal.criterion_id);
                const claim = claims.find((c) => c.criterion_id === appeal.criterion_id);

                return (
                  <div
                    key={appeal.id}
                    style={{
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      padding: '1.25rem',
                      backgroundColor: appeal.status === 'RESOLVED' ? '#fafbfc' : '#ffffff',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
                      <div>
                        <span style={{ fontWeight: 700, color: '#1e40af', fontSize: '1rem' }}>
                          {crit?.code}: {crit?.title}
                        </span>
                        <div style={{ fontSize: '0.8125rem', color: '#64748b', marginTop: '0.15rem' }}>
                          Tự chấm: <strong>{claim?.self_score ?? '—'} đ</strong> | Điểm dự kiến ban đầu: <strong>{claim?.approved_score ?? '—'} đ</strong>
                        </div>
                      </div>

                      <span
                        className={`badge ${appeal.status === 'RESOLVED' ? 'badge-success' : 'badge-warning'}`}
                      >
                        {appeal.status === 'RESOLVED' ? 'Đã giải quyết' : 'Đang chờ BCS xử lý'}
                      </span>
                    </div>

                    {/* Lý do sinh viên gửi */}
                    <div style={{ backgroundColor: '#f8fafc', padding: '0.75rem 1rem', borderRadius: '6px', marginBottom: '0.75rem' }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                        Lý do khiếu nại của bạn:
                      </div>
                      <div style={{ fontSize: '0.875rem', color: '#0f172a', marginTop: '0.25rem' }}>
                        {appeal.student_reason}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.35rem' }}>
                        Thời điểm gửi: {new Intl.DateTimeFormat('vi-VN', {
                          timeZone: 'Asia/Ho_Chi_Minh',
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        }).format(new Date(appeal.submitted_at))}
                      </div>
                    </div>

                    {/* Kết quả giải quyết của BCS nếu đã xong */}
                    {appeal.status === 'RESOLVED' && (
                      <div
                        style={{
                          backgroundColor: appeal.resolution === 'ADJUST' ? '#ecfdf5' : '#eff6ff',
                          border: `1px solid ${appeal.resolution === 'ADJUST' ? '#a7f3d0' : '#bfdbfe'}`,
                          padding: '0.75rem 1rem',
                          borderRadius: '6px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, fontSize: '0.875rem', color: appeal.resolution === 'ADJUST' ? '#065f46' : '#1e40af' }}>
                          <Award size={16} />
                          <span>
                            Kết luận của BCS: {appeal.resolution === 'ADJUST' ? 'CHẤP THUẬN (ĐIỀU CHỈNH ĐIỂM)' : 'GIỮ NGUYÊN ĐIỂM'}
                          </span>
                        </div>
                        {appeal.resolution === 'ADJUST' && appeal.new_score && (
                          <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#065f46', marginTop: '0.25rem' }}>
                            Điểm sau điều chỉnh: {appeal.new_score} đ
                          </div>
                        )}
                        <div style={{ fontSize: '0.875rem', color: '#334155', marginTop: '0.35rem' }}>
                          Lý do: {appeal.bcs_reason || '(Không có ghi chú thêm)'}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
              <Link to="/student/result" className="btn btn-primary">
                Xem lại bảng điểm đầy đủ
              </Link>
            </div>
          </div>
        </div>
      ) : !canSubmitAppeal ? (
        /* 5. TRƯỜNG HỢP: CHƯA ĐỦ ĐIỀU KIỆN KHIẾU NẠI HOẶC QUÁ HẠN */
        <div className="card" style={{ padding: '2.5rem 1.5rem', textAlign: 'center' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: '#f1f5f9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.25rem auto',
            }}
          >
            <Clock size={32} color="#64748b" />
          </div>

          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b' }}>
            Chưa mở hoặc đã kết thúc thời gian khiếu nại
          </h3>
          <p
            style={{
              fontSize: '0.9375rem',
              color: '#64748b',
              maxWidth: '600px',
              margin: '0.75rem auto 1.5rem auto',
              lineHeight: 1.6,
            }}
          >
            {isAppealExpired
              ? 'Đã hết thời hạn khiếu nại điểm đánh giá cho đợt rèn luyện này. Hệ thống đã tự động ghi nhận kết quả.'
              : studentCase.status === 'ACCEPTED' || studentCase.status === 'ACCEPTED_AUTO'
              ? 'Bạn đã xác nhận đồng ý với điểm đánh giá dự kiến hoặc hệ thống đã tự động chấp thuận do quá hạn.'
              : `Chức năng khiếu nại chỉ khả dụng khi điểm dự kiến đã được công bố (PUBLISHED). Hiện tại hồ sơ của bạn đang ở trạng thái "${studentCase.status}".`}
          </p>

          <Link to="/student" className="btn btn-secondary">
            Quay lại bảng tin sinh viên
          </Link>
        </div>
      ) : (
        /* 6. TRƯỜNG HỢP: FORM GỬI KHIẾU NẠI (PUBLISHED & TRONG HẠN) */
        <div className="card">
          <div style={{ marginBottom: '1.25rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '1rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#0f172a' }}>
              Chọn tiêu chí cần khiếu nại và nhập lý do
            </h3>
            <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: '0.25rem' }}>
              Vui lòng nêu rõ lý do tại sao điểm duyệt của BCS chưa chính xác và căn cứ vào minh chứng nào đã nộp.
            </p>
          </div>

          {validationError && (
            <div className="student-alert student-alert-danger" style={{ marginBottom: '1rem' }}>
              <AlertTriangle size={18} style={{ flexShrink: 0 }} />
              <div>{validationError}</div>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {criteria.map((crit) => {
              const claim = claims.find((c) => c.criterion_id === crit.id);
              const isSelected = !!selectedCriteria[crit.id];
              const selfScore = claim?.self_score ?? '0.00';
              const approvedScore = claim?.approved_score ?? '0.00';
              const isDifferent = parseFloat(selfScore) !== parseFloat(approvedScore);

              return (
                <div
                  key={crit.id}
                  style={{
                    border: `1px solid ${isSelected ? '#3b82f6' : '#e2e8f0'}`,
                    borderRadius: '8px',
                    padding: '1rem 1.25rem',
                    backgroundColor: isSelected ? '#f8faff' : '#ffffff',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                    <input
                      type="checkbox"
                      id={`check-${crit.id}`}
                      checked={isSelected}
                      onChange={() => handleToggleCriterion(crit.id)}
                      style={{
                        width: '18px',
                        height: '18px',
                        marginTop: '3px',
                        cursor: 'pointer',
                        accentColor: '#1e40af',
                      }}
                    />

                    <div style={{ flex: 1 }}>
                      <label
                        htmlFor={`check-${crit.id}`}
                        style={{
                          fontWeight: 600,
                          fontSize: '1rem',
                          color: '#1e40af',
                          cursor: 'pointer',
                          display: 'inline-block',
                        }}
                      >
                        {crit.code}: {crit.title}
                      </label>

                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '1rem',
                          fontSize: '0.85rem',
                          color: '#475569',
                          marginTop: '0.25rem',
                          flexWrap: 'wrap',
                        }}
                      >
                        <span>
                          Tự chấm: <strong>{selfScore} đ</strong>
                        </span>
                        <span>
                          BCS duyệt: <strong style={{ color: isDifferent ? '#dc2626' : '#15803d' }}>{approvedScore} đ</strong>
                        </span>
                        {isDifferent && (
                          <span className="score-difference-alert" style={{ margin: 0 }}>
                            Chênh lệch: {(parseFloat(approvedScore) - parseFloat(selfScore)).toFixed(2)} đ
                          </span>
                        )}
                      </div>

                      {claim?.bcs_reason && (
                        <div style={{ fontSize: '0.8rem', color: '#64748b', fontStyle: 'italic', marginTop: '0.25rem' }}>
                          Lý do duyệt của BCS: "{claim.bcs_reason}"
                        </div>
                      )}

                      {/* Ô nhập lý do nếu tiêu chí được chọn */}
                      {isSelected && (
                        <div style={{ marginTop: '0.75rem' }}>
                          <label
                            htmlFor={`reason-${crit.id}`}
                            className="form-label"
                            style={{ fontWeight: 600, color: '#1e40af' }}
                          >
                            Lý do đề nghị xem xét lại *
                          </label>
                          <textarea
                            id={`reason-${crit.id}`}
                            className="form-textarea"
                            rows={3}
                            placeholder="Trình bày rõ hoạt động, minh chứng đính kèm hoặc quy định làm cơ sở đề nghị tính lại điểm..."
                            value={reasonsMap[crit.id] ?? ''}
                            onChange={(e) => handleReasonChange(crit.id, e.target.value)}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '1.5rem',
              paddingTop: '1rem',
              borderTop: '1px solid #e2e8f0',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div style={{ fontSize: '0.8125rem', color: '#64748b' }}>
              Lưu ý: Chỉ gửi khiếu nại cho các tiêu chí bạn thấy thực sự chưa chính xác.
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <Link to="/student/result" className="btn btn-secondary">
                Hủy bỏ
              </Link>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handlePreSubmit}
                disabled={isSubmitting}
              >
                <Send size={16} />
                <span>{isSubmitting ? 'Đang gửi...' : 'Gửi khiếu nại'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. Hộp thoại xác nhận gửi khiếu nại */}
      <ConfirmDialog
        isOpen={showConfirm}
        title="Xác nhận gửi khiếu nại điểm rèn luyện"
        message="Sinh viên chỉ được gửi khiếu nại một lần trong đợt đánh giá. Sau khi gửi, bạn không thể chỉnh sửa lại nội dung khiếu nại. Ban cán sự sẽ nhận và giải quyết trong phiên họp bình xét tiếp theo. Bạn có chắc chắn muốn gửi?"
        confirmLabel="Đồng ý gửi"
        cancelLabel="Kiểm tra lại"
        isDanger={false}
        isLoading={isSubmitting}
        onConfirm={handleConfirmSubmit}
        onCancel={() => setShowConfirm(false)}
      />
    </div>
  );
};
