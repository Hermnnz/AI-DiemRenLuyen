import React, { useState } from 'react';
import { studentService, OperationMode } from './studentService';
import { SCENARIO_DICTIONARY } from './studentMockData';
import { RefreshCw, ToggleLeft, ToggleRight, Info } from 'lucide-react';

interface StudentScenarioBarProps {
  onScenarioChange: () => void;
}

export const StudentScenarioBar: React.FC<StudentScenarioBarProps> = ({ onScenarioChange }) => {
  const isDemo = typeof import.meta !== 'undefined' && import.meta.env?.VITE_DEMO_MODE === 'true';
  if (!isDemo) return null;

  const [mode, setMode] = useState<OperationMode>(studentService.getMode());
  const [scenario, setScenario] = useState<string>(studentService.getCurrentScenarioKey());
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

  const handleModeToggle = () => {
    const nextMode: OperationMode = mode === 'mock' ? 'live' : 'mock';
    studentService.setMode(nextMode);
    setMode(nextMode);
    onScenarioChange();
  };

  const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const nextScenario = e.target.value;
    studentService.setScenario(nextScenario);
    setScenario(nextScenario);
    onScenarioChange();
  };

  const handleReset = () => {
    studentService.resetScenario();
    onScenarioChange();
  };

  return (
    <div className="scenario-bar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{
            border: 'none',
            background: 'none',
            color: '#1e40af',
            fontWeight: 600,
            cursor: 'pointer',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
          }}
          title="Thu gọn / Mở rộng bảng điều khiển kịch bản demo"
        >
          <Info size={15} />
          <span>Kịch bản Demo SV (Gói B)</span>
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>[{isCollapsed ? 'Mở' : 'Ẩn'}]</span>
        </button>

        {!isCollapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label htmlFor="student-scenario-select" style={{ color: '#475569', fontSize: '0.8125rem' }}>
              Trạng thái thử nghiệm:
            </label>
            <select
              id="student-scenario-select"
              value={scenario}
              onChange={handleScenarioChange}
              disabled={mode === 'live'}
            >
              {Object.entries(SCENARIO_DICTIONARY).map(([key, item]) => (
                <option key={key} value={key}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {!isCollapsed && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            type="button"
            onClick={handleModeToggle}
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
            title="Chuyển đổi giữa Mock dữ liệu hợp đồng và Backend thật"
          >
            {mode === 'mock' ? (
              <>
                <ToggleLeft size={16} color="#d97706" />
                <span>Chế độ: <strong>Mock Fixtures</strong></span>
              </>
            ) : (
              <>
                <ToggleRight size={16} color="#16a34a" />
                <span>Chế độ: <strong>Live API (/api/v1)</strong></span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleReset}
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
            title="Khôi phục trạng thái ban đầu của kịch bản"
          >
            <RefreshCw size={14} />
            <span>Reset</span>
          </button>
        </div>
      )}
    </div>
  );
};
