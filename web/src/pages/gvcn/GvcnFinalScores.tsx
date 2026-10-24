import React, { useState, useEffect } from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { api } from '../../api/client';
import { Campaign, CaseStatus } from '../../api/types';
import { staffStore, GvcnScoreRecord } from '../../components/staff/mockStaffData';
import { Download, Clock, CheckCircle2, Search, FileSpreadsheet, Lock, AlertCircle, RotateCcw } from 'lucide-react';

const isDemoMode = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';

export const GvcnFinalScores: React.FC = () => {
  const [campaign, setCampaign] = useState<Campaign | null>(isDemoMode ? staffStore.getCampaign() : null);
  const [records, setRecords] = useState<GvcnScoreRecord[]>(isDemoMode ? staffStore.getGvcnFinalScores() : []);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [downloading, setDownloading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const camp = await api.get<Campaign>('/gvcn/campaigns/active');
      setCampaign(camp);
      if (camp.status === 'FINALIZED') {
        const csvBlob = await api.get<Blob>(`/gvcn/campaigns/${camp.id}/final-scores.csv`);
        const text = await (csvBlob instanceof Blob ? csvBlob.text() : String(csvBlob));
        const lines = text.trim().split('\n').filter((l) => l.trim().length > 0);
        const dataRows = lines.slice(1);
        const parsed: GvcnScoreRecord[] = dataRows.map((line, idx) => {
          const parts = line.split(',').map((p) => p.replace(/^"|"$/g, '').trim());
          return {
            stt: idx + 1,
            student_code: parts[0] || '',
            student_name: parts[1] || '',
            status: (parts[2] || 'FINALIZED') as CaseStatus,
            claimed_total: parts[3] || '0.00',
            proposed_total: parts[4] || '0.00',
            final_total: parts[5] || '0.00',
            note: parts[6] || '',
          };
        });
        setRecords(parsed);
      } else {
        setRecords([]);
      }
    } catch (err: unknown) {
      if (isDemoMode) {
        setCampaign(staffStore.getCampaign());
        setRecords(staffStore.getGvcnFinalScores());
      } else {
        const errObj = err as { error?: { message?: string }; message?: string };
        const msg = errObj?.error?.message || errObj?.message || 'Không thể tải bảng điểm từ máy chủ.';
        setErrorMsg(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const isFinalized = campaign?.status === 'FINALIZED';

  // Export CSV handler
  const handleExportCsv = async () => {
    if (!campaign || !isFinalized) return;
    try {
      setDownloading(true);
      setErrorMsg(null);
      let csvBlob: Blob;
      if (isDemoMode) {
        const csvContent = staffStore.exportGvcnCsvContent();
        csvBlob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      } else {
        const responseBlob = await api.get<Blob>(`/gvcn/campaigns/${campaign.id}/final-scores.csv`);
        csvBlob = responseBlob instanceof Blob ? responseBlob : new Blob([responseBlob], { type: 'text/csv;charset=utf-8;' });
      }

      const url = URL.createObjectURL(csvBlob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Bang_Diem_DRL_Chinh_Thuc_${campaign.term}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const errObj = err as { error?: { message?: string }; message?: string };
      setErrorMsg(errObj?.error?.message || errObj?.message || 'Lỗi khi tải bảng điểm CSV.');
    } finally {
      setDownloading(false);
    }
  };

  if (loading && !campaign) {
    return (
      <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
        <p style={{ color: '#64748b' }}>Đang nạp thông tin đợt đánh giá...</p>
      </div>
    );
  }

  if (errorMsg && !campaign) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
        <AlertCircle size={40} color="#dc2626" style={{ margin: '0 auto 1rem' }} />
        <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#0f172a', marginBottom: '0.5rem' }}>
          Lỗi tải bảng điểm
        </h3>
        <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
          {errorMsg}
        </p>
        <button className="btn btn-primary" onClick={loadData} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          <RotateCcw size={16} /> Thử lại
        </button>
      </div>
    );
  }

  if (!campaign) return null;

  // Filtered records
  const filteredRecords = records.filter((r) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return r.student_code.toLowerCase().includes(q) || r.student_name.toLowerCase().includes(q);
  });

  // Score statistics
  const totalStudents = records.length;
  const avgScore = totalStudents > 0
    ? (
        records.reduce((sum, r) => sum + (parseFloat(r.final_total || '0') || 0), 0) /
        totalStudents
      ).toFixed(2)
    : '0.00';

  const maxScore = totalStudents > 0
    ? Math.max(...records.map((r) => parseFloat(r.final_total || '0') || 0)).toFixed(2)
    : '0.00';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* 1. Header Bar */}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>
              Bảng điểm Rèn luyện Chính thức (GVCN)
            </h2>
            <StatusBadge status={campaign.status} />
          </div>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
            Học kỳ: <strong>{campaign.term}</strong> | Đợt: <strong>{campaign.title}</strong> | Phân quyền: <strong>Chỉ đọc bảng điểm sau khi chốt</strong>
          </p>
        </div>

        <div>
          <button
            type="button"
            disabled={!isFinalized || downloading}
            onClick={handleExportCsv}
            className="btn btn-primary"
            style={{ fontSize: '0.875rem' }}
            title={isFinalized ? 'Tải bảng điểm CSV chính thức' : 'Bảng điểm chưa được chốt'}
          >
            <Download size={16} /> {downloading ? 'Đang tạo tệp CSV...' : '📥 Xuất bảng điểm CSV'}
          </button>
        </div>
      </div>

      {/* 2. Status Gating: If NOT FINALIZED, show clear pending explanation */}
      {!isFinalized ? (
        <div
          className="card"
          style={{
            padding: '3rem 1.5rem',
            textAlign: 'center',
            backgroundColor: '#ffffff',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: '#eff6ff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#1e40af',
            }}
          >
            <Clock size={32} />
          </div>

          <div style={{ maxWidth: '520px' }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0f172a' }}>
              Đợt đánh giá chưa hoàn thành chốt điểm
            </h3>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginTop: '0.5rem', lineHeight: 1.6 }}>
              Hiện tại đợt đang ở trạng thái <strong style={{ color: '#1e40af' }}>{campaign.status}</strong>. Theo quy chế quản lý điểm rèn luyện, Giáo viên chủ nhiệm chỉ có quyền truy cập bảng điểm chính thức và xuất tệp CSV sau khi Ban cán sự lớp đã hoàn tất bình xét, giải quyết xong khiếu nại và thực hiện chốt điểm toàn lớp.
            </p>
          </div>

          <div
            style={{
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              padding: '0.75rem 1.25rem',
              fontSize: '0.825rem',
              color: '#475569',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <Lock size={15} color="#64748b" />
            <span>Nút xuất bảng điểm CSV sẽ tự động được kích hoạt ngay khi trạng thái chuyển sang <strong>FINALIZED</strong>.</span>
          </div>
        </div>
      ) : (
        /* 3. If FINALIZED: Full read-only official score table & statistics */
        <>
          {/* Statistical Summary Cards */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
            }}
          >
            <div className="card">
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Tổng số sinh viên</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#0f172a', marginTop: '0.25rem' }}>
                {totalStudents}
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Điểm trung bình lớp</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#1e40af', marginTop: '0.25rem' }}>
                {avgScore}
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Điểm cao nhất</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#059669', marginTop: '0.25rem' }}>
                {maxScore}
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Tình trạng hồ sơ</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#059669', marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <CheckCircle2 size={18} /> 100% Đã chốt
              </div>
            </div>
          </div>

          {/* Table Card */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div
              style={{
                padding: '1rem 1.25rem',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.75rem',
                backgroundColor: '#ffffff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileSpreadsheet size={18} color="#059669" />
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>
                  Bảng tổng hợp Điểm Rèn luyện Chính thức
                </h3>
              </div>

              <div style={{ position: 'relative', minWidth: '240px' }}>
                <Search size={14} color="#94a3b8" style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Tìm theo Mã SV hoặc Họ tên..."
                  style={{
                    width: '100%',
                    padding: '0.35rem 0.6rem 0.35rem 1.8rem',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '0.8rem',
                  }}
                />
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left', color: '#475569' }}>
                    <th style={{ padding: '0.75rem 1rem' }}>STT</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Mã SV</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Họ và tên</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Điểm tự khai</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Điểm dự kiến</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Điểm chính thức</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>Tình trạng</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Ghi chú</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecords.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                        Không tìm thấy sinh viên phù hợp với từ khóa.
                      </td>
                    </tr>
                  ) : (
                    filteredRecords.map((rec) => (
                      <tr key={rec.stt} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>{rec.stt}</td>
                        <td style={{ padding: '0.75rem 1rem', fontWeight: 600, color: '#0f172a' }}>{rec.student_code}</td>
                        <td style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>{rec.student_name}</td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>{rec.claimed_total}</td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right', color: '#475569' }}>{rec.proposed_total}</td>
                        <td
                          style={{
                            padding: '0.75rem 1rem',
                            textAlign: 'right',
                            fontWeight: 700,
                            color: '#1e40af',
                            fontSize: '0.95rem',
                          }}
                        >
                          {rec.final_total}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                          <StatusBadge status="FINALIZED" />
                        </td>
                        <td style={{ padding: '0.75rem 1rem', fontSize: '0.8rem', color: '#64748b' }}>
                          {rec.note}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div
              style={{
                padding: '0.75rem 1.25rem',
                borderTop: '1px solid #e2e8f0',
                backgroundColor: '#f8fafc',
                fontSize: '0.8rem',
                color: '#64748b',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span>Dữ liệu bảng điểm đã được ký số và chốt bởi Ban cán sự lớp. GVCN chỉ có quyền xem và xuất CSV.</span>
              <span>Tổng số: {records.length} sinh viên</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
