import React, { useState, useEffect, useRef } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { Deadline } from '../../components/Deadline';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { EmptyPanel, LoadingPanel } from '../../components/UiStates';
import { api } from '../../api/client';
import { Campaign, Criterion, EvaluationTemplate } from '../../api/types';
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
  GraduationCap,
  Layers,
  X,
  FileSpreadsheet,
} from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';
const toLocalDateTimeInput = (value: Date | string): string => {
  const date = value instanceof Date ? value : new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
};
const demoTemplates: EvaluationTemplate[] = [
  {
    id: 'tpl-1', code: '49K14_1_V1', name: 'Bộ quy tắc toàn trường (5 mục, 23 dòng, 100 điểm)',
    version: '1.0.0', description: 'Bộ tiêu chí rèn luyện minh họa',
    total_max_score: '100.00', is_active: true,
  },
  {
    id: 'tpl-2', code: 'LEGACY_DEMO', name: 'Mẫu minh họa Demo cũ (TC01-TC03)',
    version: '0.1.0', description: '3 tiêu chí minh họa thử nghiệm',
    total_max_score: '30.00', is_active: true,
  },
];

export const AdminCampaigns: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaign, setCampaign] = useState<Campaign>(staffStore.getCampaign());
  const [hasCampaign, setHasCampaign] = useState(isDemoMode);
  const [templates, setTemplates] = useState<EvaluationTemplate[]>([]);
  const [templatesLoaded, setTemplatesLoaded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  // Form states
  const [title, setTitle] = useState(campaign.title);
  const [term, setTerm] = useState(campaign.term);
  const [termStartOn, setTermStartOn] = useState(campaign.term_start_on || '');
  const [termEndOn, setTermEndOn] = useState(campaign.term_end_on || '');
  const [openAt, setOpenAt] = useState(
    campaign.open_at ? toLocalDateTimeInput(campaign.open_at) : ''
  );
  const [deadlineAt, setDeadlineAt] = useState(
    campaign.submission_deadline_at
      ? toLocalDateTimeInput(campaign.submission_deadline_at)
      : ''
  );
  const [supplementHours, setSupplementHours] = useState(campaign.supplement_period_hours || 48);
  const [appealHours, setAppealHours] = useState(campaign.appeal_period_hours || 72);
  const [reminderHours, setReminderHours] = useState(campaign.reminder_after_hours || 48);
  const [maxInfoRounds, setMaxInfoRounds] = useState(campaign.max_info_rounds || 2);
  const [maxProofRounds, setMaxProofRounds] = useState(campaign.max_proof_rounds || 2);
  const [criteria, setCriteria] = useState<Criterion[]>(campaign.criteria || []);

  // Modal Create Campaign
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState(isDemoMode ? 'Đánh giá kết quả rèn luyện HK2 2025-2026' : '');
  const [newClassId, setNewClassId] = useState(isDemoMode ? 'lop-49k14-1' : '');
  const [newTerm, setNewTerm] = useState(isDemoMode ? 'HK2-2025-2026' : '');
  const [createErrors, setCreateErrors] = useState<Record<string, string>>({});
  const clearCreateError = (field: string) =>
    setCreateErrors((previous) => {
      if (!previous[field]) return previous;
      const next = { ...previous };
      delete next[field];
      return next;
    });
  const [newTermStartOn, setNewTermStartOn] = useState('');
  const [newTermEndOn, setNewTermEndOn] = useState('');
  const [newTemplateCode, setNewTemplateCode] = useState(isDemoMode ? '49K14_1_V1' : '');
  const [newOpenAt, setNewOpenAt] = useState(toLocalDateTimeInput(new Date()));
  const [newDeadlineAt, setNewDeadlineAt] = useState(
    toLocalDateTimeInput(new Date(Date.now() + 14 * 24 * 3600 * 1000))
  );

  // Modal GPA Import
  const [showGpaModal, setShowGpaModal] = useState(false);
  const [gpaText, setGpaText] = useState(isDemoMode ?
    JSON.stringify(
      [
        { student_id: 'sv001', gpa: 3.45 },
        { student_id: 'sv002', gpa: 2.85 },
        { student_id: 'bcs001', gpa: 3.6 },
      ],
      null,
      2
    ) : ''
  );

  // Modal confirm
  const [showOpenConfirm, setShowOpenConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const createLock = useRef(false);

  // Alerts
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setErrorMsg(null);
    setTemplatesLoaded(false);
    setTemplateError(null);
    try {
      // 1. Load campaigns
      const list = await api.get<Campaign[]>('/admin/campaigns');
      setCampaigns(list || []);
      if (list && list.length > 0) {
        // Ưu tiên chọn campaign hiện tại nếu có
        const found = list.find((c) => c.id === campaign.id) || list[0];
        setCampaign(found);
        syncForm(found);
        setHasCampaign(true);
      } else if (!isDemoMode) {
        setHasCampaign(false);
      }

      // 2. Load templates
      try {
        const tpls = await api.get<EvaluationTemplate[]>('/admin/evaluation-templates');
        const available = tpls?.length ? tpls : (isDemoMode ? demoTemplates : []);
        setTemplates(available);
        setTemplatesLoaded(true);
        setNewTemplateCode((previous) =>
          available.some((template) => template.code === previous) ? previous : (available[0]?.code || '')
        );
        setTemplateError(null);
      } catch {
        if (isDemoMode) {
          setTemplates(demoTemplates);
          setTemplatesLoaded(true);
        } else {
          setTemplates([]);
          setTemplateError('Không tải được mẫu quy tắc. Hãy thử tải lại trước khi tạo đợt mới.');
        }
      }
    } catch (err: unknown) {
      if (isDemoMode) {
        const mock = staffStore.getCampaign();
        setCampaign(mock);
        syncForm(mock);
        setHasCampaign(true);
        setTemplates(demoTemplates);
        setTemplatesLoaded(true);
      } else {
        setHasCampaign(false);
        setCampaigns([]);
        setTemplates([]);
        const errObj = err as { error?: { message?: string }; message?: string };
        const message = errObj?.error?.message || errObj?.message;
        setErrorMsg(message && message !== 'Internal Server Error'
          ? message
          : 'Máy chủ chưa trả được danh sách đợt đánh giá. Hãy tải lại; nếu lỗi vẫn xảy ra, báo quản trị hệ thống.');
      }
    } finally {
      setLoading(false);
    }
  };

  const syncForm = (c: Campaign) => {
    setTitle(c.title);
    setTerm(c.term);
    setTermStartOn(c.term_start_on || '');
    setTermEndOn(c.term_end_on || '');
    setOpenAt(c.open_at ? toLocalDateTimeInput(c.open_at) : '');
    setDeadlineAt(
      c.submission_deadline_at ? toLocalDateTimeInput(c.submission_deadline_at) : ''
    );
    setSupplementHours(c.supplement_period_hours);
    setAppealHours(c.appeal_period_hours);
    setReminderHours(c.reminder_after_hours);
    setMaxInfoRounds(c.max_info_rounds);
    setMaxProofRounds(c.max_proof_rounds);
    setCriteria(c.criteria || []);
  };

  useEffect(() => {
    loadData();
  }, []);

  const isDraft = hasCampaign && campaign.status === 'DRAFT';
  const canEdit = hasCampaign && ['DRAFT', 'SCHEDULED', 'OPEN', 'REVIEW'].includes(campaign.status);

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
    if (Boolean(termStartOn) !== Boolean(termEndOn)) return 'Cần nhập cả ngày bắt đầu và kết thúc học kỳ.';
    if (termStartOn && termStartOn > termEndOn) return 'Ngày bắt đầu học kỳ phải trước ngày kết thúc.';
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
    const validationErr = validateForm();
    if (validationErr) {
      setErrorMsg(validationErr);
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg(null);
      setSuccessMsg(null);

      const payload = {
        class_id: campaign.class_id,
        title: title.trim(),
        term: term.trim(),
        template_code: campaign.template_code,
        term_start_on: termStartOn || null,
        term_end_on: termEndOn || null,
        open_at: new Date(openAt).toISOString(),
        submission_deadline_at: new Date(deadlineAt).toISOString(),
        supplement_period_hours: supplementHours,
        appeal_period_hours: appealHours,
        reminder_after_hours: reminderHours,
        max_info_rounds: maxInfoRounds,
        max_proof_rounds: maxProofRounds,
        criteria: criteria.map((c, idx) => ({
          id: c.id.startsWith('crit-new-') ? undefined : c.id,
          code: c.code.trim(),
          section_code: c.section_code ?? null,
          section_title: c.section_title ?? null,
          section_max_score: c.section_max_score ?? null,
          title: c.title.trim(),
          description: c.description ? c.description.trim() : null,
          max_score: parseFloat(c.max_score).toFixed(2),
          requires_evidence: c.requires_evidence,
          evidence_notes: c.evidence_notes ?? null,
          allowed_input_roles: c.allowed_input_roles ?? null,
          rule_config: c.rule_config ?? null,
          sort_order: idx + 1,
        })),
      };

      if (isDemoMode) {
        staffStore.updateCampaign({
          ...campaign,
          ...payload,
          criteria: criteria.map((c, idx) => ({ ...c, sort_order: idx + 1 })),
        });
      } else {
        await api.put(`/admin/campaigns/${campaign.id}`, payload);
      }

      setSuccessMsg('Đã lưu cấu hình đợt đánh giá thành công.');
      setIsEditing(false);
      await loadData();
    } catch (err: unknown) {
      const msg =
        (err as { error?: { message?: string }; message?: string })?.error?.message ||
        (err as { message?: string })?.message ||
        'Lỗi khi lưu cấu hình.';
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
      await loadData();
    } catch (err: unknown) {
      const msg =
        (err as { error?: { message?: string }; message?: string })?.error?.message ||
        (err as { message?: string })?.message ||
        'Lỗi khi lên lịch/mở đợt.';
      setErrorMsg(msg);
    } finally {
      setSubmitting(false);
    }
  };

  // Tạo đợt mới với template lựa chọn
  const handleCreateCampaign = async () => {
    if (createLock.current) return;
    try {
      const errors: Record<string, string> = {};
      if (!newTitle.trim()) errors.title = 'Nhập tên đợt đánh giá.';
      if (!newClassId.trim()) errors.classId = 'Nhập mã lớp sẽ tham gia đợt này.';
      if (!newTerm.trim()) errors.term = 'Nhập mã học kỳ.';
      if (!newTemplateCode || !templates.some((tpl) => tpl.code === newTemplateCode)) {
        errors.template = 'Chọn mẫu quy tắc có trong danh sách.';
      }
      if (Boolean(newTermStartOn) !== Boolean(newTermEndOn) ||
          (newTermStartOn && newTermStartOn > newTermEndOn)) {
        errors.termDates = 'Nhập đủ hai ngày học kỳ và bảo đảm ngày kết thúc sau ngày bắt đầu.';
      }
      if (!newOpenAt || !newDeadlineAt ||
          !Number.isFinite(new Date(newOpenAt).getTime()) ||
          !Number.isFinite(new Date(newDeadlineAt).getTime()) ||
          new Date(newDeadlineAt).getTime() <= new Date(newOpenAt).getTime()) {
        errors.deadline = 'Hạn nộp phải sau thời điểm mở đợt.';
      }
      setCreateErrors(errors);
      if (Object.keys(errors).length > 0) return;
      createLock.current = true;
      setSubmitting(true);
      setErrorMsg(null);
      setSuccessMsg(null);

      const payload = {
        title: newTitle.trim(),
        class_id: newClassId.trim(),
        term: newTerm.trim(),
        term_start_on: newTermStartOn || null,
        term_end_on: newTermEndOn || null,
        template_code: newTemplateCode,
        open_at: new Date(newOpenAt).toISOString(),
        submission_deadline_at: new Date(newDeadlineAt).toISOString(),
        supplement_period_hours: 48,
        appeal_period_hours: 72,
        reminder_after_hours: 48,
        max_info_rounds: 2,
        max_proof_rounds: 2,
      };

      const res = await api.post<Campaign>('/admin/campaigns', payload);
      setShowCreateModal(false);
      setSuccessMsg(
        `Đã tạo thành công đợt đánh giá mới "${res.title}" áp dụng mẫu quy tắc [${newTemplateCode}]!`
      );
      await loadData();
    } catch (err: unknown) {
      const msg =
        (err as { error?: { message?: string }; message?: string })?.error?.message ||
        (err as { message?: string })?.message ||
        'Lỗi khi tạo đợt mới.';
      setErrorMsg(msg);
    } finally {
      setSubmitting(false);
      createLock.current = false;
    }
  };

  // Import GPA
  const handleImportGpa = async () => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      setSuccessMsg(null);

      let items: Array<{ student_id: string; gpa: number }> = [];
      try {
        items = JSON.parse(gpaText);
      } catch {
        // Parse line format: "student_id: gpa" or "student_id, gpa"
        const lines = gpaText.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          const parts = trimmed.split(/[:, \t]+/);
          if (parts.length >= 2) {
            const sid = parts[0].trim();
            const gpaNum = parseFloat(parts[1].trim());
            if (sid && !isNaN(gpaNum)) {
              items.push({ student_id: sid, gpa: gpaNum });
            }
          }
        }
      }

      if (!items || items.length === 0) {
        setErrorMsg('Vui lòng nhập danh sách điểm GPA hợp lệ (JSON hoặc dòng: mã_sv gpa).');
        setSubmitting(false);
        return;
      }

      const res = await api.post<{
        imported_count: number;
        audit_log: string;
        details: Array<{ student_id: string; gpa: number; converted_score: string }>;
      }>(`/admin/campaigns/${campaign.id}/academic-scores`, { items });

      setShowGpaModal(false);
      setSuccessMsg(
        `Đã nhập và quy đổi tự động thành công cho ${res.imported_count} sinh viên (Điều 4e). Ghi nhận nhật ký kiểm toán [${res.audit_log}].`
      );
      await loadData();
    } catch (err: unknown) {
      const msg =
        (err as { error?: { message?: string }; message?: string })?.error?.message ||
        (err as { message?: string })?.message ||
        'Lỗi khi nhập điểm GPA.';
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
            Khởi tạo, mở và cập nhật đợt đánh giá; mọi thay đổi tiêu chí đều được ghi lịch sử
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {hasCampaign && <button
            type="button"
            onClick={() => setShowGpaModal(true)}
            className="btn btn-secondary"
            style={{ fontSize: '0.85rem' }}
            title="Nhập điểm GPA học kỳ để hệ thống tự động quy đổi Điều 4e"
          >
            <GraduationCap size={15} color="#2563eb" /> Nhập điểm GPA học kỳ
          </button>}

          <button
            type="button"
            disabled={loading || templates.length === 0}
            onClick={() => setShowCreateModal(true)}
            className="btn btn-secondary"
            style={{ fontSize: '0.85rem' }}
            title="Tạo đợt đánh giá mới và chọn mẫu quy tắc"
          >
            <Plus size={15} /> Tạo đợt mới
          </button>

          {isDraft ? (
            <button
              type="button"
              disabled={submitting}
              onClick={() => setShowOpenConfirm(true)}
              className="btn btn-primary"
            >
              <Send size={15} /> Lên lịch / Mở đợt
            </button>
          ) : hasCampaign && !canEdit ? (
            <div className="badge badge-neutral" style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Lock size={14} /> Đợt đã công bố hoặc kết thúc
            </div>
          ) : null}
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

      {templateError && <p role="alert" style={{ color: '#b91c1c', fontSize: '0.875rem' }}>{templateError}</p>}
      {!loading && templatesLoaded && templates.length === 0 && !templateError && (
        <p role="status" style={{ color: '#92400e', fontSize: '0.875rem' }}>
          Chưa có mẫu quy tắc để tạo đợt mới. Hãy cấu hình mẫu trước khi tiếp tục.
        </p>
      )}

      {/* Danh sách chọn đợt nếu có nhiều hơn 1 campaign */}
      {campaigns.length > 1 && (
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569' }}>Chọn đợt:</span>
          {campaigns.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => {
                setCampaign(c);
                syncForm(c);
              }}
              style={{
                padding: '0.3rem 0.75rem',
                fontSize: '0.8rem',
                fontWeight: c.id === campaign.id ? 700 : 500,
                backgroundColor: c.id === campaign.id ? '#1e40af' : '#ffffff',
                color: c.id === campaign.id ? '#ffffff' : '#334155',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              {c.title} ({c.term})
            </button>
          ))}
        </div>
      )}

      {/* 2. Main Config Card */}
      {loading && !hasCampaign ? (
        <LoadingPanel label="Đang tải cấu hình đợt đánh giá" />
      ) : !hasCampaign ? (
        <EmptyPanel
          title={errorMsg ? 'Chưa tải được đợt đánh giá' : 'Chưa có đợt đánh giá'}
          description={errorMsg
            ? 'Kiểm tra kết nối hoặc quyền truy cập, sau đó tải lại. Dữ liệu minh họa không được dùng thay cho đợt thật.'
            : 'Tạo đợt mới từ mẫu quy tắc đã được duyệt để bắt đầu cấu hình và mở cho sinh viên.'}
        >
          <button type="button" className="btn btn-secondary" onClick={loadData} disabled={loading}>
            Tải lại danh sách
          </button>
        </EmptyPanel>
      ) : <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#1e40af' }}>
                {campaign.title}
              </h3>
              <StatusBadge status={campaign.status} />
              {campaign.template_code && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    backgroundColor: '#e0e7ff',
                    color: '#3730a3',
                    fontWeight: 600,
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                  }}
                >
                  <Layers size={12} /> Mẫu: {campaign.template_code}
                </span>
              )}
            </div>
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.25rem' }}>
              Mã học kỳ: <strong>{campaign.term}</strong> | Lớp: <strong>{campaign.class_id}</strong>
            </p>
          </div>

          {canEdit && !isEditing && (
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

        {/* Active edits require BCS to review affected proposed cases again. */}
        {canEdit && campaign.status !== 'DRAFT' && (
          <div
            style={{
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
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
            <AlertTriangle size={16} color="#b45309" />
            <span>
              Admin được sửa đợt đang {campaign.status}. Nếu sửa tiêu chí, hồ sơ đã có điểm dự kiến sẽ quay lại BCS kiểm tra. Không thể xóa tiêu chí đã có điểm hoặc minh chứng.
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
            {canEdit && isEditing ? (
              <input
                type="datetime-local"
                value={openAt}
                onChange={(e) => setOpenAt(e.target.value)}
                style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              />
            ) : (
              <Deadline isoString={campaign.open_at} label="Mở" kind="start" />
            )}
          </div>

          {/* Hạn nộp hồ sơ */}
          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
              Hạn nộp hồ sơ (submission_deadline_at):
            </label>
            {canEdit && isEditing ? (
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

          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
              Ngày bắt đầu học kỳ (để đối chiếu minh chứng):
            </label>
            {canEdit && isEditing ? (
              <input type="date" value={termStartOn} onChange={(e) => setTermStartOn(e.target.value)}
                style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }} />
            ) : <span>{campaign.term_start_on || 'Chưa cấu hình'}</span>}
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
              Ngày kết thúc học kỳ:
            </label>
            {canEdit && isEditing ? (
              <input type="date" value={termEndOn} onChange={(e) => setTermEndOn(e.target.value)}
                style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }} />
            ) : <span>{campaign.term_end_on || 'Chưa cấu hình'}</span>}
          </div>

          {/* Trần lượt bổ sung */}
          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
              Trần lượt bổ sung (max rounds):
            </label>
            {canEdit && isEditing ? (
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
            {canEdit && isEditing ? (
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
            {canEdit && isEditing && (
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
                    {canEdit && isEditing ? (
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

                    {canEdit && isEditing ? (
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

                    {cr.section_title && (
                      <span style={{ fontSize: '0.75rem', color: '#64748b', backgroundColor: '#f1f5f9', padding: '0.15rem 0.4rem', borderRadius: '3px' }}>
                        {cr.section_title}
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem' }}>
                      <span style={{ color: '#64748b' }}>Tối đa:</span>
                      {canEdit && isEditing ? (
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

                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', cursor: canEdit && isEditing ? 'pointer' : 'default' }}>
                      <input
                        type="checkbox"
                        disabled={!canEdit || !isEditing}
                        checked={cr.requires_evidence}
                        onChange={(e) => handleUpdateCriterion(idx, { requires_evidence: e.target.checked })}
                      />
                      <span>Cần minh chứng</span>
                    </label>

                    {canEdit && isEditing && (
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

                {canEdit && isEditing ? (
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
        {canEdit && isEditing && (
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
      </div>}

      {/* Modal Tạo Đợt Đánh Giá Mới */}
      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem',
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '8px',
              maxWidth: '560px',
              width: '100%',
              padding: '1.5rem',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
                Tạo Đợt Đánh Giá Mới
              </h3>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.875rem' }}>
              <div>
                <label htmlFor="create-title" style={{ display: 'block', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
                  Tên đợt đánh giá:
                </label>
                <input
                  id="create-title"
                  type="text"
                  value={newTitle}
                  onChange={(e) => { setNewTitle(e.target.value); clearCreateError('title'); }}
                  aria-invalid={Boolean(createErrors.title)}
                  aria-describedby={createErrors.title ? 'create-title-error' : undefined}
                  style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                />
                {createErrors.title && <span id="create-title-error" className="form-error-text" role="alert">{createErrors.title}</span>}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label htmlFor="create-class" style={{ display: 'block', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
                    Mã lớp:
                  </label>
                  <input
                    id="create-class"
                    type="text"
                    value={newClassId}
                    onChange={(e) => { setNewClassId(e.target.value); clearCreateError('classId'); }}
                    aria-invalid={Boolean(createErrors.classId)}
                    aria-describedby={createErrors.classId ? 'create-class-error' : undefined}
                    style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                  />
                  {createErrors.classId && <span id="create-class-error" className="form-error-text" role="alert">{createErrors.classId}</span>}
                </div>
                <div>
                  <label htmlFor="create-term" style={{ display: 'block', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
                    Mã học kỳ:
                  </label>
                  <input
                    id="create-term"
                    type="text"
                    value={newTerm}
                    onChange={(e) => { setNewTerm(e.target.value); clearCreateError('term'); }}
                    aria-invalid={Boolean(createErrors.term)}
                    aria-describedby={createErrors.term ? 'create-term-error' : undefined}
                    style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                  />
                  {createErrors.term && <span id="create-term-error" className="form-error-text" role="alert">{createErrors.term}</span>}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label htmlFor="create-term-start" style={{ display: 'block', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>Ngày bắt đầu học kỳ:</label>
                  <input id="create-term-start" type="date" value={newTermStartOn} onChange={(e) => { setNewTermStartOn(e.target.value); clearCreateError('termDates'); }}
                    style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }} />
                </div>
                <div>
                  <label htmlFor="create-term-end" style={{ display: 'block', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>Ngày kết thúc học kỳ:</label>
                  <input id="create-term-end" type="date" value={newTermEndOn} onChange={(e) => { setNewTermEndOn(e.target.value); clearCreateError('termDates'); }}
                    style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }} />
                </div>
              </div>
              {createErrors.termDates && <span className="form-error-text" role="alert">{createErrors.termDates}</span>}

              <div>
                <label htmlFor="create-template" style={{ display: 'block', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
                  Mẫu quy tắc chấm (Template):
                </label>
                <select
                  id="create-template"
                  value={newTemplateCode}
                  onChange={(e) => { setNewTemplateCode(e.target.value); clearCreateError('template'); }}
                  aria-invalid={Boolean(createErrors.template)}
                  style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                >
                  {templates.map((tpl) => (
                    <option key={tpl.code} value={tpl.code}>
                      {tpl.name} ({tpl.code} - {tpl.total_max_score}đ)
                    </option>
                  ))}
                </select>
                {createErrors.template && <span className="form-error-text" role="alert">{createErrors.template}</span>}
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                  * Quy tắc và điểm tối đa của campaign sẽ được cố định theo phiên bản đã chọn để việc sửa đổi sau này không làm thay đổi dữ liệu lịch sử.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label htmlFor="create-open" style={{ display: 'block', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
                    Thời gian mở:
                  </label>
                  <input
                    id="create-open"
                    type="datetime-local"
                    value={newOpenAt}
                    onChange={(e) => { setNewOpenAt(e.target.value); clearCreateError('deadline'); }}
                    style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                  />
                </div>
                <div>
                  <label htmlFor="create-deadline" style={{ display: 'block', fontWeight: 600, color: '#475569', marginBottom: '0.3rem' }}>
                    Hạn nộp:
                  </label>
                  <input
                    id="create-deadline"
                    type="datetime-local"
                    value={newDeadlineAt}
                    onChange={(e) => { setNewDeadlineAt(e.target.value); clearCreateError('deadline'); }}
                    style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                  />
                </div>
              </div>
              {createErrors.deadline && <span className="form-error-text" role="alert">{createErrors.deadline}</span>}
            </div>

            {errorMsg && <p role="alert" className="form-error-text" style={{ marginTop: '0.75rem' }}>{errorMsg}</p>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.25rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCreateModal(false)}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={submitting}
                onClick={handleCreateCampaign}
              >
                {submitting ? 'Đang tạo...' : 'Tạo đợt đánh giá'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Nhập Điểm GPA Học Kỳ */}
      {showGpaModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem',
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '8px',
              maxWidth: '600px',
              width: '100%',
              padding: '1.5rem',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <GraduationCap size={20} color="#2563eb" />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
                  Nhập Điểm GPA Học Kỳ (Quy đổi Điều 4e)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowGpaModal(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: '0.825rem', color: '#64748b', marginBottom: '0.75rem' }}>
              Tiêu chí 4e do Nhà trường quy đổi tự động từ điểm GPA (thang 4.0), sinh viên không được phép tự nhập. Nhập danh sách GPA dưới dạng JSON hoặc mỗi dòng một sinh viên: <code>mã_sv gpa</code>.
            </p>

            <div
              style={{
                backgroundColor: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: '6px',
                padding: '0.6rem 0.85rem',
                fontSize: '0.8rem',
                color: '#1e40af',
                marginBottom: '0.75rem',
              }}
            >
              <strong>Bảng thang quy đổi chính thức:</strong>
              <ul style={{ margin: '0.2rem 0 0 1.2rem', padding: 0 }}>
                <li>GPA &ge; 3.20 đến 4.00 &rarr; <strong>4.00 điểm</strong></li>
                <li>GPA &ge; 2.00 đến dưới 3.20 &rarr; <strong>2.00 điểm</strong></li>
                <li>GPA &lt; 2.00 &rarr; <strong>0.00 điểm</strong></li>
              </ul>
            </div>

            <textarea
              rows={8}
              value={gpaText}
              onChange={(e) => setGpaText(e.target.value)}
              style={{
                width: '100%',
                fontFamily: 'monospace',
                fontSize: '0.825rem',
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid #cbd5e1',
              }}
            />

            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.4rem' }}>
              * Thao tác này sẽ ghi nhận nhật ký kiểm toán (Audit Trail: <code>ACADEMIC_SCORES_IMPORTED</code>) gắn với tài khoản ADMIN thực hiện.
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.25rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowGpaModal(false)}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={submitting}
                onClick={handleImportGpa}
              >
                {submitting ? 'Đang cập nhật...' : 'Cập nhật điểm GPA & Quy đổi 4e'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Confirm Lên lịch / Mở đợt */}
      <ConfirmDialog
        isOpen={showOpenConfirm}
        title="Xác nhận Lên lịch / Mở đợt đánh giá"
        message="Nếu đã tới thời gian mở, hệ thống sẽ tạo hồ sơ cho sinh viên trong lớp. Admin vẫn có thể cập nhật cấu hình sau khi mở; thay đổi tiêu chí sẽ yêu cầu BCS kiểm tra lại điểm dự kiến."
        confirmLabel="Tiến hành Lên lịch/Mở"
        isLoading={submitting}
        onConfirm={handleOpenCampaign}
        onCancel={() => setShowOpenConfirm(false)}
      />
    </div>
  );
};
