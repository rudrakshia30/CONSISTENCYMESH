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

  const handleExportCSV = () => {
    const headers = ['Finding ID', 'Relationship Type', 'Confidence', 'Risk Level', 'Explanation', 'Evidence Count'];
    const rows = findings.map((f) => [
      f.finding_id,
      f.relationship_type,
      f.confidence,
      (f as any).risk_level || 'MEDIUM',
      `"${f.explanation.replace(/"/g, '""')}"`,
      f.evidence.length,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `ConsistencyMesh_Report_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

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

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'var(--space-lg)', marginBottom: 'var(--space-md)' }}>
        <div className="tabs">
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

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handleExportCSV}
          style={{ gap: '6px' }}
        >
          📥 Export CSV Audit Report
        </button>
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
            style={{ cursor: 'pointer', marginBottom: 'var(--space-md)' }}
          >
            <div className="finding-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <span className={`rel-type rel-type-${finding.relationship_type.toLowerCase()}`}>
                  {TYPE_ICONS[finding.relationship_type] || '•'} {finding.relationship_type}
                </span>
                <span className={`confidence-badge confidence-${finding.confidence.toLowerCase().replace('_', '-')}`}>
                  {finding.confidence}
                </span>
                {(finding as any).risk_level && (
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '12px',
                      background:
                        (finding as any).risk_level === 'CRITICAL'
                          ? 'rgba(239, 68, 68, 0.2)'
                          : (finding as any).risk_level === 'HIGH'
                          ? 'rgba(245, 158, 11, 0.2)'
                          : 'rgba(59, 130, 246, 0.2)',
                      color:
                        (finding as any).risk_level === 'CRITICAL'
                          ? '#ef4444'
                          : (finding as any).risk_level === 'HIGH'
                          ? '#f59e0b'
                          : '#3b82f6',
                    }}
                  >
                    ⚡ RISK: {(finding as any).risk_level}
                  </span>
                )}
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

            {/* Comparative Side-by-Side Evidence Layout */}
            <div
              style={{
                marginTop: 'var(--space-md)',
                display: finding.evidence.length === 2 ? 'grid' : 'block',
                gridTemplateColumns: finding.evidence.length === 2 ? '1fr 1fr' : '1fr',
                gap: 'var(--space-md)',
              }}
            >
              {finding.evidence.map((span, idx) => (
                <div key={idx} className="finding-evidence" style={{ margin: 0 }}>
                  <div className="evidence-source" style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                    📄 {docNameMap.get(span.document_id) || span.document_id.slice(0, 8)} • Page {span.page}
                  </div>
                  <div className="evidence-text" style={{ fontStyle: 'italic', marginTop: '4px' }}>
                    "{span.text_span}"
                  </div>
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
