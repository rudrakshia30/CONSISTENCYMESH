import React, { useState } from 'react';
import type { QAResponse } from '../services/api';
import { api } from '../services/api';
import { Disclaimer } from './Disclaimer';

interface QAPanelProps {
  jobId: string;
}

interface QAHistoryItem {
  question: string;
  response: QAResponse;
}

export const QAPanel: React.FC<QAPanelProps> = ({ jobId }) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<QAHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!question.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      const res = await api.askQuestion(jobId, question.trim());
      setHistory((prev) => [...prev, { question: question.trim(), response: res }]);
      setQuestion('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get answer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
      <Disclaimer />

      <form onSubmit={handleSubmit} className="card-glass">
        <h2 style={{ marginBottom: 'var(--space-md)' }}>Follow-up Q&A</h2>
        <p style={{ marginBottom: 'var(--space-md)', color: 'var(--text-secondary)' }}>
          Ask a question across the document set. Every answer is grounded in extracted evidence.
        </p>

        <textarea
          className="input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Which notice period controls if the MSA and SOW conflict?"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          disabled={loading}
        />

        <div style={{ marginTop: 'var(--space-md)', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-primary" type="submit" disabled={!question.trim() || loading}>
            {loading ? <span className="spinner" /> : 'Ask Question'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: 'var(--space-md)', color: 'var(--color-error)', fontSize: '0.9rem' }}>
            {error}
          </div>
        )}
      </form>

      <div aria-live="polite" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        {history.map((item, idx) => (
          <div key={idx} className="card">
            <h3 style={{ fontSize: '1rem', color: 'var(--accent-primary)', marginBottom: 'var(--space-sm)' }}>
              Q: {item.question}
            </h3>
            <p style={{ color: 'var(--text-primary)', marginBottom: 'var(--space-md)', lineHeight: 1.6 }}>
              {item.response.answer}
            </p>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
              <span className={`confidence-badge confidence-${item.response.confidence.toLowerCase().replace('_', '-')}`}>
                {item.response.confidence}
              </span>
            </div>

            {item.response.evidence.length > 0 && (
              <div>
                <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 'var(--space-xs)' }}>
                  Grounded Evidence:
                </h4>
                {item.response.evidence.map((span, sIdx) => (
                  <div key={sIdx} className="finding-evidence" style={{ fontSize: '0.85rem' }}>
                    <div className="evidence-source">
                      Doc {span.document_id.slice(0, 8)} • Page {span.page}
                    </div>
                    <div className="evidence-text">"{span.text_span}"</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
