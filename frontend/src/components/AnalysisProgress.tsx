import React, { useEffect, useState } from 'react';
import type { AnalysisResult } from '../services/api';
import { api } from '../services/api';

interface AnalysisProgressProps {
  jobId: string;
  onComplete: (result: AnalysisResult) => void;
}

const STEPS = [
  'QUEUED',
  'PARSING',
  'INDEXING',
  'MATCHING',
  'ANALYZING',
  'VALIDATING',
  'COMPLETE',
];

export const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ jobId, onComplete }) => {
  const [currentState, setCurrentState] = useState<string>('QUEUED');
  const [progressDetail, setProgressDetail] = useState<string>('Initializing analysis...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: number;

    const pollStatus = async () => {
      try {
        const response = await api.getAnalysisStatus(jobId);
        setCurrentState(response.state);
        if (response.progress_detail) {
          setProgressDetail(response.progress_detail);
        }

        if (response.state === 'COMPLETE' && response.result) {
          onComplete(response.result);
        } else if (response.state === 'FAILED') {
          setError(response.result?.error_message || 'Analysis failed. Please try again.');
        } else {
          timer = window.setTimeout(pollStatus, 2000);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error polling status');
      }
    };

    pollStatus();

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [jobId, onComplete]);

  const currentIdx = STEPS.indexOf(currentState);
  const progressPercent = currentIdx >= 0 ? Math.round(((currentIdx + 1) / STEPS.length) * 100) : 0;

  return (
    <div className="card-glass" role="status" aria-live="polite">
      <h2 style={{ marginBottom: 'var(--space-md)' }}>Analysis in Progress</h2>
      <p style={{ marginBottom: 'var(--space-lg)', color: 'var(--text-secondary)' }}>
        Job ID: <code style={{ color: 'var(--accent-primary)' }}>{jobId.slice(0, 12)}...</code>
      </p>

      {error ? (
        <div style={{ color: 'var(--color-error)', padding: 'var(--space-md)', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)' }}>
          {error}
        </div>
      ) : (
        <>
          <div className="progress-bar" style={{ marginBottom: 'var(--space-lg)' }}>
            <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            {STEPS.map((step, idx) => {
              const isDone = currentIdx > idx;
              const isCurrent = currentIdx === idx;
              return (
                <div
                  key={step}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-md)',
                    color: isCurrent ? 'var(--accent-primary)' : isDone ? 'var(--color-success)' : 'var(--text-muted)',
                    fontWeight: isCurrent ? 600 : 400,
                  }}
                >
                  <span>{isDone ? '✓' : isCurrent ? '●' : '○'}</span>
                  <span>{step}</span>
                  {isCurrent && <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />}
                </div>
              );
            })}
          </div>

          <p style={{ marginTop: 'var(--space-lg)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {progressDetail}
          </p>
        </>
      )}
    </div>
  );
};
