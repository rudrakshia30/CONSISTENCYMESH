import React from 'react';

export interface MetricsPanelProps {
  metrics: Record<string, number>;
}

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ metrics }) => {
  const documentCount = metrics['documentCount'] ?? 0;
  const totalClauses = metrics['totalClauses'] ?? 0;
  const naivePairs = metrics['naivePairs'] ?? 0;
  const filteredPairs = metrics['filteredPairs'] ?? 0;
  
  const candidateReduction = metrics['candidateReduction'] ?? 0;
  const llmCalls = metrics['llmCalls'] ?? 0;
  const cacheHitRate = metrics['cacheHitRate'] ?? 0;
  
  const p50Latency = metrics['p50Latency'] ?? 0;
  const p95Latency = metrics['p95Latency'] ?? 0;
  const wallClockTime = metrics['wallClockTime'] ?? 0;
  const totalTokens = metrics['totalTokens'] ?? 0;

  const cards = [
    { label: 'Document Count', value: documentCount },
    { label: 'Total Clauses', value: totalClauses },
    { label: 'Naive Pairs', value: naivePairs },
    { label: 'Filtered Pairs', value: filteredPairs },
    { label: 'Candidate Reduction (%)', value: `${candidateReduction}%` },
    { label: 'LLM Calls', value: llmCalls },
    { label: 'Cache Hit Rate (%)', value: `${cacheHitRate}%` },
    { label: 'p50 Latency (ms)', value: p50Latency },
    { label: 'p95 Latency (ms)', value: p95Latency },
    { label: 'Wall Clock Time (s)', value: wallClockTime },
    { label: 'Total Tokens', value: totalTokens },
  ];

  return (
    <div className="metrics-panel">
      <h2>Job Performance Metrics</h2>
      <div className="metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
        {cards.map((card, idx) => (
          <div key={idx} className="metric-card" style={{ padding: '1rem', border: '1px solid #ccc', borderRadius: '4px' }}>
            <div className="metric-label" style={{ fontSize: '0.875rem', color: '#666' }}>{card.label}</div>
            <div className="metric-value" style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{card.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
