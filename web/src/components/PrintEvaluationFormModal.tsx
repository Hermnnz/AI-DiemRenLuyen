import React, { useRef } from 'react';
import { Criterion, Claim } from '../api/types';
import { Printer, X } from 'lucide-react';

interface PrintEvaluationFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  campaignTitle: string;
  term: string;
  studentName: string;
  studentCode: string;
  className?: string;
  facultyName?: string;
  criteria: Criterion[];
  claims: Claim[];
  proposedTotal?: string | null;
  claimedTotal?: string | null;
}

export const PrintEvaluationFormModal: React.FC<PrintEvaluationFormModalProps> = ({
  isOpen,
  onClose,
  campaignTitle,
  term,
  studentName,
  studentCode,
  className = '',
  facultyName = '',
  criteria,
  claims,
  proposedTotal,
  claimedTotal,
}) => {
  const printRef = useRef<HTMLDivElement>(null);

  if (!isOpen) return null;

  // Map criterion id -> claim
  const claimMap: Record<string, Claim> = {};
  claims.forEach((cl) => {
    claimMap[cl.criterion_id] = cl;
  });

  // Sections in the approved school-wide rubric.
  const SECTION_ORDER = ['DIEU_4', 'DIEU_5', 'DIEU_6', 'DIEU_7', 'DIEU_8'];
  const SECTION_NAMES: Record<string, { title: string; max: string }> = {
    DIEU_4: { title: 'ĐIỀU 4. Ý thức tham gia học tập', max: '20.00' },
    DIEU_5: { title: 'ĐIỀU 5. Ý thức chấp hành nội quy, quy chế, quy định trong nhà trường', max: '25.00' },
    DIEU_6: {
      title: 'ĐIỀU 6. Ý thức tham gia các hoạt động chính trị, xã hội, văn hóa, văn nghệ, thể thao...',
      max: '20.00',
    },
    DIEU_7: { title: 'ĐIỀU 7. Ý thức công dân trong quan hệ cộng đồng', max: '25.00' },
    DIEU_8: {
      title: 'ĐIỀU 8. Ý thức và kết quả tham gia công tác cán bộ lớp, đoàn thể, thành tích đặc biệt',
      max: '10.00',
    },
  };

  // Group criteria by section
  const grouped: Record<string, Criterion[]> = {};
  criteria.forEach((crit) => {
    const sec = crit.section_code || 'OTHER';
    if (!grouped[sec]) grouped[sec] = [];
    grouped[sec].push(crit);
  });

  // Calculate sum of self-score and approved-score per section (respecting section caps)
  const calculateSectionScores = (secCode: string, secMax: number) => {
    const secCriteria = grouped[secCode] || [];
    let selfSum = 0;
    let apprSum = 0;
    secCriteria.forEach((crit) => {
      const cl = claimMap[crit.id];
      if (cl?.self_score) selfSum += parseFloat(cl.self_score) || 0;
      if (cl?.approved_score) apprSum += parseFloat(cl.approved_score) || 0;
    });
    return {
      selfRaw: selfSum,
      selfCapped: Math.min(selfSum, secMax),
      apprRaw: apprSum,
      apprCapped: Math.min(apprSum, secMax),
    };
  };

  // Compute grand total
  let totalSelf = 0;
  let totalAppr = 0;
  SECTION_ORDER.forEach((secCode) => {
    const max = parseFloat(SECTION_NAMES[secCode]?.max || '0');
    const { selfCapped, apprCapped } = calculateSectionScores(secCode, max);
    totalSelf += selfCapped;
    totalAppr += apprCapped;
  });

  // If proposedTotal or claimedTotal provided from backend, use them as authoritative
  const finalSelfScore = claimedTotal !== undefined && claimedTotal !== null ? claimedTotal : totalSelf.toFixed(2);
  const finalApprScore = proposedTotal !== undefined && proposedTotal !== null ? proposedTotal : totalAppr.toFixed(2);

  // Rating based on Parameters sheet
  const getRating = (scoreStr: string) => {
    const num = parseFloat(scoreStr);
    if (isNaN(num)) return 'Chưa xếp loại';
    if (num >= 90) return 'Xuất sắc';
    if (num >= 80) return 'Tốt';
    if (num >= 65) return 'Khá';
    if (num >= 50) return 'Trung bình';
    if (num >= 35) return 'Yếu';
    return 'Kém';
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '1rem',
      }}
    >
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          #print-evaluation-sheet, #print-evaluation-sheet * {
            visibility: visible;
          }
          #print-evaluation-sheet {
            position: absolute;
            left: 0;
            top: 0;
            width: 100% !important;
            margin: 0 !important;
            padding: 10mm 15mm !important;
            box-shadow: none !important;
            background: #ffffff !important;
            font-size: 11pt !important;
            line-height: 1.3 !important;
          }
          .no-print {
            display: none !important;
          }
          .page-break-after {
            page-break-after: always;
          }
        }
      `}</style>

      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '8px',
          width: '950px',
          maxWidth: '96vw',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
          overflow: 'hidden',
        }}
      >
        {/* Modal Toolbar (hidden when printing) */}
        <div
          className="no-print"
          style={{
            padding: '0.75rem 1.25rem',
            backgroundColor: '#0f172a',
            color: '#ffffff',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Printer size={18} color="#38bdf8" />
            <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
              Bản in Phiếu Tự Đánh Giá Kết Quả Rèn Luyện (Khổ A4)
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              type="button"
              onClick={handlePrint}
              style={{
                backgroundColor: '#2563eb',
                color: '#ffffff',
                border: 'none',
                padding: '0.4rem 0.9rem',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
              }}
            >
              <Printer size={16} /> In phiếu (Print A4)
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '0.3rem',
              }}
              title="Đóng modal"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Scrollable Printable Document Area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.5rem',
            backgroundColor: '#f1f5f9',
          }}
        >
          <div
            id="print-evaluation-sheet"
            ref={printRef}
            style={{
              backgroundColor: '#ffffff',
              margin: '0 auto',
              padding: '2.5rem 3rem',
              width: '100%',
              maxWidth: '850px',
              fontFamily: '"Times New Roman", Times, serif',
              color: '#000000',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            }}
          >
            {/* Header: Quốc hiệu & Tên trường */}
            <table style={{ width: '100%', borderCollapse: 'collapse', border: 'none', marginBottom: '1rem' }}>
              <tbody>
                <tr>
                  <td style={{ textAlign: 'center', verticalAlign: 'top', width: '45%' }}>
                    <div style={{ fontSize: '11pt', fontWeight: 600, textTransform: 'uppercase' }}>
                      TRƯỜNG ĐẠI HỌC KINH TẾ
                    </div>
                    <div style={{ fontSize: '11pt', fontWeight: 700, textTransform: 'uppercase' }}>
                      KHOA {facultyName.toUpperCase()}
                    </div>
                    <div style={{ width: '120px', height: '1px', backgroundColor: '#000', margin: '4px auto 0' }} />
                  </td>
                  <td style={{ textAlign: 'center', verticalAlign: 'top', width: '55%' }}>
                    <div style={{ fontSize: '11pt', fontWeight: 700, textTransform: 'uppercase' }}>
                      CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
                    </div>
                    <div style={{ fontSize: '11pt', fontWeight: 700 }}>
                      Độc lập - Tự do - Hạnh phúc
                    </div>
                    <div style={{ width: '150px', height: '1px', backgroundColor: '#000', margin: '4px auto 0' }} />
                  </td>
                </tr>
              </tbody>
            </table>

            {/* Document Title */}
            <div style={{ textAlign: 'center', marginTop: '1.25rem', marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '14pt', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                PHIẾU TỰ ĐÁNH GIÁ KẾT QUẢ RÈN LUYỆN CỦA SINH VIÊN
              </div>
              <div style={{ fontSize: '11.5pt', fontStyle: 'italic', marginTop: '0.25rem' }}>
                {campaignTitle} (Học kỳ: {term})
              </div>
            </div>

            {/* Student Personal Information */}
            <div style={{ marginBottom: '1rem', fontSize: '11pt', lineHeight: 1.6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>
                  Họ và tên sinh viên: <strong>{studentName}</strong>
                </span>
                <span>
                  Mã sinh viên: <strong>{studentCode}</strong>
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>
                  Lớp: <strong>{className}</strong>
                </span>
                <span>
                  Khoa: <strong>{facultyName}</strong>
                </span>
              </div>
            </div>

            {/* Evaluation Criteria Table */}
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '10pt',
                border: '1.5px solid #000000',
              }}
            >
              <thead>
                <tr style={{ backgroundColor: '#f8fafc', textAlign: 'center', fontWeight: 700 }}>
                  <th style={{ border: '1px solid #000', padding: '6px 4px', width: '45px' }}>TT</th>
                  <th style={{ border: '1px solid #000', padding: '6px 8px', textAlign: 'left' }}>
                    Nội dung đánh giá
                  </th>
                  <th style={{ border: '1px solid #000', padding: '6px 4px', width: '60px' }}>Điểm tối đa</th>
                  <th style={{ border: '1px solid #000', padding: '6px 4px', width: '65px' }}>Điểm SV tự chấm</th>
                  <th style={{ border: '1px solid #000', padding: '6px 4px', width: '65px' }}>Điểm Lớp đánh giá</th>
                </tr>
              </thead>
              <tbody>
                {SECTION_ORDER.map((secCode, secIdx) => {
                  const secInfo = SECTION_NAMES[secCode];
                  const secCriteria = grouped[secCode] || [];
                  const { selfCapped, apprCapped } = calculateSectionScores(
                    secCode,
                    parseFloat(secInfo.max)
                  );

                  return (
                    <React.Fragment key={secCode}>
                      {/* Section Header Row */}
                      <tr style={{ backgroundColor: '#f1f5f9', fontWeight: 700 }}>
                        <td style={{ border: '1px solid #000', textAlign: 'center', padding: '5px 4px' }}>
                          {['I', 'II', 'III', 'IV', 'V'][secIdx]}
                        </td>
                        <td style={{ border: '1px solid #000', padding: '5px 8px' }}>
                          {secInfo.title}
                        </td>
                        <td style={{ border: '1px solid #000', textAlign: 'center', padding: '5px 4px' }}>
                          {secInfo.max}
                        </td>
                        <td style={{ border: '1px solid #000', textAlign: 'center', padding: '5px 4px', color: '#1e40af' }}>
                          {selfCapped.toFixed(2)}
                        </td>
                        <td style={{ border: '1px solid #000', textAlign: 'center', padding: '5px 4px', color: '#047857' }}>
                          {apprCapped > 0 ? apprCapped.toFixed(2) : '-'}
                        </td>
                      </tr>

                      {/* Criteria Detail Rows */}
                      {secCriteria.map((crit, critIdx) => {
                        const cl = claimMap[crit.id];
                        const selfScore = cl?.self_score ? parseFloat(cl.self_score).toFixed(2) : '-';
                        const apprScore = cl?.approved_score ? parseFloat(cl.approved_score).toFixed(2) : '-';

                        return (
                          <tr key={crit.id}>
                            <td style={{ border: '1px solid #000', textAlign: 'center', padding: '4px' }}>
                              {critIdx + 1}
                            </td>
                            <td style={{ border: '1px solid #000', padding: '4px 8px' }}>
                              <div style={{ fontWeight: 600 }}>
                                [{crit.code}] {crit.title}
                              </div>
                              {crit.description && (
                                <div style={{ fontSize: '9pt', color: '#475569', marginTop: '2px' }}>
                                  {crit.description}
                                </div>
                              )}
                              {cl?.student_note && (
                                <div style={{ fontSize: '8.5pt', fontStyle: 'italic', color: '#334155', marginTop: '2px' }}>
                                  Ghi chú: {cl.student_note}
                                </div>
                              )}
                              {cl?.bcs_reason && (
                                <div style={{ fontSize: '8.5pt', color: '#b91c1c', marginTop: '2px' }}>
                                  Ý kiến BCS: {cl.bcs_reason}
                                </div>
                              )}
                            </td>
                            <td style={{ border: '1px solid #000', textAlign: 'center', padding: '4px' }}>
                              {parseFloat(crit.max_score).toFixed(2)}
                            </td>
                            <td style={{ border: '1px solid #000', textAlign: 'center', padding: '4px' }}>
                              {selfScore}
                            </td>
                            <td style={{ border: '1px solid #000', textAlign: 'center', padding: '4px', fontWeight: apprScore !== '-' ? 600 : 400 }}>
                              {apprScore}
                            </td>
                          </tr>
                        );
                      })}
                    </React.Fragment>
                  );
                })}

                {/* Grand Total Row */}
                <tr style={{ backgroundColor: '#e2e8f0', fontWeight: 700, fontSize: '10.5pt' }}>
                  <td colSpan={2} style={{ border: '1px solid #000', textAlign: 'center', padding: '8px' }}>
                    TỔNG CỘNG ĐIỂM RÈN LUYỆN
                  </td>
                  <td style={{ border: '1px solid #000', textAlign: 'center', padding: '8px' }}>
                    100.00
                  </td>
                  <td style={{ border: '1px solid #000', textAlign: 'center', padding: '8px', color: '#1e40af' }}>
                    {finalSelfScore}
                  </td>
                  <td style={{ border: '1px solid #000', textAlign: 'center', padding: '8px', color: '#047857' }}>
                    {finalApprScore !== '0.00' ? finalApprScore : finalSelfScore}
                  </td>
                </tr>

                {/* Rating Row */}
                <tr style={{ fontWeight: 700 }}>
                  <td colSpan={2} style={{ border: '1px solid #000', textAlign: 'center', padding: '6px' }}>
                    Xếp loại rèn luyện (Tham khảo sheet Parameters)
                  </td>
                  <td colSpan={3} style={{ border: '1px solid #000', textAlign: 'center', padding: '6px', color: '#b45309' }}>
                    {getRating(finalApprScore !== '0.00' ? finalApprScore : finalSelfScore)}
                  </td>
                </tr>
              </tbody>
            </table>

            {/* Disclaimer & Note */}
            <div style={{ marginTop: '0.5rem', fontSize: '8.5pt', fontStyle: 'italic', color: '#475569' }}>
              * Xếp loại theo bộ quy tắc toàn trường: Xuất sắc &ge;90; Tốt &ge;80; Khá &ge;65; Trung bình &ge;50; Yếu &ge;35; Kém &lt;35.
            </div>

            {/* Signature Block */}
            <div style={{ marginTop: '2rem', pageBreakInside: 'avoid' }}>
              <div style={{ textAlign: 'right', fontStyle: 'italic', fontSize: '10pt', marginBottom: '0.75rem' }}>
                Đà Nẵng, ngày ...... tháng ...... năm 20......
              </div>

              <table style={{ width: '100%', borderCollapse: 'collapse', border: 'none', textAlign: 'center', fontSize: '10.5pt' }}>
                <tbody>
                  <tr style={{ fontWeight: 700 }}>
                    <td style={{ width: '33%', paddingBottom: '4rem' }}>
                      SINH VIÊN TỰ ĐÁNH GIÁ
                      <div style={{ fontWeight: 400, fontStyle: 'italic', fontSize: '9pt' }}>(Ký và ghi rõ họ tên)</div>
                    </td>
                    <td style={{ width: '34%', paddingBottom: '4rem' }}>
                      TM. BAN CÁN SỰ LỚP
                      <div style={{ fontWeight: 400, fontStyle: 'italic', fontSize: '9pt' }}>(Lớp trưởng ký và ghi rõ họ tên)</div>
                    </td>
                    <td style={{ width: '33%', paddingBottom: '4rem' }}>
                      GIÁO VIÊN CHỦ NHIỆM
                      <div style={{ fontWeight: 400, fontStyle: 'italic', fontSize: '9pt' }}>(Ký và ghi rõ họ tên)</div>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <strong>{studentName}</strong>
                    </td>
                    <td>
                      <strong>................................................</strong>
                    </td>
                    <td>
                      <strong>................................................</strong>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
