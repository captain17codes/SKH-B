/**
 * Triage Panel - Block 2 (Assistant 1)
 * Run Fuzzy TOPSIS + Knapsack optimization
 */
import React, { useState } from 'react';
import { triageAPI } from '../api/client';

export default function TriagePanel({ onTriageComplete }) {
  const [dailyBudget, setDailyBudget] = useState(100000);
  const [dailyWorkforce, setDailyWorkforce] = useState(80);
  const [wardId, setWardId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await triageAPI.run(dailyBudget, dailyWorkforce, wardId || null);
      setResult(res);
      if (onTriageComplete) onTriageComplete(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-2">Run Triage Optimization</h3>
      <p className="text-gray-600 mb-6">
        Run Fuzzy TOPSIS prioritization followed by Knapsack allocation to generate today's dispatch manifest.
      </p>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {result && (
        <div className="bg-green-50 border-l-4 border-green-500 p-4 mb-4">
          <p className="text-green-700 font-medium">{result.message}</p>
          <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Prioritized:</span>
              <span className="font-semibold ml-1">{result.prioritized_count}</span>
            </div>
            <div>
              <span className="text-gray-600">Scheduled:</span>
              <span className="font-semibold ml-1 text-green-600">{result.scheduled_count}</span>
            </div>
            <div>
              <span className="text-gray-600">Deferred:</span>
              <span className="font-semibold ml-1 text-orange-600">{result.deferred_count}</span>
            </div>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Total CCi Score: {result.total_cci_score?.toFixed(3)}
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Daily Budget (₹)
            </label>
            <input
              type="number"
              value={dailyBudget}
              onChange={(e) => setDailyBudget(Number(e.target.value))}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              min={0}
              step={1000}
              required
            />
            <p className="text-xs text-gray-500 mt-1">e.g., 100000 for ₹1,00,000</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Daily Workforce Hours
            </label>
            <input
              type="number"
              value={dailyWorkforce}
              onChange={(e) => setDailyWorkforce(Number(e.target.value))}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              min={0}
              step={8}
              required
            />
            <p className="text-xs text-gray-500 mt-1">e.g., 80 hours (10 workers × 8h)</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ward (optional)
          </label>
          <select
            value={wardId}
            onChange={(e) => setWardId(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Wards</option>
            {Array.from({ length: 10 }, (_, i) => (
              <option key={i + 1} value={`Ward-${i + 1}`}>Ward-{i + 1}</option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Leave blank to triage all wards
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              Running Triage...
            </span>
          ) : (
            'Run Triage'
          )}
        </button>
      </form>
    </div>
  );
}
