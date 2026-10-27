import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import {
  BcsAiFeedbackItem,
  BcsAiFeedbackDetail,
  AiFeedbackMetrics,
  AiFeedbackListResponse,
  GroundTruthLabel,
} from '../../api/types';
import {
  Brain,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  ShieldCheck,
  Scale,
  RefreshCw,
  X,
  FileText,
  HelpCircle,
  History,
} from 'lucide-react';

export const AdminAiEvaluation: React.FC = () => {
  const [items, setItems] = useState<BcsAiFeedbackItem[]>([]);
  const [metrics, setMetrics] = useState<AiFeedbackMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterDiscrepancy, setFilterDiscrepancy] = useState<string>('');
  const [filterGroundTruth, setFilterGroundTruth] = useState<string>('');

  // Selected detail modal
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<BcsAiFeedbackDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Form states for ground-truth verification
  const [selectedLabel, setSelectedLabel] = useState<GroundTruthLabel>('SUPPORTED');
  const [verifyReason, setVerifyReason] = useState<string>('');
  const [submittingVerify, setSubmittingVerify] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifySuccess, setVerifySuccess] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterDiscrepancy) params.set('discrepancy_status', filterDiscrepancy);
      if (filterGroundTruth) params.set('ground_truth_status', filterGroundTruth);

      const qs = params.toString() ? `?${params.toString()}` : '';
      const [listRes, metricsRes] = await Promise.all([
        api.get<AiFeedbackListResponse>(`/admin/ai-feedback${qs}`),
        api.get<AiFeedbackMetrics>('/admin/ai-feedback-metrics'),
      ]);
      setItems(listRes.items || []);
      setMetrics(metricsRes);
    } catch (err: any) {
      console.error('Failed to load AI evaluation data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filterDiscrepancy, filterGroundTruth]);

  const openDetail = async (id: string) => {
    setSelectedId(id);
    setLoadingDetail(true);
    setVerifyError(null);
    setVerifySuccess(null);
    setVerifyReason('');
    try {
      const res = await api.get<BcsAiFeedbackDetail>(`/admin/ai-feedback/${id}`);
      setDetail(res);
      if (res.ground_truth_label) {
        setSelectedLabel(res.ground_truth_label);
      }
      if (res.verification_reason) {
        setVerifyReason(res.verification_reason);
      }
    } catch (err: any) {
      console.error('Failed to load feedback detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId) return;
    if (!verifyReason.trim()) {
      setVerifyError('Vui lòng nhập lý do / căn cứ xác nhận nhãn chuẩn.');
      return;
    }

    setSubmittingVerify(true);
    setVerifyError(null);
    try {
      const updated = await api.post<BcsAiFeedbackDetail>(`/admin/ai-feedback/${selectedId}/verify`, {
        ground_truth_label: selectedLabel,
        reason: verifyReason.trim(),
      });
      setDetail(updated);
      setVerifySuccess('Đã xác nhận nhãn chuẩn thành công!');
      fetchData();
    } catch (err: any) {
      setVerifyError(err.message || 'Lỗi khi xác nhận nhãn chuẩn.');
    } finally {
      setSubmittingVerify(false);
    }
  };

  const renderDiscrepancyBadge = (status: string) => {
    switch (status) {
      case 'NEEDS_REVIEW':
        return (
          <span style={{ backgroundColor: '#fef3c7', color: '#92400e', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <AlertTriangle size={12} /> Cần rà soát chênh lệch
          </span>
        );
      case 'AGREED':
        return (
          <span style={{ backgroundColor: '#dcfce7', color: '#166534', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <CheckCircle2 size={12} /> Thống nhất
          </span>
        );
      case 'NON_FINAL_DECISION':
        return (
          <span style={{ backgroundColor: '#e2e8f0', color: '#475569', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <Clock size={12} /> Chưa cuối cùng (HOLD / Bổ sung)
          </span>
        );
      case 'NO_AI_RESULT':
      default:
        return (
          <span style={{ backgroundColor: '#f1f5f9', color: '#64748b', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <HelpCircle size={12} /> Không có kết quả AI
          </span>
        );
    }
  };

  const renderVerdictBadge = (verdict?: string | null) => {
    if (!verdict) return <span style={{ color: '#94a3b8' }}>Chưa có</span>;
    switch (verdict) {
      case 'SUPPORTED':
        return <span style={{ backgroundColor: '#dbeafe', color: '#1e40af', padding: '0.15rem 0.4rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>SUPPORTED</span>;
      case 'FLAGGED':
        return <span style={{ backgroundColor: '#fee2e2', color: '#991b1b', padding: '0.15rem 0.4rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>FLAGGED</span>;
      case 'UNKNOWN':
      default:
        return <span style={{ backgroundColor: '#f3e8ff', color: '#6b21a8', padding: '0.15rem 0.4rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>UNKNOWN</span>;
    }
  };

  const renderBcsDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'ACCEPT':
        return <span style={{ color: '#15803d', fontWeight: 600 }}>ACCEPT (Chấp thuận)</span>;
      case 'REJECT_ITEM':
        return <span style={{ color: '#b91c1c', fontWeight: 600 }}>REJECT (Bác bỏ)</span>;
      case 'REQUEST_SUPPLEMENT':
        return <span style={{ color: '#b45309', fontWeight: 600 }}>Yêu cầu bổ sung</span>;
      case 'HOLD':
        return <span style={{ color: '#4b5563', fontWeight: 600 }}>HOLD (Tạm giữ)</span>;
      default:
        return <span>{decision}</span>;
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
            <Brain size={26} color="#2563eb" /> Rà soát Chênh lệch & Đánh giá Chất lượng AI
          </h1>
          <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '0.25rem', marginBottom: 0 }}>
            Đối chiếu quyết định của Ban cán sự với kết luận phân tích AI để rà soát chênh lệch, xác nhận nhãn chuẩn và đo lường độ chính xác.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.5rem 0.85rem', borderRadius: '6px', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', cursor: 'pointer', fontSize: '0.875rem', color: '#334155' }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Làm mới
        </button>
      </div>

      {/* Metrics Summary Cards */}
      {metrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Tổng phản hồi</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', marginTop: '0.25rem' }}>{metrics.total_count}</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>{metrics.matched_count} ca có kết quả AI khớp</div>
          </div>

          <div style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ color: '#92400e', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Cần rà soát chênh lệch</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#b45309', marginTop: '0.25rem' }}>{metrics.discrepancy_count}</div>
            <div style={{ fontSize: '0.75rem', color: '#92400e', marginTop: '0.25rem' }}>Ứng viên rà soát đối chiếu</div>
          </div>

          <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ color: '#166534', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>AI & BCS Thống nhất</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#15803d', marginTop: '0.25rem' }}>{metrics.agreed_count}</div>
            <div style={{ fontSize: '0.75rem', color: '#166534', marginTop: '0.25rem' }}>Đồng thuận kết luận</div>
          </div>

          <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ color: '#475569', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Chưa cuối cùng</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#334155', marginTop: '0.25rem' }}>{metrics.non_final_count}</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>HOLD hoặc yêu cầu bổ sung</div>
          </div>

          <div style={{ backgroundColor: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ color: '#1e40af', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Đã xác nhận nhãn chuẩn</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#2563eb', marginTop: '0.25rem' }}>
              {metrics.verified_matched_count} <span style={{ fontSize: '0.875rem', color: '#64748b', fontWeight: 400 }}>/ {metrics.total_count}</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#1e40af', marginTop: '0.25rem' }}>
              {metrics.ai_accuracy !== null ? `Độ chính xác AI: ${(metrics.ai_accuracy * 100).toFixed(1)}%` : 'Chưa có nhãn chuẩn'}
            </div>
          </div>
        </div>
      )}

      {/* Metrics note */}
      {metrics && metrics.message && (
        <div style={{ backgroundColor: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '6px', padding: '0.75rem 1rem', fontSize: '0.8rem', color: '#475569', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ShieldCheck size={16} color="#059669" />
          <span><strong>Chính sách đánh giá độc lập:</strong> {metrics.message} Mọi chênh lệch chỉ là ứng viên rà soát, không tự gán nhãn chuẩn và không tự huấn luyện mô hình.</span>
        </div>
      )}

      {/* Filter Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem', backgroundColor: '#ffffff', padding: '1rem', borderRadius: '8px', border: '1px solid #e2e8f0', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#334155' }}>Trạng thái chênh lệch:</span>
          <select
            value={filterDiscrepancy}
            onChange={(e) => setFilterDiscrepancy(e.target.value)}
            style={{ padding: '0.4rem 0.75rem', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.875rem', backgroundColor: '#ffffff' }}
          >
            <option value="">Tất cả trạng thái</option>
            <option value="NEEDS_REVIEW">Cần rà soát chênh lệch</option>
            <option value="AGREED">Thống nhất</option>
            <option value="NON_FINAL_DECISION">Chưa cuối cùng (HOLD / Bổ sung)</option>
            <option value="NO_AI_RESULT">Không có kết quả AI</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#334155' }}>Nhãn chuẩn độc lập:</span>
          <select
            value={filterGroundTruth}
            onChange={(e) => setFilterGroundTruth(e.target.value)}
            style={{ padding: '0.4rem 0.75rem', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.875rem', backgroundColor: '#ffffff' }}
          >
            <option value="">Tất cả</option>
            <option value="UNVERIFIED">Chưa xác nhận nhãn chuẩn</option>
            <option value="VERIFIED">Đã xác nhận nhãn chuẩn</option>
          </select>
        </div>

        <div style={{ marginLeft: 'auto', fontSize: '0.875rem', color: '#64748b' }}>
          Hiển thị <strong>{items.length}</strong> ca
        </div>
      </div>

      {/* Main Table */}
      <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <th style={{ padding: '0.75rem 1rem' }}>Tiêu chí / Tệp</th>
              <th style={{ padding: '0.75rem 1rem' }}>Quyết định BCS</th>
              <th style={{ padding: '0.75rem 1rem' }}>Kết luận AI</th>
              <th style={{ padding: '0.75rem 1rem' }}>Tình trạng chênh lệch</th>
              <th style={{ padding: '0.75rem 1rem' }}>Nhãn chuẩn</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
                  {loading ? 'Đang tải dữ liệu...' : 'Không có ca phản hồi nào phù hợp với bộ lọc hiện tại.'}
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '0.75rem 1rem' }}>
                    <div style={{ fontWeight: 600, color: '#0f172a' }}>Mục {item.criterion_code}</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'monospace' }} title={item.file_sha256}>
                      Hash: {item.file_sha256.slice(0, 10)}... (v{item.file_version_no})
                    </div>
                  </td>
                  <td style={{ padding: '0.75rem 1rem', maxWidth: '240px' }}>
                    {renderBcsDecisionBadge(item.bcs_decision)}
                    <div style={{ fontSize: '0.8rem', color: '#475569', marginTop: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.bcs_reason}>
                      {item.bcs_reason}
                    </div>
                  </td>
                  <td style={{ padding: '0.75rem 1rem', maxWidth: '240px' }}>
                    {renderVerdictBadge(item.ai_verdict)}
                    <div style={{ fontSize: '0.8rem', color: '#475569', marginTop: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.ai_reason || ''}>
                      {item.ai_reason || <span style={{ color: '#94a3b8' }}>(Chưa có nhận xét)</span>}
                    </div>
                  </td>
                  <td style={{ padding: '0.75rem 1rem' }}>
                    {renderDiscrepancyBadge(item.discrepancy_status)}
                  </td>
                  <td style={{ padding: '0.75rem 1rem' }}>
                    {item.ground_truth_status === 'VERIFIED' ? (
                      <div>
                        <span style={{ backgroundColor: '#ecfdf5', color: '#065f46', border: '1px solid #a7f3d0', padding: '0.15rem 0.4rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}>
                          <CheckCircle2 size={12} /> {item.ground_truth_label}
                        </span>
                      </div>
                    ) : (
                      <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Chưa xác nhận</span>
                    )}
                  </td>
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                    <button
                      onClick={() => openDetail(item.id)}
                      style={{ padding: '0.35rem 0.75rem', borderRadius: '4px', backgroundColor: '#2563eb', color: '#ffffff', border: 'none', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 500 }}
                    >
                      Rà soát & Xác nhận
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal Detail & Verification */}
      {selectedId && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', width: '100%', maxWidth: '900px', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', padding: '1.5rem' }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem', marginBottom: '1.25rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Scale size={20} color="#2563eb" /> Chi tiết Ca Đánh giá & Xác nhận Nhãn chuẩn
                </h2>
                {detail && (
                  <p style={{ fontSize: '0.875rem', color: '#64748b', margin: '0.25rem 0 0 0' }}>
                    Tiêu chí: <strong>Mục {detail.criterion_code}</strong> | File: <strong>{detail.file_original_name || detail.evidence_file_id}</strong>
                  </p>
                )}
              </div>
              <button
                onClick={() => { setSelectedId(null); setDetail(null); }}
                style={{ backgroundColor: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
              >
                <X size={20} />
              </button>
            </div>

            {loadingDetail || !detail ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>Đang tải thông tin chi tiết...</div>
            ) : (
              <div>
                {/* File open link */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#f8fafc', padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid #e2e8f0', marginBottom: '1.25rem' }}>
                  <div style={{ fontSize: '0.875rem' }}>
                    <span style={{ color: '#64748b' }}>Tệp minh chứng: </span>
                    <strong style={{ color: '#0f172a' }}>{detail.file_original_name || 'Tệp minh chứng'}</strong> ({detail.file_mime_type || 'application/octet-stream'})
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'monospace' }}>SHA-256: {detail.file_sha256}</div>
                  </div>
                  <a
                    href={`/api/v1/files/${detail.evidence_file_id}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', padding: '0.4rem 0.75rem', borderRadius: '4px', backgroundColor: '#eff6ff', color: '#1e40af', textDecoration: 'none', fontSize: '0.8rem', fontWeight: 600, border: '1px solid #bfdbfe' }}
                  >
                    <ExternalLink size={14} /> Mở tệp gốc
                  </a>
                </div>

                {/* Side-by-Side Comparison */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                  {/* Left: BCS Decision */}
                  <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', backgroundColor: '#fafafa' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0f172a', marginBottom: '0.75rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
                      🧑‍🏫 Quyết định của Ban cán sự
                    </div>
                    <div style={{ marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Quyết định: </span>
                      {renderBcsDecisionBadge(detail.bcs_decision)}
                    </div>
                    <div style={{ marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Lý do của BCS:</span>
                      <div style={{ fontSize: '0.875rem', color: '#1e293b', backgroundColor: '#ffffff', padding: '0.5rem', borderRadius: '4px', border: '1px solid #e2e8f0', marginTop: '0.2rem' }}>
                        {detail.bcs_reason}
                      </div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      Người duyệt: <strong>{detail.reviewer_name || 'BCS'}</strong> lúc {new Date(detail.reviewed_at).toLocaleString('vi-VN')}
                    </div>
                  </div>

                  {/* Right: AI Assessment */}
                  <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', backgroundColor: '#f0f9ff' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0369a1', marginBottom: '0.75rem', borderBottom: '1px solid #bae6fd', paddingBottom: '0.5rem' }}>
                      🤖 Kết luận của Mô hình AI
                    </div>
                    <div style={{ marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Kết luận AI: </span>
                      {renderVerdictBadge(detail.ai_verdict)}
                    </div>
                    <div style={{ marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Nhận xét / Căn cứ AI:</span>
                      <div style={{ fontSize: '0.875rem', color: '#1e293b', backgroundColor: '#ffffff', padding: '0.5rem', borderRadius: '4px', border: '1px solid #bae6fd', marginTop: '0.2rem' }}>
                        {detail.ai_reason || <span style={{ color: '#94a3b8' }}>(Không có kết quả phân tích AI phù hợp)</span>}
                      </div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      Mô hình: <strong>{detail.ai_model || 'N/A'}</strong> (Prompt: {detail.ai_prompt_version || 'N/A'})
                    </div>
                  </div>
                </div>

                {/* Audit History Timeline */}
                {detail.audit_history && detail.audit_history.length > 0 && (
                  <div style={{ marginBottom: '1.5rem', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', backgroundColor: '#ffffff' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.75rem' }}>
                      <History size={16} /> Lịch sử thay đổi quyết định & kiểm tra vết
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {detail.audit_history.map((ev, idx) => (
                        <div key={idx} style={{ fontSize: '0.8rem', color: '#475569', padding: '0.4rem 0.6rem', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
                          <span style={{ fontWeight: 600 }}>{ev.action}</span> bởi <strong>{ev.actor_name}</strong> lúc {ev.created_at ? new Date(ev.created_at).toLocaleString('vi-VN') : ''}
                          {ev.before && ev.before.decision && (
                            <span style={{ marginLeft: '0.5rem', color: '#94a3b8' }}>
                              (Trước: {ev.before.decision})
                            </span>
                          )}
                          {ev.after && ev.after.decision && (
                            <span style={{ marginLeft: '0.5rem', color: '#2563eb' }}>
                              → Mới: {ev.after.decision}
                            </span>
                          )}
                          {ev.after && ev.after.ground_truth_label && (
                            <span style={{ marginLeft: '0.5rem', color: '#166534' }}>
                              [Nhãn chuẩn: {ev.after.ground_truth_label}]
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Ground Truth Verification Section (Requirement 4) */}
                <div style={{ backgroundColor: '#fefce8', border: '1px solid #fef08a', borderRadius: '8px', padding: '1.25rem' }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#854d0e', display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
                    <ShieldCheck size={18} color="#854d0e" /> Xác nhận Nhãn Chuẩn Độc lập (Ground Truth)
                  </div>
                  <p style={{ fontSize: '0.8rem', color: '#713f12', margin: '0 0 1rem 0' }}>
                    Người phụ trách xem xét minh chứng gốc và đối chiếu quy chế để đưa ra kết luận chuẩn.
                    <strong> Chỉ các ca đã được xác nhận nhãn chuẩn mới được đưa vào tập chỉ số đánh giá chất lượng AI.</strong>
                  </p>

                  <form onSubmit={handleVerify}>
                    <div style={{ marginBottom: '1rem' }}>
                      <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '0.5rem' }}>
                        Nhãn chuẩn độc lập:
                      </label>
                      <div style={{ display: 'flex', gap: '1rem' }}>
                        {(['SUPPORTED', 'FLAGGED', 'UNKNOWN'] as GroundTruthLabel[]).map((label) => (
                          <label key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.875rem' }}>
                            <input
                              type="radio"
                              name="ground_truth_label"
                              value={label}
                              checked={selectedLabel === label}
                              onChange={() => setSelectedLabel(label)}
                            />
                            <strong>{label}</strong>
                            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                              {label === 'SUPPORTED' ? '(Hợp lệ)' : label === 'FLAGGED' ? '(Vi phạm/Nghi ngờ)' : '(Chưa rõ/Không đủ căn cứ)'}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div style={{ marginBottom: '1rem' }}>
                      <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '0.4rem' }}>
                        Căn cứ / Lý do xác nhận nhãn chuẩn (bắt buộc):
                      </label>
                      <textarea
                        value={verifyReason}
                        onChange={(e) => setVerifyReason(e.target.value)}
                        placeholder="Nêu rõ điều khoản quy chế, kiểm tra mã số sinh viên, danh sách công khai ngoài trường hoặc nguồn xác minh..."
                        rows={3}
                        style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.875rem', boxSizing: 'border-box' }}
                        required
                      />
                    </div>

                    {verifyError && (
                      <div style={{ color: '#b91c1c', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                        {verifyError}
                      </div>
                    )}
                    {verifySuccess && (
                      <div style={{ color: '#15803d', fontSize: '0.85rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <CheckCircle2 size={16} /> {verifySuccess}
                      </div>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                      <button
                        type="button"
                        onClick={() => { setSelectedId(null); setDetail(null); }}
                        style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: '1px solid #cbd5e1', backgroundColor: '#ffffff', cursor: 'pointer', fontSize: '0.875rem' }}
                      >
                        Đóng
                      </button>
                      <button
                        type="submit"
                        disabled={submittingVerify}
                        style={{ padding: '0.5rem 1.25rem', borderRadius: '6px', border: 'none', backgroundColor: '#059669', color: '#ffffff', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 600 }}
                      >
                        {submittingVerify ? 'Đang lưu...' : 'Lưu Nhãn Chuẩn'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
