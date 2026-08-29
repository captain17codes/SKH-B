import React, { useState, useEffect } from 'react';
import { healthAPI, auditAPI, referenceAPI } from '../api/client';

export default function DiagnosticChecks() {
  const [health, setHealth] = useState(null);
  const [audit, setAudit] = useState(null);
  const [reference, setReference] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDiagnostics = async () => {
      setLoading(true);
      try {
        const [hRes, aRes, rRes] = await Promise.all([
          healthAPI.check().catch(e => ({ status: 'error', error: e.message })),
          auditAPI.verify().catch(e => ({ ok: false, error: e.message })),
          referenceAPI.gaps().catch(e => ({ error: e.message }))
        ]);
        setHealth(hRes);
        setAudit(aRes);
        setReference(rRes);
      } catch (err) {
        console.error("Diagnostics error", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDiagnostics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-4 bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm mb-6 animate-pulse">
        <span className="material-symbols-outlined text-outline">sync</span>
        <span className="text-on-surface-variant font-label-sm">Running system diagnostics...</span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      
      {/* Health API Card */}
      <div className={`p-4 rounded-xl border shadow-sm ${health?.status === 'healthy' ? 'bg-primary-container/20 border-primary-container' : 'bg-error-container/20 border-error-container'}`}>
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-bold text-sm text-on-surface flex items-center gap-2">
            <span className={`material-symbols-outlined ${health?.status === 'healthy' ? 'text-primary' : 'text-error'}`}>
              {health?.status === 'healthy' ? 'health_and_safety' : 'warning'}
            </span>
            System Health
          </h3>
          <span className={`text-xs px-2 py-0.5 rounded ${health?.status === 'healthy' ? 'bg-primary text-on-primary' : 'bg-error text-on-error'}`}>
            {health?.status || 'UNKNOWN'}
          </span>
        </div>
        <div className="text-xs text-on-surface-variant mt-2 space-y-1">
          {health?.version && <p>Version: <span className="font-mono">{health.version}</span></p>}
          <p>Database: {health?.database?.reachable ? 'Connected' : 'Unreachable'}</p>
        </div>
      </div>

      {/* Audit API Card */}
      <div className={`p-4 rounded-xl border shadow-sm ${audit?.ok ? 'bg-primary-container/20 border-primary-container' : 'bg-error-container/20 border-error-container'}`}>
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-bold text-sm text-on-surface flex items-center gap-2">
            <span className={`material-symbols-outlined ${audit?.ok ? 'text-primary' : 'text-error'}`}>
              {audit?.ok ? 'verified_user' : 'gpp_bad'}
            </span>
            Audit Chain
          </h3>
          <span className={`text-xs px-2 py-0.5 rounded ${audit?.ok ? 'bg-primary text-on-primary' : 'bg-error text-on-error'}`}>
            {audit?.ok ? 'VERIFIED' : 'BROKEN'}
          </span>
        </div>
        <div className="text-xs text-on-surface-variant mt-2 space-y-1">
          <p>Chain Length: <span className="font-mono font-bold text-on-surface">{audit?.entries ?? 0}</span> entries</p>
          {audit?.ok && audit?.tip_hash && (
            <p>Tip: <span className="font-mono">{audit.tip_hash.slice(0, 12)}…</span></p>
          )}
          {!audit?.ok && audit?.first_broken_seq != null && (
            <p className="text-error font-medium mt-1">First Bad Sequence: <span className="font-mono font-bold bg-error-container px-1 rounded">{audit.first_broken_seq}</span> ({audit.break_type})</p>
          )}
        </div>
      </div>

      {/* Reference API Card */}
      <div className="p-4 rounded-xl border shadow-sm bg-surface-container-lowest border-outline-variant/20">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-bold text-sm text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary">
              library_books
            </span>
            Reference Data
          </h3>
          <span className="text-xs px-2 py-0.5 rounded bg-surface-variant text-on-surface-variant">
            GAPS
          </span>
        </div>
        <div className="text-xs text-on-surface-variant mt-2 space-y-1">
          <p>Known Gaps: <span className="font-bold text-on-surface">{reference?.gaps?.length ?? 0}</span> (each with a stated fallback)</p>
          <p>Missing Dataset Files: <span className="font-bold text-on-surface">{reference?.missing_dataset_files?.length ?? 0}</span></p>
          <p>Categories With No Response Target: <span className="font-bold text-on-surface">{reference?.categories_without_response_target?.length ?? 0}</span></p>
        </div>
      </div>

    </div>
  );
}
