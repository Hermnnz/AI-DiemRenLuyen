import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { StudentCurrentResponse, Claim } from '../../api/types';
import { studentService } from '../../components/student/studentService';
import { CriterionCard } from '../../components/student/CriterionCard';
import { StudentScenarioBar } from '../../components/student/StudentScenarioBar';
import '../../components/student/studentStyles.css';
import {
  Save,
  Send,
  AlertTriangle,
  CheckCircle2,
  Lock,
  RefreshCw,
  Info,
  ArrowLeft,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const StudentSubmission: React.FC = () => {
  const [data, setData] = useState<StudentCurrentResponse | null>(null);
  const [claimsMap, setClaimsMap] = useState<Record<string, { self_score: string | null; student_note: string | null }>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'danger' | 'info'; text: string } | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setValidationError(null);
      setFeedbackMessage(null);
      const res = await studentService.getCurrent();
      setData(res);

      // Khởi tạo map claims để theo dõi chỉnh sửa
      const initMap: Record<string, { self_score: string | null; student_note: string | null }> = {};
      for (const cl of res.claims) {
        initMap[cl.criterion_id] = {
          self_score: cl.self_score,
          student_note: cl.student_note,
        };
      }
      setClaimsMap(initMap);
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      setFeedbackMessage({
        type: 'danger',
        text: errObj?.error?.message || 'Không thể tải dữ liệu tự chấm.',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Kiểm tra quyền chỉnh sửa form
  const isEditable = useMemo(() => {
    if (!data) return false;
    const { status } = data.case;
    const editableStatuses = ['DRAFT', 'NEEDS_INFO', 'NEEDS_PROOF'];
    if (!editableStatuses.includes(status)) return false;

    // Kiểm tra hạn chót
    const now = new Date().getTime();
    if (status === 'DRAFT') {
      const deadline = new Date(data.campaign.submission_deadline_at).getTime();
      return now < deadline;
    } else {
      // NEEDS_INFO hoặc NEEDS_PROOF: kiểm tra hạn của yêu cầu bổ sung
      const activeSupplement = data.supplement_requests?.find((r) => !r.fulfilled_at);
      if (activeSupplement) {
        const suppDeadline = new Date(activeSupplement.deadline_at).getTime();
        return now < suppDeadline;
      }
    }
    return true;
  }, [data]);

  // Tính tổng điểm tự khai hiện tại
  const claimedTotal = useMemo(() => {
    if (!data) return '0.00';
    let sum = 0;
    for (const crit of data.criteria) {
      const c = claimsMap[crit.id];
      if (c && c.self_score) {
        sum += parseFloat(c.self_score) || 0;
      }
    }
    return sum.toFixed(2);
  }, [data, claimsMap]);

  // Tổng điểm tối đa
  const maxTotal = useMemo(() => {
    if (!data) return '0.00';
    const sum = data.criteria.reduce((acc, c) => acc + (parseFloat(c.max_score) || 0), 0);
    return sum.toFixed(2);
  }, [data]);

  const handleClaimChange = (criterionId: string, selfScore: string | null, studentNote: string | null) => {
    setClaimsMap((prev) => ({
      ...prev,
      [criterionId]: {
        self_score: selfScore,
        student_note: studentNote,
      },
    }));
  };

  const handleFileUpload = async (criterionId: string, file: File) => {
    if (!data) return;
    try {
      await studentService.uploadEvidence(data.case.id, criterionId, file);
      // Tải lại dữ liệu để cập nhật danh sách evidence
      const updated = await studentService.getCurrent();
      setData(updated);
      setFeedbackMessage({
        type: 'success',
        text: `Đã tải lên tệp "${file.name}" thành công.`,
      });
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      throw errObj;
    }
  };

  const handleFileRemove = async (criterionId: string, fileId: string) => {
    if (!data) return;
    try {
      await studentService.removeEvidence(data.case.id, criterionId, fileId);
      const updated = await studentService.getCurrent();
      setData(updated);
      setFeedbackMessage({
        type: 'info',
        text: 'Đã xóa tệp minh chứng.',
      });
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      setFeedbackMessage({
        type: 'danger',
        text: errObj?.error?.message || 'Không thể xóa tệp.',
      });
    }
  };

  // Lưu nháp toàn bộ các tiêu chí đã sửa
  const handleSaveDraft = async () => {
    if (!data || !isEditable) return;
    setIsSaving(true);
    setValidationError(null);
    setFeedbackMessage(null);

    try {
      let currentVer = data.case.version;
      for (const crit of data.criteria) {
        const item = claimsMap[crit.id];
        if (item) {
          const res = await studentService.saveClaim(
            data.case.id,
            crit.id,
            item.self_score,
            item.student_note,
            currentVer
          );
          currentVer = res.version;
        }
      }

      const updated = await studentService.getCurrent();
      setData(updated);
      setFeedbackMessage({
        type: 'success',
        text: 'Đã lưu bản nháp thành công! (Phiên bản v' + updated.case.version + ')',
      });
    } catch (err: unknown) {
      const errObj = err as { error?: { code?: string; message?: string } };
      if (errObj?.error?.code === 'CASE_CHANGED') {
        setFeedbackMessage({
          type: 'danger',
          text: 'Hồ sơ đã được cập nhật từ nơi khác. Vui lòng bấm "Tải lại dữ liệu".',
        });
      } else {
        setFeedbackMessage({
          type: 'danger',
          text: errObj?.error?.message || 'Lỗi khi lưu nháp.',
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  // Kiểm tra trước khi mở hộp xác nhận nộp
  const handlePreSubmit = () => {
    if (!data || !isEditable) return;
    setValidationError(null);

    // Kiểm tra mọi tiêu chí phải có self_score
    const unScored: string[] = [];
    const missingEvidence: string[] = [];

    for (const crit of data.criteria) {
      const claim = claimsMap[crit.id];
      if (!claim || claim.self_score === null || claim.self_score.trim() === '') {
        unScored.push(crit.code);
      } else {
        const num = parseFloat(claim.self_score);
        if (isNaN(num) || num < 0 || num > parseFloat(crit.max_score)) {
          unScored.push(`${crit.code} (điểm không hợp lệ)`);
        }
      }

      // Kiểm tra minh chứng bắt buộc
      const originalClaim = data.claims.find((c) => c.criterion_id === crit.id);
      if (crit.requires_evidence && (!originalClaim || !originalClaim.evidence || originalClaim.evidence.length === 0)) {
        missingEvidence.push(crit.code);
      }
    }

    if (unScored.length > 0) {
      setValidationError(`Vui lòng tự chấm điểm hợp lệ cho tất cả tiêu chí: ${unScored.join(', ')}.`);
      return;
    }

    if (missingEvidence.length > 0) {
      // Cảnh báo người dùng nhưng cho phép nộp (hệ thống sẽ chuyển thành NEEDS_INFO như đặc tả)
      setFeedbackMessage({
        type: 'info',
        text: `Lưu ý: Tiêu chí [${missingEvidence.join(', ')}] bắt buộc có minh chứng nhưng bạn chưa đính kèm. Hồ sơ sau khi nộp sẽ chuyển sang trạng thái "Cần bổ sung thông tin" (NEEDS_INFO).`,
      });
    }

    setShowConfirm(true);
  };

  // Xác nhận nộp hồ sơ
  const handleConfirmSubmit = async () => {
    if (!data) return;
    setShowConfirm(false);
    setIsSubmitting(true);
    setValidationError(null);
    setFeedbackMessage(null);

    try {
      // Lưu lại các chỉnh sửa mới nhất trước khi gọi nộp
      let currentVer = data.case.version;
      for (const crit of data.criteria) {
        const item = claimsMap[crit.id];
        if (item) {
          const res = await studentService.saveClaim(
            data.case.id,
            crit.id,
            item.self_score,
            item.student_note,
            currentVer
          );
          currentVer = res.version;
        }
      }

      // Gọi API nộp hồ sơ
      const submitRes = await studentService.submitCase(data.case.id, currentVer);

      const updated = await studentService.getCurrent();
      setData(updated);

      if (submitRes.status === 'NEEDS_INFO') {
        setFeedbackMessage({
          type: 'danger',
          text: `Hồ sơ đã được tiếp nhận nhưng thiếu thông tin bắt buộc. Trạng thái hiện tại: Cần bổ sung thông tin (NEEDS_INFO). Vui lòng bổ sung trước hạn.`,
        });
      } else {
        setFeedbackMessage({
          type: 'success',
          text: 'Nộp hồ sơ thành công! Hồ sơ đã được chuyển đến Ban cán sự lớp kiểm tra.',
        });
      }
    } catch (err: unknown) {
      const errObj = err as { error?: { code?: string; message?: string } };
      if (errObj?.error?.code === 'CASE_CHANGED') {
        setFeedbackMessage({
          type: 'danger',
          text: 'Hồ sơ đã thay đổi từ trước. Vui lòng tải lại dữ liệu và thử lại.',
        });
      } else {
        setFeedbackMessage({
          type: 'danger',
          text: errObj?.error?.message || 'Có lỗi xảy ra khi nộp hồ sơ.',
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
          <div className="skeleton-line" style={{ width: '50%', height: '1.5rem' }} />
          <div className="skeleton-line" style={{ width: '80%', height: '1rem' }} />
          <div style={{ marginTop: '2rem' }}>
            <div className="skeleton-line" style={{ height: '6rem' }} />
            <div className="skeleton-line" style={{ height: '6rem' }} />
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
            <strong>Lỗi tải dữ liệu:</strong> {feedbackMessage?.text || 'Không thể tải hồ sơ rèn luyện.'}
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

  const { campaign, case: studentCase, criteria, claims, supplement_requests } = data;
  const activeSupplement = supplement_requests?.find((r) => !r.fulfilled_at);

  return (
    <div>
      {/* 1. Thanh kịch bản hỗ trợ kiểm thử */}
      <StudentScenarioBar onScenarioChange={loadData} />

      {/* 2. Header trang */}
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
            <Link to="/student" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem' }}>
              <ArrowLeft size={16} /> Quay lại bảng tin
            </Link>
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
            Biểu mẫu Tự đánh giá & Nộp minh chứng
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Hồ sơ phiên bản v{studentCase.version} • {campaign.title}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <StatusBadge status={studentCase.status} />
          {studentCase.status === 'NEEDS_INFO' || studentCase.status === 'NEEDS_PROOF' ? (
            activeSupplement ? (
              <Deadline isoString={activeSupplement.deadline_at} label="Hạn bổ sung" />
            ) : null
          ) : (
            <Deadline isoString={campaign.submission_deadline_at} label="Hạn nộp" />
          )}
        </div>
      </div>

      {/* 3. Banner phản hồi / thông báo kết quả */}
      {feedbackMessage && (
        <div className={`student-alert student-alert-${feedbackMessage.type}`}>
          {feedbackMessage.type === 'success' && <CheckCircle2 size={18} style={{ flexShrink: 0 }} />}
          {feedbackMessage.type === 'danger' && <AlertTriangle size={18} style={{ flexShrink: 0 }} />}
          {feedbackMessage.type === 'info' && <Info size={18} style={{ flexShrink: 0 }} />}
          <div style={{ flex: 1 }}>{feedbackMessage.text}</div>
        </div>
      )}

      {/* 4. Banner cảnh báo nếu form bị khóa không cho sửa */}
      {!isEditable && (
        <div className="student-alert student-alert-info">
          <Lock size={18} style={{ flexShrink: 0 }} />
          <div>
            <strong>Biểu mẫu đang ở chế độ xem:</strong>{' '}
            {studentCase.status === 'SUBMITTED' || studentCase.status === 'BCS_REVIEW'
              ? 'Hồ sơ đã được nộp và đang trong quá trình Ban cán sự kiểm tra. Bạn không thể chỉnh sửa lúc này.'
              : studentCase.status === 'PROPOSED' || studentCase.status === 'PUBLISHED'
              ? 'Điểm đánh giá đang được xét duyệt hoặc đã công bố. Vui lòng sang trang "Kết quả dự kiến" để xem chi tiết.'
              : studentCase.status.startsWith('CLOSED')
              ? 'Hồ sơ đã đóng, không còn hiệu lực chỉnh sửa.'
              : 'Đã quá thời hạn nộp hoặc hồ sơ không thuộc trạng thái cho phép chỉnh sửa.'}
          </div>
        </div>
      )}

      {/* 5. Cảnh báo lỗi xác thực */}
      {validationError && (
        <div className="student-alert student-alert-danger">
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <div>{validationError}</div>
        </div>
      )}

      {/* 6. Danh sách các tiêu chí đánh giá */}
      <div>
        {criteria.map((crit) => {
          const claim = claims.find((c) => c.criterion_id === crit.id) || {
            id: `temp-${crit.id}`,
            criterion_id: crit.id,
            self_score: null,
            student_note: null,
            approved_score: null,
            bcs_reason: null,
            evidence: [],
          };

          const suppReq = supplement_requests?.find(
            (r) => !r.fulfilled_at && (r.criterion_id === crit.id || r.criterion_id === null)
          );

          return (
            <CriterionCard
              key={crit.id}
              criterion={crit}
              claim={claim}
              supplementRequest={suppReq}
              isEditable={isEditable}
              onClaimChange={handleClaimChange}
              onFileUpload={handleFileUpload}
              onFileRemove={handleFileRemove}
            />
          );
        })}
      </div>

      {/* 7. Thanh tổng kết & Hành động (Sticky / Footer Card) */}
      <div className="card" style={{ marginTop: '1.5rem', position: 'sticky', bottom: '1rem', zIndex: 10 }}>
        <div className="student-action-bar" style={{ margin: 0, padding: 0, border: 'none' }}>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Tổng điểm tự khai dự tính:</div>
            <div style={{ fontSize: '1.45rem', fontWeight: 700, color: '#1e40af' }}>
              {claimedTotal}{' '}
              <span style={{ fontSize: '0.95rem', color: '#64748b', fontWeight: 400 }}>
                / {maxTotal} điểm
              </span>
            </div>
          </div>

          <div className="btn-group" style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleSaveDraft}
              disabled={!isEditable || isSaving || isSubmitting}
              title="Lưu lại điểm tự khai và ghi chú hiện tại"
            >
              <Save size={16} />
              <span>{isSaving ? 'Đang lưu...' : 'Lưu nháp'}</span>
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={handlePreSubmit}
              disabled={!isEditable || isSaving || isSubmitting}
              title="Gửi hồ sơ cho Ban cán sự lớp kiểm tra"
            >
              <Send size={16} />
              <span>
                {isSubmitting
                  ? 'Đang nộp...'
                  : studentCase.status === 'NEEDS_INFO' || studentCase.status === 'NEEDS_PROOF'
                  ? 'Nộp bổ sung'
                  : 'Nộp hồ sơ'}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* 8. Hộp thoại xác nhận nộp hồ sơ */}
      <ConfirmDialog
        isOpen={showConfirm}
        title="Xác nhận nộp hồ sơ rèn luyện"
        message="Sau khi nộp, hồ sơ sẽ được chuyển tới Ban cán sự lớp để kiểm tra. Bạn sẽ không thể tự ý sửa đổi trừ khi có yêu cầu bổ sung thông tin hoặc minh chứng. Bạn có chắc chắn muốn nộp?"
        confirmLabel="Đồng ý nộp"
        cancelLabel="Kiểm tra lại"
        isLoading={isSubmitting}
        onConfirm={handleConfirmSubmit}
        onCancel={() => setShowConfirm(false)}
      />
    </div>
  );
};
