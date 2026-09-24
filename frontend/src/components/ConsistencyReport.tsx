import React, { useState } from 'react';
import type { Document, Finding } from '../services/api';
import { Disclaimer } from './Disclaimer';
import { EvidenceViewer } from './EvidenceViewer';

interface ConsistencyReportProps {
  findings: Finding[];
  documents: Document[];
}

const TYPE_ICONS: Record<string, string> = {
  CONSISTENT: '✓',
  CONFLICT: '✕',
  OVERRIDE: '↑',
  AMBIGUOUS: '?',
  UNADDRESSED: '○',
};

const CONFIDENCE_ORDER: Record<string, number> = {
  NOT_ESTABLISHED: 0,
  INTERPRETED: 1,
  STATED: 2,
};

export const ConsistencyReport: React.FC<ConsistencyReportProps> = ({ findings, documents }) => {
  const [activeTab, setActiveTab] = useState<string>('ALL');
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  const docNameMap = new Map<string, string>();
  documents.forEach((d) => docNameMap.set(d.document_id, d.filename));

  const filteredFindings = findings.filter((f) => {
    if (activeTab === 'ALL') return true;
    return f.relationship_type === activeTab;
  });

  const sortedFindings = [...filteredFindings].sort((a, b) => {
    return (CONFIDENCE_ORDER[a.confidence] ?? 9) - (CONFIDENCE_ORDER[b.confidence] ?? 9);
  });

  const counts = {
    ALL: findings.length,
    CONFLICT: findings.filter((f) => f.relationship_type === 'CONFLICT').length,
    OVERRIDE: findings.filter((f) => f.relationship_type === 'OVERRIDE').length,
    AMBIGUOUS: findings.filter((f) => f.relationship_type === 'AMBIGUOUS').length,
    CONSISTENT: findings.filter((f) => f.relationship_type === 'CONSISTENT').length,
    UNADDRESSED: findings.filter((f) => f.relationship_type === 'UNADDRESSED').length,
  };

  return (
    <section aria-label="Consistency Report">
      <Disclaimer />

      <div style={{ marginTop: 'var(--space-lg)', marginBottom: 'var(--space-md)' }} className="tabs">
        {(['ALL', 'CONFLICT', 'OVERRIDE', 'AMBIGUOUS', 'CONSISTENT', 'UNADDRESSED'] as const).map((type) => (
          <button
            key={type}
            className={`tab ${activeTab === type ? 'active' : ''}`}
            onClick={() => setActiveTab(type)}
            type="button"
          >
            {type} ({counts[type]})
          </button>
        ))}
      </div>

      {sortedFindings.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-2xl)' }}>
          <p>No findings found for this category.</p>
        </div>
      ) : (
        sortedFindings.map((finding) => (
          <article
            key={finding.finding_id}
            className="finding-card"
            onClick={() => setSelectedFinding(finding)}
            style={{ cursor: 'pointer' }}
          >
            <div className="finding-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <span className={`rel-type rel-type-${finding.relationship_type.toLowerCase()}`}>
                  {TYPE_ICONS[finding.relationship_type] || '•'} {finding.relationship_type}
                </span>
                <span className={`confidence-badge confidence-${finding.confidence.toLowerCase().replace('_', '-')}`}>
                  {finding.confidence}
                </span>
              </div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {finding.evidence.length} evidence quote(s)
              </span>
            </div>

            <p className="finding-explanation">{finding.explanation}</p>

            {finding.uncertainty && (
              <div
                style={{
                  fontSize: '0.85rem',
                  color: 'var(--color-warning)',
                  background: 'rgba(245, 158, 11, 0.1)',
                  padding: 'var(--space-xs) var(--space-sm)',
                  borderRadius: 'var(--radius-sm)',
                  marginTop: 'var(--space-xs)',
                }}
              >
                ⚠️ {finding.uncertainty}
              </div>
            )}

            <div style={{ marginTop: 'var(--space-md)' }}>
              {finding.evidence.map((span, idx) => (
                <div key={idx} className="finding-evidence">
                  <div className="evidence-source">
                    {docNameMap.get(span.document_id) || span.document_id.slice(0, 8)} • Page {span.page}
                  </div>
                  <div className="evidence-text">"{span.text_span}"</div>
                </div>
              ))}
            </div>
          </article>
        ))
      )}

      {selectedFinding && (
        <EvidenceViewer
          finding={selectedFinding}
          documents={documents}
          onClose={() => setSelectedFinding(null)}
        />
      )}
    </section>
  );
};
