import React, { useState, useEffect, useCallback } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { Link, useNavigate } from 'react-router-dom';
import { StudentCurrentResponse } from '../../api/types';
import { studentService } from '../../components/student/studentService';
import { StudentScenarioBar } from '../../components/student/StudentScenarioBar';
import '../../components/student/studentStyles.css';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  FileQuestion,
  ArrowLeft,
  Clock,
  EyeOff,
  Scale,
  RefreshCw,
  FileText,
  Image as ImageIcon,
} from 'lucide-react';

export const StudentResult: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<StudentCurrentResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAccepting, setIsAccepting] = useState<boolean>(false);
  const [showConfirmAccept, setShowConfirmAccept] = useState<boolean>(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'danger' | 'info'; text: string } | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setFeedbackMessage(null);
      const res = await studentService.getCurrent();
      setData(res);
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      setFeedbackMessage({
        type: 'danger',
        text: errObj?.error?.message || 'Không thể tải kết quả đánh giá.',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Kiểm tra trạng thái đã công bố chưa
  const isPublishedStage = (status: string): boolean => {
    const publishedStages = ['PUBLISHED', 'ACCEPTED', 'ACCEPTED_AUTO', 'APPEALED', 'RESOLVED', 'FINALIZED'];
    return publishedStages.includes(status);
  };

  // Kiểm tra hết hạn khiếu nại
  const isAppealExpired = (deadlineIso: string | null | undefined): boolean => {
    if (!deadlineIso) return false;
    return new Date(deadlineIso).getTime() <= new Date().getTime();
  };

  // Xác nhận đồng ý điểm
  const handleConfirmAccept = async () => {
    if (!data) return;
    setShowConfirmAccept(false);
    setIsAccepting(true);
    setFeedbackMessage(null);

    try {
      await studentService.acceptCase(data.case.id, data.case.version);
      const updated = await studentService.getCurrent();
      setData(updated);
      setFeedbackMessage({
        type: 'success',
        text: 'Bạn đã xác nhận đồng ý với điểm dự kiến thành công!',
      });
    } catch (err: unknown) {
      const errObj = err as { error?: { code?: string; message?: string } };
      if (errObj?.error?.code === 'CASE_CHANGED') {
        setFeedbackMessage({
          type: 'danger',
          text: 'Hồ sơ đã thay đổi từ trước. Vui lòng tải lại trang.',
        });
      } else {
        setFeedbackMessage({
          type: 'danger',
          text: errObj?.error?.message || 'Không thể ghi nhận phản hồi đồng ý.',
        });
      }
    } finally {
      setIsAccepting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container" style={{ padding: '1.5rem' }}>
        <StudentScenarioBar onScenarioChange={loadData} />
        <div className="card" style={{ padding: '2rem' }}>
          <div className="skeleton-line" style={{ width: '45%', height: '1.5rem' }} />
          <div className="skeleton-line" style={{ width: '75%', height: '1rem' }} />
          <div style={{ marginTop: '2rem' }}>
            <div className="skeleton-line" style={{ height: '4rem' }} />
            <div className="skeleton-line" style={{ height: '4rem' }} />
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { campaign, case: studentCase, criteria, claims } = data;
  const isPublished = isPublishedStage(studentCase.status);
  const appealExpired = isAppealExpired(studentCase.appeal_deadline_at);

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
            <Link to="/student" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem' }}>
              <ArrowLeft size={16} /> Quay lại bảng tin
            </Link>
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
            Kết quả Đánh giá Điểm Rèn luyện
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            {campaign.title} • {campaign.term}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <StatusBadge status={studentCase.status} />
          {isPublished && studentCase.appeal_deadline_at && (
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

      {/* 4. TRƯỜNG HỢP: CHƯA CÔNG BỐ ĐIỂM (Bảo mật: Không được rò rỉ điểm BCS) */}
      {!isPublished ? (
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
            <EyeOff size={32} color="#64748b" />
          </div>

          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b' }}>
            Điểm dự kiến chưa được công bố
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
            Hồ sơ rèn luyện của bạn đang ở trạng thái{' '}
            <strong style={{ color: '#1e40af' }}>{studentCase.status}</strong>. Theo quy định,
            điểm chỉ được công bố sau khi Ban cán sự hoàn tất kiểm tra hồ sơ và hoàn thành các cuộc họp
            bình xét theo quy chế.
          </p>

          <div style={{ display: 'inline-flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
            <Link to="/student" className="btn btn-secondary">
              Xem bảng tin sinh viên
            </Link>
            {(studentCase.status === 'DRAFT' ||
              studentCase.status === 'NEEDS_INFO' ||
              studentCase.status === 'NEEDS_PROOF') && (
              <Link to="/student/submission" className="btn btn-primary">
                Xem lại hồ sơ tự chấm
              </Link>
            )}
          </div>
        </div>
      ) : (
        /* 5. TRƯỜNG HỢP: ĐÃ CÔNG BỐ ĐIỂM (Hiển thị đầy đủ bảng điểm & lý do BCS) */
        <div>
          {/* Card tổng kết điểm */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem',
                borderBottom: '1px solid #f1f5f9',
                paddingBottom: '1rem',
              }}
            >
              <div>
                <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
                  {studentCase.status === 'FINALIZED'
                    ? 'Bảng điểm chính thức đã chốt toàn khóa'
                    : 'Bảng điểm rèn luyện dự kiến do Ban cán sự duyệt'}
                </span>
                <div style={{ fontSize: '0.875rem', color: '#475569', marginTop: '0.2rem' }}>
                  Sinh viên có quyền gửi khiếu nại một lần trước hạn chót nếu phát hiện sai lệch.
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.8125rem', color: '#64748b' }}>
                  {studentCase.status === 'FINALIZED' ? 'Điểm chính thức:' : 'Tổng điểm dự kiến:'}
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#1e40af' }}>
                  {studentCase.final_total ?? studentCase.proposed_total ?? '—'}
                  <span style={{ fontSize: '1rem', color: '#64748b', fontWeight: 400 }}>
                    {' '}
                    (Tự khai: {studentCase.claimed_total ?? '0.00'})
                  </span>
                </div>
              </div>
            </div>

            {/* Thông báo trạng thái phản hồi */}
            {studentCase.status === 'ACCEPTED' && (
              <div className="student-alert student-alert-success" style={{ marginTop: '1rem', marginBottom: 0 }}>
                <CheckCircle2 size={18} />
                <div>
                  <strong>Bạn đã đồng ý với điểm dự kiến.</strong> Kết quả đang chờ Ban cán sự và GVCN chốt chính thức.
                </div>
              </div>
            )}

            {studentCase.status === 'ACCEPTED_AUTO' && (
              <div className="student-alert student-alert-info" style={{ marginTop: '1rem', marginBottom: 0 }}>
                <Clock size={18} />
                <div>
                  <strong>Hệ thống đã tự động chấp nhận kết quả:</strong> Đã quá thời hạn phản hồi mà không có khiếu nại.
                </div>
              </div>
            )}

            {studentCase.status === 'APPEALED' && (
              <div className="student-alert student-alert-warning" style={{ marginTop: '1rem', marginBottom: 0 }}>
                <Scale size={18} />
                <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <span>
                    <strong>Đang có khiếu nại chờ Ban cán sự giải quyết.</strong>
                  </span>
                  <Link to="/student/appeal" className="btn btn-secondary" style={{ padding: '0.25rem 0.6rem', fontSize: '0.8rem' }}>
                    Xem chi tiết khiếu nại
                  </Link>
                </div>
              </div>
            )}

            {studentCase.status === 'RESOLVED' && (
              <div className="student-alert student-alert-success" style={{ marginTop: '1rem', marginBottom: 0 }}>
                <CheckCircle2 size={18} />
                <div>
                  <strong>Ban cán sự đã giải quyết khiếu nại của bạn.</strong> Điểm mới đã được cập nhật vào bảng dưới đây.
                </div>
              </div>
            )}

            {studentCase.status === 'FINALIZED' && (
              <div className="student-alert student-alert-success" style={{ marginTop: '1rem', marginBottom: 0 }}>
                <Award size={18} />
                <div>
                  <strong>Kết quả rèn luyện đã được chốt chính thức.</strong> Điểm số đã cố định và được lưu vào hồ sơ đào tạo.
                </div>
              </div>
            )}
          </div>

          {/* Bảng so sánh chi tiết các tiêu chí */}
          <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem' }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.75rem', color: '#1e40af' }}>
              Chi tiết đánh giá từng tiêu chí
            </h3>

            <div className="result-table-wrapper">
              <table className="result-table">
                <thead>
                  <tr>
                    <th style={{ width: '30%' }}>Tiêu chí</th>
                    <th style={{ width: '22%' }}>Sinh viên tự khai</th>
                    <th style={{ width: '18%' }}>BCS duyệt</th>
                    <th style={{ width: '30%' }}>Lý do & Nhận xét của BCS</th>
                  </tr>
                </thead>
                <tbody>
                  {criteria.map((crit) => {
                    const claim = claims.find((c) => c.criterion_id === crit.id);
                    const selfScore = claim?.self_score ?? '0.00';
                    const approvedScore = claim?.approved_score ?? '—';
                    const isDifferent =
                      claim?.approved_score !== null &&
                      claim?.approved_score !== undefined &&
                      parseFloat(selfScore) !== parseFloat(claim.approved_score);

                    return (
                      <tr key={crit.id} style={{ backgroundColor: isDifferent ? '#fffdfa' : undefined }}>
                        {/* Cột 1: Tiêu chí */}
                        <td>
                          <div style={{ fontWeight: 600, color: '#1e40af' }}>{crit.code}</div>
                          <div style={{ fontSize: '0.875rem', color: '#0f172a' }}>{crit.title}</div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.15rem' }}>
                            Tối đa: {crit.max_score} điểm
                          </div>
                        </td>

                        {/* Cột 2: Tự khai */}
                        <td>
                          <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{selfScore} đ</div>
                          {claim?.student_note && (
                            <div style={{ fontSize: '0.8rem', color: '#475569', fontStyle: 'italic', marginTop: '0.2rem' }}>
                              "{claim.student_note}"
                            </div>
                          )}
                          {claim?.evidence && claim.evidence.length > 0 && (
                            <div style={{ marginTop: '0.35rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                              {claim.evidence.map((ev) => (
                                <a
                                  key={ev.id}
                                  href={`/api/v1/files/${ev.id}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    fontSize: '0.75rem',
                                    color: '#2563eb',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.2rem',
                                  }}
                                >
                                  {ev.mime_type.startsWith('image/') ? <ImageIcon size={12} /> : <FileText size={12} />}
                                  <span style={{ textDecoration: 'underline' }}>{ev.original_name}</span>
                                </a>
                              ))}
                            </div>
                          )}
                        </td>

                        {/* Cột 3: Điểm duyệt BCS */}
                        <td>
                          <div
                            style={{
                              fontWeight: 700,
                              fontSize: '1rem',
                              color: isDifferent ? '#dc2626' : '#15803d',
                            }}
                          >
                            {approvedScore} đ
                          </div>
                          {isDifferent && (
                            <span className="score-difference-alert">
                              Khác tự khai: {(parseFloat(approvedScore) - parseFloat(selfScore)).toFixed(2)} đ
                            </span>
                          )}
                        </td>

                        {/* Cột 4: Lý do BCS */}
                        <td>
                          {claim?.bcs_reason ? (
                            <div style={{ fontSize: '0.85rem', color: '#334155' }}>
                              {claim.bcs_reason}
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                              (Không có ghi chú thêm)
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Action Bar khi ở trạng thái PUBLISHED */}
          {studentCase.status === 'PUBLISHED' && (
            <div className="card">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '1rem',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, color: '#0f172a' }}>
                    Phản hồi về kết quả dự kiến:
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                    {appealExpired
                      ? 'Đã hết thời hạn gửi khiếu nại. Kết quả sẽ được tự động ghi nhận.'
                      : 'Bạn có thể chọn Đồng ý hoặc gửi Khiếu nại nếu có điểm chưa thỏa đáng.'}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => navigate('/student/appeal')}
                    disabled={appealExpired || isAccepting}
                    title="Gửi khiếu nại về các tiêu chí chưa đồng thuận"
                  >
                    <FileQuestion size={16} />
                    <span>Khiếu nại điểm</span>
                  </button>

                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setShowConfirmAccept(true)}
                    disabled={appealExpired || isAccepting}
                    title="Đồng ý với toàn bộ điểm đánh giá dự kiến"
                  >
                    <CheckCircle2 size={16} />
                    <span>{isAccepting ? 'Đang xác nhận...' : 'Đồng ý với điểm dự kiến'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Hộp thoại xác nhận Đồng ý điểm */}
          <ConfirmDialog
            isOpen={showConfirmAccept}
            title="Xác nhận đồng ý điểm rèn luyện dự kiến"
            message={`Bạn xác nhận đồng ý với điểm rèn luyện dự kiến là ${studentCase.proposed_total} điểm? Sau khi đồng ý, bạn sẽ không thể gửi khiếu nại nữa.`}
            confirmLabel="Đồng ý kết quả"
            cancelLabel="Xem lại"
            isLoading={isAccepting}
            onConfirm={handleConfirmAccept}
            onCancel={() => setShowConfirmAccept(false)}
          />
        </div>
      )}
    </div>
  );
};
