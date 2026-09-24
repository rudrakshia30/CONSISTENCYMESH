import React from 'react';
import type { ConsistencyGraph, Document, Finding } from '../services/api';

interface RelationshipGraphProps {
  graph: ConsistencyGraph;
  documents: Document[];
  findings: Finding[];
  onEdgeClick?: (findingId: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  CONSISTENT: '#22c55e',
  CONFLICT: '#ef4444',
  OVERRIDE: '#f59e0b',
  AMBIGUOUS: '#a855f7',
  UNADDRESSED: '#6b7280',
};

export const RelationshipGraph: React.FC<RelationshipGraphProps> = ({ graph, documents, onEdgeClick }) => {
  const docNameMap = new Map<string, string>();
  documents.forEach((d) => docNameMap.set(d.document_id, d.filename));

  const numDocs = documents.length;
  const radius = 140;
  const centerX = 250;
  const centerY = 200;

  const docPositions = documents.map((doc, idx) => {
    const angle = (idx / Math.max(numDocs, 1)) * 2 * Math.PI - Math.PI / 2;
    return {
      id: doc.document_id,
      name: doc.filename,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  const posMap = new Map<string, { x: number; y: number }>();
  docPositions.forEach((pos) => posMap.set(pos.id, pos));

  return (
    <div className="graph-container">
      <div style={{ padding: 'var(--space-md)', display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap', borderBottom: '1px solid var(--border-color)' }}>
        {Object.entries(TYPE_COLORS).map(([type, color]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', fontSize: '0.8rem' }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: color }} />
            <span>{type}</span>
          </div>
        ))}
      </div>

      {graph.edges.length === 0 ? (
        <div style={{ padding: 'var(--space-2xl)', textAlign: 'center', color: 'var(--text-muted)' }}>
          No relationships mapped in the graph yet.
        </div>
      ) : (
        <svg viewBox="0 0 500 400" style={{ width: '100%', height: '400px' }} aria-label="Consistency Relationship Graph">
          {graph.edges.map((edge, idx) => {
            const sourceDocId = edge.source_clause_id.split('_')[0];
            const targetDocId = edge.target_clause_id.split('_')[0];
            const p1 = posMap.get(sourceDocId);
            const p2 = posMap.get(targetDocId);

            if (!p1 || !p2) return null;

            const color = TYPE_COLORS[edge.relationship_type] || '#6b7280';

            return (
              <g key={idx} onClick={() => onEdgeClick && onEdgeClick(edge.finding_id)} style={{ cursor: 'pointer' }}>
                <line
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  stroke={color}
                  strokeWidth="2"
                  strokeDasharray={edge.relationship_type === 'AMBIGUOUS' ? '4 4' : 'none'}
                />
              </g>
            );
          })}

          {docPositions.map((pos) => (
            <g key={pos.id} transform={`translate(${pos.x}, ${pos.y})`}>
              <circle r="28" fill="var(--bg-tertiary)" stroke="var(--accent-primary)" strokeWidth="2" />
              <text textAnchor="middle" dy="4" fill="var(--text-primary)" fontSize="10" fontWeight="600">
                {pos.name.length > 10 ? `${pos.name.slice(0, 8)}...` : pos.name}
              </text>
            </g>
          ))}
        </svg>
      )}
    </div>
  );
};
