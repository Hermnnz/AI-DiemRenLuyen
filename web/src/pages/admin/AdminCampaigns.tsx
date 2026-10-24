import React, { useState, useEffect } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { api } from '../../api/client';
import { Campaign, Criterion } from '../../api/types';
import { staffStore } from '../../components/staff/mockStaffData';
import {
  Settings,
  Lock,
  Plus,
  Trash2,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Send,
  Save,
} from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';

export const AdminCampaigns: React.FC = () => {
  const [campaign, setCampaign] = useState<Campaign>(staffStore.getCampaign());
  const [loading, setLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Form states
  const [title, setTitle] = useState(campaign.title);
  const [term, setTerm] = useState(campaign.term);
  const [openAt, setOpenAt] = useState(
    campaign.open_at ? new Date(campaign.open_at).toISOString().slice(0, 16) : ''
  );
  const [deadlineAt, setDeadlineAt] = useState(
    campaign.submission_deadline_at
      ? new Date(campaign.submission_deadline_at).toISOString().slice(0, 16)
      : ''
  );
  const [supplementHours, setSupplementHours] = useState(campaign.supplement_period_hours || 48);
  const [appealHours, setAppealHours] = useState(campaign.appeal_period_hours || 72);
  const [reminderHours, setReminderHours] = useState(campaign.reminder_after_hours || 48);
  const [maxInfoRounds, setMaxInfoRounds] = useState(campaign.max_info_rounds || 2);
  const [maxProofRounds, setMaxProofRounds] = useState(campaign.max_proof_rounds || 2);
  const [criteria, setCriteria] = useState<Criterion[]>(campaign.criteria || []);

  // Modal confirm
  const [showOpenConfirm, setShowOpenConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Alerts
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadCampaign = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const list = await api.get<Campaign[]>('/admin/campaigns');
      if (list && list.length > 0) {
        const first = list[0];
        setCampaign(first);
        syncForm(first);
      }
    } catch (err: unknown) {
      if (isDemoMode) {
        const mock = staffStore.getCampaign();
        setCampaign(mock);
        syncForm(mock);
      } else {
        const errObj = err as { error?: { message?: string }; message?: string };
        setErrorMsg(errObj?.error?.message || errObj?.message || 'Không thể tải danh sách đợt đánh giá.');
      }
    } finally {
      setLoading(false);
    }
  };

  const syncForm = (c: Campaign) => {
    setTitle(c.title);
    setTerm(c.term);
    setOpenAt(c.open_at ? new Date(c.open_at).toISOString().slice(0, 16) : '');
    setDeadlineAt(
      c.submission_deadline_at ? new Date(c.submission_deadline_at).toISOString().slice(0, 16) : ''
    );
    setSupplementHours(c.supplement_period_hours);
    setAppealHours(c.appeal_period_hours);
    setReminderHours(c.reminder_after_hours);
    setMaxInfoRounds(c.max_info_rounds);
    setMaxProofRounds(c.max_proof_rounds);
    setCriteria(c.criteria || []);
  };

  useEffect(() => {
    loadCampaign();
  }, []);

  const isDraft = campaign.status === 'DRAFT';

  // Criteria handlers
  const handleAddCriterion = () => {
    const nextOrder = criteria.length + 1;
    const newCode = `TC0${nextOrder}`;
    const newCrit: Criterion = {
      id: `crit-new-${Date.now()}`,
      campaign_id: campaign.id,
      code: newCode,
      title: `Tiêu chí mới ${nextOrder}`,
      description: 'Mô tả tiêu chí minh họa',
      max_score: '10.00',
      requires_evidence: true,
      sort_order: nextOrder,
    };
    setCriteria([...criteria, newCrit]);
  };

  const handleUpdateCriterion = (index: number, updated: Partial<Criterion>) => {
    const copy = [...criteria];
    copy[index] = { ...copy[index], ...updated };
    setCriteria(copy);
  };

  const handleRemoveCriterion = (index: number) => {
    if (criteria.length <= 1) {
      setErrorMsg('Đợt đánh giá phải có ít nhất 1 tiêu chí.');
      return;
    }
    const copy = criteria.filter((_, i) => i !== index);
    setCriteria(copy);
  };

  // Validation
  const validateForm = (): string | null => {
    if (!title.trim()) return 'Vui lòng nhập tên đợt đánh giá.';
    if (!term.trim()) return 'Vui lòng nhập mã học kỳ.';
    if (!openAt) return 'Vui lòng nhập thời gian mở nộp hồ sơ.';
    if (!deadlineAt) return 'Vui lòng nhập hạn nộp hồ sơ.';

    const openDate = new Date(openAt);
    const deadlineDate = new Date(deadlineAt);
    if (openDate >= deadlineDate) {
      return 'Ràng buộc thời gian vi phạm: Thời gian mở (open_at) phải trước Hạn nộp hồ sơ (submission_deadline_at).';
    }

    if (reminderHours <= 0 || reminderHours >= appealHours) {
      return `Ràng buộc thông báo: Thời gian nhắc hạn (${reminderHours}h) phải lớn hơn 0 và nhỏ hơn thời hạn phản hồi khiếu nại (${appealHours}h).`;
    }

    if (maxInfoRounds < 0 || maxProofRounds < 0) {
      return 'Giới hạn số lượt bổ sung phải lớn hơn hoặc bằng 0.';
    }

    if (criteria.length === 0) {
      return 'Cần thiết lập ít nhất 1 tiêu chí chấm điểm.';
    }

    for (const cr of criteria) {
      const max = parseFloat(cr.max_score);
      if (isNaN(max) || max <= 0) {
        return `Tiêu chí [${cr.code}] có điểm tối đa không hợp lệ (${cr.max_score}).`;
      }
    }

    return null;
  };

  const handleSaveConfig = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    const valErr = validateForm();
    if (valErr) {
      setErrorMsg(valErr);
      return;
    }

    const payload = {
      class_id: campaign.class_id,
      title: title.trim(),
      term: term.trim(),
      open_at: new Date(openAt).toISOString(),
      submission_deadline_at: new Date(deadlineAt).toISOString(),
      supplement_period_hours: Number(supplementHours),
      appeal_period_hours: Number(appealHours),
      reminder_after_hours: Number(reminderHours),
      max_info_rounds: Number(maxInfoRounds),
      max_proof_rounds: Number(maxProofRounds),
      criteria,
    };

    try {
      setSubmitting(true);
      if (isDemoMode) {
        staffStore.updateCampaign(payload);
      } else {
        await api.put(`/admin/campaigns/${campaign.id}`, payload);
      }
      setSuccessMsg('Đã lưu cấu hình đợt đánh giá thành công.');
      setIsEditing(false);
      await loadCampaign();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message || (err as { message?: string })?.message || 'Lỗi khi lưu cấu hình.';
      setErrorMsg(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenCampaign = async () => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      let statusResult: string;
      if (isDemoMode) {
        const res = staffStore.openCampaign();
        statusResult = res.status;
      } else {
        const res = await api.post<{ id: string; status: string }>(`/admin/campaigns/${campaign.id}/open`);
        statusResult = res.status;
      }
      setShowOpenConfirm(false);
      setSuccessMsg(
        statusResult === 'SCHEDULED'
          ? 'Đợt đánh giá đã được chuyển sang trạng thái ĐÃ LÊN LỊCH (SCHEDULED). Khi đến open_at, hệ thống sẽ tự động mở đợt và tạo hồ sơ cho sinh viên.'
          : 'Đợt đánh giá đã chính thức MỞ (OPEN). Sinh viên trong lớp đã có thể đăng nhập để tự chấm và nộp hồ sơ!'
      );
      await loadCampaign();
    } catch (err: unknown) {
      const msg = (err as { error?: { message?: string }; message?: string })?.error?.message || (err as { message?: string })?.message || 'Lỗi khi lên lịch/mở đợt.';
      setErrorMsg(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* 1. Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
            Quản trị Cấu hình Đợt Đánh giá
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Khởi tạo đợt, thiết lập thời hạn, trần số lượt bổ sung và bộ tiêu chí cho lớp
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {isDraft ? (
            <button
              type="button"
              disabled={submitting}
              onClick={() => setShowOpenConfirm(true)}
              className="btn btn-primary"
            >
              <Send size={15} /> Lên lịch / Mở đợt
            </button>
          ) : (
            <div className="badge badge-neutral" style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Lock size={14} /> Tiêu chí & Cấu hình đã khóa
            </div>
          )}
        </div>
      </div>

      {/* Alerts */}
      {errorMsg && (
        <div
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#991b1b',
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div
          style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #a7f3d0',
            color: '#065f46',
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* 2. Main Config Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#1e40af' }}>
                {campaign.title}
              </h3>
              <StatusBadge status={campaign.status} />
            </div>
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.25rem' }}>
              Mã học kỳ: <strong>{campaign.term}</strong> | Lớp quản lý: <strong>LOP-DEMO</strong>
            </p>
          </div>

          {isDraft && !isEditing && (
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="btn btn-secondary"
              style={{ fontSize: '0.825rem' }}
            >
              Chỉnh sửa thông số
            </button>
          )}
        </div>

        {/* Locked warning notice if not DRAFT */}
        {!isDraft && (
          <div
            style={{
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              fontSize: '0.825rem',
              color: '#475569',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <Lock size={16} color="#64748b" />
            <span>
              Đợt đánh giá đã ở trạng thái <strong>{campaign.status}</strong>. Theo quy tắc nghiệp vụ V1, toàn bộ tiêu chí, thời hạn và trần lượt bổ sung đã được khóa bất biến nhằm đảm bảo công bằng cho sinh viên.
            </span>
          </div>
        )}

        {/* Thông số thời gian & trần bổ sung */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '1rem',
            marginBottom: '1.5rem',
          }}
        >
          {/* Thời gian mở nộp */}
          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
              Thời gian mở nộp hồ sơ (open_at):
            </label>
            {isDraft && isEditing ? (
              <input
                type="datetime-local"
                value={openAt}
                onChange={(e) => setOpenAt(e.target.value)}
                style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              />
            ) : (
              <Deadline isoString={campaign.open_at} label="Mở" />
            )}
          </div>

          {/* Hạn nộp hồ sơ */}
          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
              Hạn nộp hồ sơ (submission_deadline_at):
            </label>
            {isDraft && isEditing ? (
              <input
                type="datetime-local"
                value={deadlineAt}
                onChange={(e) => setDeadlineAt(e.target.value)}
                style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              />
            ) : (
              <Deadline isoString={campaign.submission_deadline_at} label="Hạn" />
            )}
          </div>

          {/* Trần lượt bổ sung */}
          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
              Trần lượt bổ sung (max rounds):
            </label>
            {isDraft && isEditing ? (
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="number"
                  min="0"
                  value={maxInfoRounds}
                  onChange={(e) => setMaxInfoRounds(parseInt(e.target.value, 10))}
                  placeholder="INFO"
                  style={{ width: '70px', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                />
                <input
                  type="number"
                  min="0"
                  value={maxProofRounds}
                  onChange={(e) => setMaxProofRounds(parseInt(e.target.value, 10))}
                  placeholder="PROOF"
                  style={{ width: '70px', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                />
              </div>
            ) : (
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#0f172a' }}>
                INFO: {campaign.max_info_rounds} lượt · PROOF: {campaign.max_proof_rounds} lượt
              </div>
            )}
          </div>

          {/* Thời hạn phản hồi / nhắc hạn */}
          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
              Thời hạn khiếu nại & Nhắc nhở:
            </label>
            {isDraft && isEditing ? (
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.825rem' }}>
                <input
                  type="number"
                  min="1"
                  value={appealHours}
                  onChange={(e) => setAppealHours(parseInt(e.target.value, 10))}
                  style={{ width: '65px', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                />
                <span>giờ khiếu nại (nhắc sau</span>
                <input
                  type="number"
                  min="1"
                  value={reminderHours}
                  onChange={(e) => setReminderHours(parseInt(e.target.value, 10))}
                  style={{ width: '65px', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                />
                <span>h)</span>
              </div>
            ) : (
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#0f172a' }}>
                Khiếu nại: {campaign.appeal_period_hours}h · Nhắc hạn sau: {campaign.reminder_after_hours}h
              </div>
            )}
          </div>
        </div>

        {/* 3. Danh sách Tiêu chí Đánh giá */}
        <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>
              Bộ Tiêu chí Đánh giá ({criteria.length} tiêu chí)
            </h4>
            {isDraft && (
              <button
                type="button"
                onClick={handleAddCriterion}
                className="btn btn-secondary"
                style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
              >
                <Plus size={14} /> Thêm tiêu chí
              </button>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {criteria.map((cr, idx) => (
              <div
                key={cr.id || idx}
                style={{
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '0.85rem',
                  backgroundColor: '#ffffff',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#1e40af' }}>
                      #{cr.sort_order}
                    </span>
                    {isDraft && isEditing ? (
                      <input
                        type="text"
                        value={cr.code}
                        onChange={(e) => handleUpdateCriterion(idx, { code: e.target.value })}
                        placeholder="Mã (TC01)"
                        style={{ width: '80px', padding: '0.3rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                      />
                    ) : (
                      <strong style={{ fontSize: '0.95rem' }}>[{cr.code}]</strong>
                    )}

                    {isDraft && isEditing ? (
                      <input
                        type="text"
                        value={cr.title}
                        onChange={(e) => handleUpdateCriterion(idx, { title: e.target.value })}
                        placeholder="Tên tiêu chí"
                        style={{ flex: 1, minWidth: '200px', padding: '0.3rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                      />
                    ) : (
                      <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{cr.title}</span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem' }}>
                      <span style={{ color: '#64748b' }}>Tối đa:</span>
                      {isDraft && isEditing ? (
                        <input
                          type="text"
                          value={cr.max_score}
                          onChange={(e) => handleUpdateCriterion(idx, { max_score: e.target.value })}
                          style={{ width: '70px', padding: '0.3rem', borderRadius: '4px', border: '1px solid #cbd5e1', textAlign: 'right', fontSize: '0.85rem' }}
                        />
                      ) : (
                        <strong style={{ color: '#0f172a' }}>{cr.max_score} đ</strong>
                      )}
                    </div>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', cursor: isDraft && isEditing ? 'pointer' : 'default' }}>
                      <input
                        type="checkbox"
                        disabled={!isDraft || !isEditing}
                        checked={cr.requires_evidence}
                        onChange={(e) => handleUpdateCriterion(idx, { requires_evidence: e.target.checked })}
                      />
                      <span>Cần minh chứng</span>
                    </label>

                    {isDraft && isEditing && (
                      <button
                        type="button"
                        onClick={() => handleRemoveCriterion(idx)}
                        style={{ background: 'transparent', border: 'none', color: '#dc2626', cursor: 'pointer', padding: '0.2rem' }}
                        title="Xóa tiêu chí"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </div>

                {isDraft && isEditing ? (
                  <input
                    type="text"
                    value={cr.description || ''}
                    onChange={(e) => handleUpdateCriterion(idx, { description: e.target.value })}
                    placeholder="Mô tả hướng dẫn cho tiêu chí..."
                    style={{ width: '100%', padding: '0.3rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.8rem' }}
                  />
                ) : (
                  cr.description && (
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      {cr.description}
                    </div>
                  )
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Save Bar if Editing */}
        {isDraft && isEditing && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.25rem', borderTop: '1px solid #f1f5f9', paddingTop: '1rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                syncForm(campaign);
                setIsEditing(false);
              }}
            >
              Hủy chỉnh sửa
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={submitting}
              onClick={handleSaveConfig}
            >
              <Save size={15} /> {submitting ? 'Đang lưu...' : 'Lưu cấu hình'}
            </button>
          </div>
        )}
      </div>

      {/* Modal Confirm Lên lịch / Mở đợt */}
      <ConfirmDialog
        isOpen={showOpenConfirm}
        title="Xác nhận Lên lịch / Mở đợt đánh giá"
        message="Hành động này sẽ khóa vĩnh viễn cấu hình tiêu chí và thời hạn của đợt. Nếu thời gian open_at đã tới, đợt sẽ mở ngay và tạo hồ sơ cho tất cả sinh viên trong lớp. Bạn có chắc chắn muốn tiếp tục?"
        confirmLabel="Tiến hành Lên lịch/Mở"
        onConfirm={handleOpenCampaign}
        onCancel={() => setShowOpenConfirm(false)}
      />
    </div>
  );
};
