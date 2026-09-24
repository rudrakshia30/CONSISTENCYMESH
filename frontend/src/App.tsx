import React, { useState } from 'react';
import type { AnalysisResult } from './services/api';
import { UploadWorkspace } from './components/UploadWorkspace';
import { AnalysisProgress } from './components/AnalysisProgress';
import { ConsistencyReport } from './components/ConsistencyReport';
import { RelationshipGraph } from './components/RelationshipGraph';
import { QAPanel } from './components/QAPanel';
import { MetricsPanel } from './components/MetricsPanel';

type PageState = 'upload' | 'analyzing' | 'report';
type ReportTab = 'report' | 'graph' | 'qa' | 'metrics';

export const App: React.FC = () => {
  const [pageState, setPageState] = useState<PageState>('upload');
  const [reportTab, setReportTab] = useState<ReportTab>('report');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

  const handleStartAnalysis = async (docIds: string[]) => {
    try {
      const { api } = await import('./services/api');
      const resp = await api.createAnalysis(docIds);
      setActiveJobId(resp.job_id);
      setPageState('analyzing');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start analysis job');
    }
  };

  const handleAnalysisComplete = (result: AnalysisResult) => {
    setAnalysisResult(result);
    setPageState('report');
  };

  const handleReset = () => {
    setPageState('upload');
    setActiveJobId(null);
    setAnalysisResult(null);
    setReportTab('report');
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="header-content">
          <div className="header-brand">
            <span style={{ fontSize: '1.5rem' }}>🕸️</span>
            <div>
              <h1>ConsistencyMesh</h1>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Multi-Document Consistency Engine
              </span>
            </div>
          </div>

          <nav className="header-nav">
            {pageState !== 'upload' && (
              <button className="btn btn-secondary btn-sm" onClick={handleReset} type="button">
                + New Analysis
              </button>
            )}
          </nav>
        </div>
      </header>

      <main className="app-main">
        {pageState === 'upload' && (
          <UploadWorkspace onAnalyze={handleStartAnalysis} />
        )}

        {pageState === 'analyzing' && activeJobId && (
          <AnalysisProgress jobId={activeJobId} onComplete={handleAnalysisComplete} />
        )}

        {pageState === 'report' && analysisResult && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
              <h2>Consistency Analysis Report</h2>
              <div className="tabs">
                <button
                  className={`tab ${reportTab === 'report' ? 'active' : ''}`}
                  onClick={() => setReportTab('report')}
                  type="button"
                >
                  📋 Findings ({analysisResult.findings.length})
                </button>
                <button
                  className={`tab ${reportTab === 'graph' ? 'active' : ''}`}
                  onClick={() => setReportTab('graph')}
                  type="button"
                >
                  🕸️ Relationship Graph
                </button>
                <button
                  className={`tab ${reportTab === 'qa' ? 'active' : ''}`}
                  onClick={() => setReportTab('qa')}
                  type="button"
                >
                  💬 Follow-up Q&A
                </button>
                <button
                  className={`tab ${reportTab === 'metrics' ? 'active' : ''}`}
                  onClick={() => setReportTab('metrics')}
                  type="button"
                >
                  📊 Performance Metrics
                </button>
              </div>
            </div>

            {reportTab === 'report' && (
              <ConsistencyReport findings={analysisResult.findings} documents={analysisResult.documents} />
            )}

            {reportTab === 'graph' && (
              <RelationshipGraph
                graph={analysisResult.graph}
                documents={analysisResult.documents}
                findings={analysisResult.findings}
              />
            )}

            {reportTab === 'qa' && (
              <QAPanel jobId={analysisResult.job_id} />
            )}

            {reportTab === 'metrics' && (
              <MetricsPanel metrics={analysisResult.metrics} />
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
