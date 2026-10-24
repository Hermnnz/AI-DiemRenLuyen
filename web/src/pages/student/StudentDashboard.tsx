import React, { useEffect, useState, useCallback } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { Link } from 'react-router-dom';
import { StudentCurrentResponse, NotificationItem } from '../../api/types';
import { studentService } from '../../components/student/studentService';
import { StudentScenarioBar } from '../../components/student/StudentScenarioBar';
import '../../components/student/studentStyles.css';
import {
  FileEdit,
  Award,
  AlertTriangle,
  Bell,
  CheckCircle2,
  Clock,
  ArrowRight,
  RefreshCw,
  Info,
} from 'lucide-react';

export const StudentDashboard: React.FC = () => {
  const [data, setData] = useState<StudentCurrentResponse | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [currentRes, notifs] = await Promise.all([
        studentService.getCurrent(),
        studentService.getNotifications(),
      ]);
      setData(currentRes);
      setNotifications(notifs);
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string } };
      setError(errObj?.error?.message || 'Không thể tải thông tin sinh viên.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleMarkNotifRead = async (id: string) => {
    await studentService.markNotificationRead(id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
    );
  };

  if (isLoading) {
    return (
      <div className="container" style={{ padding: '1.5rem' }}>
        <StudentScenarioBar onScenarioChange={loadData} />
        <div className="card" style={{ padding: '2rem' }}>
          <div className="skeleton-line" style={{ width: '40%', height: '1.5rem' }} />
          <div className="skeleton-line" style={{ width: '70%', height: '1rem' }} />
          <div style={{ marginTop: '2rem' }}>
            <div className="skeleton-line" style={{ height: '3rem' }} />
            <div className="skeleton-line" style={{ height: '3rem' }} />
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container" style={{ padding: '1.5rem' }}>
        <StudentScenarioBar onScenarioChange={loadData} />
        <div className="student-alert student-alert-danger">
          <AlertTriangle size={20} />
          <div>
            <strong>Lỗi tải dữ liệu:</strong> {error || 'Không tìm thấy hồ sơ sinh viên.'}
            <div style={{ marginTop: '0.75rem' }}>
              <button type="button" className="btn btn-secondary" onClick={loadData}>
                <RefreshCw size={14} /> Thử lại
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const { campaign, case: studentCase, supplement_requests } = data;
  const activeSupplement = supplement_requests?.find((r) => !r.fulfilled_at);

  // Tính tổng điểm tối đa của các tiêu chí
  const totalMaxScore = data.criteria.reduce(
    (acc, c) => acc + (parseFloat(c.max_score) || 0),
    0
  );

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
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
            Bảng tin Đánh giá Rèn luyện
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Theo dõi tiến độ tự chấm, nộp minh chứng và kết quả điểm rèn luyện cá nhân
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8125rem', color: '#64748b' }}>Trạng thái đợt:</span>
          <StatusBadge status={campaign.status} />
        </div>
      </div>

      {/* 3. Banner cảnh báo yêu cầu bổ sung thông tin/minh chứng */}
      {activeSupplement && (
        <div className="student-alert student-alert-warning">
          <AlertTriangle size={22} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
              Yêu cầu bổ sung {activeSupplement.kind === 'INFO' ? 'thông tin hồ sơ' : 'minh chứng'} (Lượt {activeSupplement.round_no})
            </div>
            <div style={{ marginTop: '0.25rem' }}>{activeSupplement.reason}</div>
            <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <Deadline isoString={activeSupplement.deadline_at} label="Hạn chót bổ sung" />
              <Link to="/student/submission" className="btn btn-primary" style={{ padding: '0.35rem 0.85rem', fontSize: '0.8125rem' }}>
                Bổ sung hồ sơ ngay <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* 4. Thẻ tổng quan đợt & tiến độ hồ sơ */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            flexWrap: 'wrap',
            gap: '1rem',
            borderBottom: '1px solid #f1f5f9',
            paddingBottom: '1rem',
          }}
        >
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#1e40af' }}>
              {campaign.title}
            </h3>
            <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: '0.25rem' }}>
              Học kỳ: <strong>{campaign.term}</strong> • Phiên bản hồ sơ: v{studentCase.version}
            </p>
          </div>
          <div>
            <span style={{ fontSize: '0.8125rem', color: '#64748b', marginRight: '0.5rem' }}>Hồ sơ của bạn:</span>
            <StatusBadge status={studentCase.status} />
          </div>
        </div>

        {/* Grid thông tin chi tiết */}
        <div className="student-dashboard-grid" style={{ marginTop: '1.25rem' }}>
          {/* Cột 1: Hạn nộp / Hạn phản hồi */}
          <div style={{ backgroundColor: '#f8fafc', padding: '1rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.8125rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Clock size={15} />
              <span>
                {studentCase.status === 'PUBLISHED'
                  ? 'Hạn khiếu nại / Đồng ý'
                  : 'Hạn chót nộp hồ sơ'}
              </span>
            </div>
            <div style={{ marginTop: '0.5rem' }}>
              {studentCase.status === 'PUBLISHED' ? (
                <Deadline isoString={studentCase.appeal_deadline_at} label="Hạn phản hồi" />
              ) : (
                <Deadline isoString={campaign.submission_deadline_at} label="Hạn nộp" />
              )}
            </div>
          </div>

          {/* Cột 2: Điểm tự khai */}
          <div style={{ backgroundColor: '#f8fafc', padding: '1rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.8125rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <FileEdit size={15} />
              <span>Tổng điểm tự khai</span>
            </div>
            <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#1e40af', marginTop: '0.35rem' }}>
              {studentCase.claimed_total ?? '0.00'}{' '}
              <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 400 }}>
                / {totalMaxScore.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Cột 3: Điểm dự kiến (chỉ hiện khi đã công bố) */}
          <div style={{ backgroundColor: '#f8fafc', padding: '1rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.8125rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Award size={15} />
              <span>
                {studentCase.status === 'FINALIZED' ? 'Điểm chốt chính thức' : 'Điểm dự kiến (BCS)'}
              </span>
            </div>
            <div style={{ fontSize: '1.35rem', fontWeight: 700, color: studentCase.proposed_total ? '#047857' : '#94a3b8', marginTop: '0.35rem' }}>
              {studentCase.final_total ?? studentCase.proposed_total ?? (
                <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#64748b' }}>
                  Chưa công bố
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 5. Khối "Hành động tiếp theo" */}
        <div
          style={{
            backgroundColor: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: '6px',
            padding: '1rem 1.25rem',
            marginTop: '0.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div>
            <div style={{ fontWeight: 600, color: '#1e40af', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Info size={16} /> Việc tiếp theo cần làm:
            </div>
            <p style={{ fontSize: '0.875rem', color: '#1e3a8a', marginTop: '0.25rem' }}>
              {studentCase.status === 'DRAFT' &&
                'Bạn đang ở giai đoạn tự chấm. Vui lòng rà soát điểm tự khai và tải minh chứng trước hạn chót.'}
              {studentCase.status === 'NEEDS_INFO' &&
                'Hồ sơ của bạn bị yêu cầu bổ sung thông tin/minh chứng bắt buộc. Hãy hoàn tất bổ sung trước hạn.'}
              {studentCase.status === 'NEEDS_PROOF' &&
                'Ban cán sự yêu cầu bạn bổ sung thêm minh chứng. Vui lòng gửi tệp minh chứng rõ ràng hơn.'}
              {(studentCase.status === 'SUBMITTED' || studentCase.status === 'BCS_REVIEW') &&
                'Hồ sơ của bạn đã nộp thành công và đang được Ban cán sự lớp kiểm tra. Vui lòng chờ họp bình xét.'}
              {studentCase.status === 'PROPOSED' &&
                'Ban cán sự đã duyệt xong điểm dự kiến. Điểm sẽ được công bố sau khi hoàn tất các cuộc họp lớp.'}
              {studentCase.status === 'PUBLISHED' &&
                'Điểm dự kiến đã công bố! Bạn hãy kiểm tra bảng điểm, bấm "Đồng ý" hoặc gửi "Khiếu nại" trong thời hạn.'}
              {studentCase.status === 'ACCEPTED' &&
                'Bạn đã đồng ý với điểm dự kiến. Hồ sơ đang chờ Ban cán sự và GVCN chốt chính thức.'}
              {studentCase.status === 'ACCEPTED_AUTO' &&
                'Hồ sơ đã được tự động chấp nhận do hết hạn khiếu nại. Chờ chốt kết quả toàn khóa.'}
              {studentCase.status === 'APPEALED' &&
                'Khiếu nại của bạn đang được Ban cán sự xem xét giải quyết. Bạn có thể theo dõi tiến độ ở trang Khiếu nại.'}
              {studentCase.status === 'RESOLVED' &&
                'Ban cán sự đã xử lý khiếu nại của bạn. Vui lòng xem điểm điều chỉnh tại trang Kết quả.'}
              {studentCase.status === 'FINALIZED' &&
                'Đợt đánh giá đã hoàn tất và chốt kết quả chính thức. Bạn có thể xem bảng điểm cuối cùng.'}
              {studentCase.status === 'CLOSED_NO_SUBMIT' &&
                'Đã quá hạn nộp hồ sơ mà bạn chưa hoàn thành. Hồ sơ được đánh dấu đóng.'}
              {studentCase.status === 'CLOSED_INCOMPLETE' &&
                'Hồ sơ đã đóng do hết lượt hoặc hết hạn bổ sung minh chứng.'}
            </p>
          </div>

          <div>
            {(studentCase.status === 'DRAFT' ||
              studentCase.status === 'NEEDS_INFO' ||
              studentCase.status === 'NEEDS_PROOF') && (
              <Link to="/student/submission" className="btn btn-primary">
                <FileEdit size={16} /> Điền tự chấm & Tải minh chứng
              </Link>
            )}

            {(studentCase.status === 'PUBLISHED' ||
              studentCase.status === 'ACCEPTED' ||
              studentCase.status === 'ACCEPTED_AUTO' ||
              studentCase.status === 'RESOLVED' ||
              studentCase.status === 'FINALIZED') && (
              <Link to="/student/result" className="btn btn-primary">
                <Award size={16} /> Xem kết quả chi tiết
              </Link>
            )}

            {studentCase.status === 'APPEALED' && (
              <Link to="/student/appeal" className="btn btn-secondary">
                Xem tiến độ khiếu nại
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* 6. Danh sách thông báo trong hệ thống */}
      <div className="card">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Bell size={18} color="#1e40af" />
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Thông báo hệ thống</h3>
          </div>
          <span style={{ fontSize: '0.8125rem', color: '#64748b' }}>
            {notifications.filter((n) => !n.read_at).length} thông báo chưa đọc
          </span>
        </div>

        {notifications.length === 0 ? (
          <p style={{ fontSize: '0.875rem', color: '#94a3b8', textAlign: 'center', padding: '1rem' }}>
            Không có thông báo mới
          </p>
        ) : (
          <div>
            {notifications.map((notif) => (
              <div
                key={notif.id}
                className={`notification-card ${!notif.read_at ? 'unread' : ''}`}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>
                    {notif.title}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '0.2rem' }}>
                    {notif.body}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.35rem' }}>
                    {new Intl.DateTimeFormat('vi-VN', {
                      timeZone: 'Asia/Ho_Chi_Minh',
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    }).format(new Date(notif.created_at))}
                  </div>
                </div>

                {!notif.read_at && (
                  <button
                    type="button"
                    onClick={() => handleMarkNotifRead(notif.id)}
                    className="btn btn-secondary"
                    style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                    title="Đánh dấu đã đọc"
                  >
                    <CheckCircle2 size={14} />
                    <span>Đã đọc</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
