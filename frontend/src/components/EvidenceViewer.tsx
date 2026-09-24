import React from 'react';
import type { Document, Finding } from '../services/api';

interface EvidenceViewerProps {
  finding: Finding;
  documents: Document[];
  onClose?: () => void;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ finding, documents, onClose }) => {
  const docNameMap = new Map<string, string>();
  documents.forEach((d) => docNameMap.set(d.document_id, d.filename));

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="evidence-dialog-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'rgba(10, 14, 26, 0.85)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-md)',
      }}
      onClick={onClose}
    >
      <div
        className="card-glass"
        style={{ maxWidth: 700, width: '100%', maxHeight: '90vh', overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
          <h2 id="evidence-dialog-title">Evidence Citation Detail</h2>
          {onClose && (
            <button className="btn btn-ghost btn-sm" onClick={onClose} type="button" aria-label="Close dialog">
              ✕
            </button>
          )}
        </div>

        <div style={{ marginBottom: 'var(--space-md)' }}>
          <span className={`rel-type rel-type-${finding.relationship_type.toLowerCase()}`}>
            {finding.relationship_type}
          </span>
          {' '}
          <span className={`confidence-badge confidence-${finding.confidence.toLowerCase().replace('_', '-')}`}>
            {finding.confidence}
          </span>
          {finding.validated ? (
            <span className="status-badge" style={{ color: 'var(--color-success)', marginLeft: 'var(--space-sm)' }}>
              ✓ Deterministically Validated
            </span>
          ) : (
            <span className="status-badge" style={{ color: 'var(--color-warning)', marginLeft: 'var(--space-sm)' }}>
              ⚠️ Validation Unconfirmed
            </span>
          )}
        </div>

        <p style={{ color: 'var(--text-primary)', marginBottom: 'var(--space-lg)' }}>
          {finding.explanation}
        </p>

        {finding.uncertainty && (
          <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: 'var(--space-sm)', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-md)', fontSize: '0.85rem' }}>
            <strong>Uncertainty Note:</strong> {finding.uncertainty}
          </div>
        )}

        <h3>Supporting Citations ({finding.evidence.length})</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', marginTop: 'var(--space-sm)' }}>
          {finding.evidence.map((span, idx) => (
            <div key={idx} className="finding-evidence">
              <div className="evidence-source">
                <strong>Source:</strong> {docNameMap.get(span.document_id) || span.document_id.slice(0, 8)} | Page {span.page} | Clause ID: {span.clause_id}
              </div>
              <div className="evidence-text">"{span.text_span}"</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
