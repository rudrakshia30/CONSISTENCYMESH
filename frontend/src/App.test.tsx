import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';
import { Disclaimer } from './components/Disclaimer';
import { MetricsPanel } from './components/MetricsPanel';

describe('Frontend Components', () => {
  it('renders application header and title', () => {
    render(<App />);
    expect(screen.getByText('ConsistencyMesh')).toBeDefined();
  });

  it('renders legal safety disclaimer banner with note role', () => {
    render(<Disclaimer />);
    const note = screen.getByRole('note');
    expect(note).toBeDefined();
    expect(screen.getByText(/informational purposes only/i)).toBeDefined();
  });

  it('renders performance metrics grid', () => {
    const mockMetrics = {
      candidate_reduction_percent: 88,
      llm_calls_made: 5,
      p50_llm_latency_ms: 120.5,
      cache_hit_rate: 0.75,
    };
    render(<MetricsPanel metrics={mockMetrics} />);
    expect(screen.getByText('Job Performance Metrics')).toBeDefined();
    expect(screen.getByText('LLM Calls')).toBeDefined();
  });
});
