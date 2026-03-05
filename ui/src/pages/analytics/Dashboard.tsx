import { useEffect, useState } from 'react';
import { getAnalytics } from '../../api/client';
import type { AnalyticsSummary } from '../../api/types';

interface Props {
  slug: string;
}

function StatCard({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="bg-gray-800/60 rounded-xl p-5 border border-gray-700/50">
      <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-semibold text-white">
        {value}
        {unit && <span className="text-sm text-gray-400 ml-1">{unit}</span>}
      </p>
    </div>
  );
}

export default function AnalyticsDashboard({ slug }: Props) {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAnalytics(slug)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen bg-para-navy flex items-center justify-center">
        <div className="flex gap-1">
          <span className="w-3 h-3 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-3 h-3 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-3 h-3 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-para-navy flex items-center justify-center text-red-400">
        Failed to load analytics: {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-para-navy text-white p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-1">Monitoring Dashboard</h1>
        <p className="text-gray-400 text-sm mb-6">{slug}</p>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Queries" value={data.total_queries} />
          <StatCard
            label="Avg Confidence"
            value={data.avg_confidence !== null ? `${(data.avg_confidence * 100).toFixed(1)}` : '--'}
            unit="%"
          />
          <StatCard
            label="Avg Latency"
            value={data.avg_latency_ms !== null ? `${(data.avg_latency_ms / 1000).toFixed(1)}` : '--'}
            unit="s"
          />
          <StatCard
            label="Silence Rate"
            value={`${(data.silence_rate * 100).toFixed(1)}`}
            unit="%"
          />
        </div>

        {/* Two-column layout */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Queries Per Day */}
          <div className="bg-gray-800/60 rounded-xl p-5 border border-gray-700/50">
            <h2 className="text-sm font-medium text-gray-300 mb-3 uppercase tracking-wider">Queries Per Day</h2>
            {data.queries_per_day.length === 0 ? (
              <p className="text-gray-500 text-sm">No data yet</p>
            ) : (
              <div className="space-y-2">
                {data.queries_per_day.slice(0, 14).map((day) => (
                  <div key={day.date} className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">{day.date}</span>
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 bg-para-teal rounded"
                        style={{ width: `${Math.max(8, (day.count / Math.max(...data.queries_per_day.map((d) => d.count))) * 120)}px` }}
                      />
                      <span className="text-gray-300 w-8 text-right">{day.count}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Top Intents */}
          <div className="bg-gray-800/60 rounded-xl p-5 border border-gray-700/50">
            <h2 className="text-sm font-medium text-gray-300 mb-3 uppercase tracking-wider">Top Intent Classes</h2>
            {data.top_intents.length === 0 ? (
              <p className="text-gray-500 text-sm">No data yet</p>
            ) : (
              <div className="space-y-3">
                {data.top_intents.map((intent) => (
                  <div key={intent.intent}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-300 capitalize">{intent.intent}</span>
                      <span className="text-gray-400">{intent.count}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-1.5">
                      <div
                        className="bg-para-teal h-1.5 rounded-full"
                        style={{ width: `${(intent.count / data.top_intents[0].count) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
