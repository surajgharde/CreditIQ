/**
 * useApi — Generic hook for any async API call.
 * Handles loading, error, and data state automatically.
 * Never shows a blank screen — always returns loading=true initially.
 *
 * Usage:
 *   const { data, loading, error, refetch } = useApi(() => getFullResults(id), [id]);
 */
import { useState, useEffect, useCallback, useRef } from 'react';

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string;
  refetch: () => void;
}

export function useApi<T>(
  fn: () => Promise<T>,
  deps: React.DependencyList = []
): ApiState<T> {
  const [data, setData]       = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const mountedRef             = useRef(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await fn();
      if (mountedRef.current) { setData(result); }
    } catch (e: any) {
      if (mountedRef.current) {
        setError(e.userMessage || e.message || 'An unexpected error occurred.');
      }
    } finally {
      if (mountedRef.current) { setLoading(false); }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mountedRef.current = true;
    fetch();
    return () => { mountedRef.current = false; };
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

/** Skeleton loader — replace content while loading */
export function Skeleton({ width = '100%', height = 24, style = {} }: { width?: string | number; height?: number; style?: React.CSSProperties }) {
  return (
    <div style={{
      width, height,
      borderRadius: 6,
      background: 'linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.5s infinite',
      ...style,
    }} />
  );
}

/** Error Banner — shows API errors clearly with optional retry button */
export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  if (!message) return null;
  return (
    <div style={{
      background: '#FEE2E2', border: '1px solid #FCA5A5',
      borderLeft: '4px solid #DC2626', borderRadius: 8,
      padding: '1rem 1.5rem', marginBottom: '1.5rem',
      display: 'flex', gap: 12, alignItems: 'flex-start'
    }}>
      <span style={{ fontSize: '1.2rem' }}>⚠️</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, color: '#B91C1C', marginBottom: 4 }}>Backend Error</div>
        <div style={{ color: '#7F1D1D', fontSize: '0.9rem' }}>{message}</div>
      </div>
      {onRetry && (
        <button onClick={onRetry} style={{
          background: '#DC2626', color: 'white', border: 'none',
          borderRadius: 6, padding: '6px 12px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600
        }}>
          Retry
        </button>
      )}
    </div>
  );
}
