import React, { useState, useEffect } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { useSearchParams, Link } from 'react-router-dom';
import { explainAPI } from '../api/client';

export default function CitizenInsightsPage() {
  const [searchParams] = useSearchParams();
  const ticketId = searchParams.get('ticketId');
  const refNo = searchParams.get('ref_no');
  const isDuplicate = searchParams.get('dup') === 'true';

  const [lang, setLang] = useState('en');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ticketId) {
      setError("No ticket ID provided.");
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await explainAPI.citizen(ticketId, lang);
        setData(res);
      } catch (err) {
        console.error(err);
        setError("Failed to load explanation.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [ticketId, lang]);

  return (
    <div className="bg-surface text-on-surface font-body-md min-h-screen relative flex flex-col">
      {/* Header */}
      <div className="bg-primary text-on-primary py-6 shadow-md">
        <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-4xl">location_city</span>
              <div>
                <h1 className="text-headline-md font-headline-md font-bold">Kopargaon Municipal Council</h1>
                <p className="text-body-md opacity-90">Ticket Tracking & AI Insights</p>
              </div>
            </div>
            <Link to="/submit" className="flex items-center gap-2 bg-on-primary text-primary px-4 py-2 rounded font-bold hover:bg-gray-100 transition-colors">
              <span className="material-symbols-outlined">add</span>
              New Report
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 max-w-container-max w-full mx-auto px-margin-mobile md:px-margin-desktop py-8">
        <div className="max-w-3xl mx-auto">
          
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-outline-variant/30 pb-4">
            <div>
              <h2 className="text-headline-sm font-headline-sm text-primary">
                Ticket Reference: <span className="font-mono">{refNo || data?.ref_no || ticketId?.substring(0,8)}</span>
              </h2>
            </div>
            
            <div className="flex items-center bg-surface-container-high rounded-lg overflow-hidden border border-outline-variant/20 p-1 shadow-sm">
              <button 
                onClick={() => setLang('en')}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${lang === 'en' ? 'bg-primary text-on-primary shadow' : 'text-on-surface-variant hover:bg-surface-variant/50'}`}
              >
                English
              </button>
              <button 
                onClick={() => setLang('mr')}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${lang === 'mr' ? 'bg-primary text-on-primary shadow' : 'text-on-surface-variant hover:bg-surface-variant/50'}`}
              >
                मराठी
              </button>
            </div>
          </div>

          {isDuplicate && (
            <div className="bg-tertiary-container text-on-tertiary-container p-4 rounded-lg mb-6 flex items-start gap-3 shadow-sm">
              <span className="material-symbols-outlined shrink-0 mt-0.5">merge</span>
              <div>
                <h3 className="font-bold">Duplicate Report Merged</h3>
                <p className="text-sm mt-1">This issue was merged with an existing report for faster resolution. The combined report carries more community weight.</p>
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-on-surface-variant">
              <span className="material-symbols-outlined animate-spin text-4xl mb-4">progress_activity</span>
              <p>Fetching AI explanation...</p>
            </div>
          ) : error ? (
            <div className="bg-error-container text-on-error-container p-4 rounded-lg">
              <span className="material-symbols-outlined">error</span> {error}
            </div>
          ) : data ? (
            <div className="space-y-6">
              
              {data.translation_status === 'machine_drafted_pending_council_review' && lang === 'mr' && (
                <div className="bg-error-container text-on-error-container p-4 rounded-lg flex items-start gap-3 shadow-sm border border-error/20">
                  <span className="material-symbols-outlined shrink-0 text-error">warning</span>
                  <div>
                    <h3 className="font-bold text-error">Pending Council Review / अधिकृत पुष्टीकरणाच्या प्रतीक्षेत</h3>
                    <p className="text-sm mt-1">
                      This text is machine-drafted and pending official council review. 
                      <br/>
                      हे मजकूर मशीन-ड्राफ्ट केलेले आहे आणि अधिकृत नगर परिषद पुनरावलोकनाच्या प्रतीक्षेत आहे.
                    </p>
                  </div>
                </div>
              )}

              <div className="glass-panel rounded-xl p-6 md:p-8">
                <div className="flex items-center gap-3 mb-4">
                  <span className="material-symbols-outlined text-primary text-2xl">auto_awesome</span>
                  <h3 className="text-title-lg font-bold text-on-surface">AI Decision Explanation</h3>
                </div>

                <div className="prose prose-on-surface max-w-none">
                  <p className="text-lg leading-relaxed mb-6 bg-surface-variant/30 p-4 rounded-lg border-l-4 border-primary">
                    {data.outcome_sentence}
                  </p>
                  
                  <div className="bg-surface-container p-4 rounded-lg">
                    <h4 className="font-bold text-sm text-on-surface-variant uppercase tracking-wider mb-2">Next Step</h4>
                    <p className="text-body-lg">
                      {data.next_step}
                    </p>
                  </div>
                  
                  <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-outline-variant/30 text-sm">
                    <div>
                      <span className="block text-on-surface-variant mb-1 text-xs">Decision</span>
                      <span className="font-bold text-primary px-2 py-1 bg-primary-container rounded">{data.decision}</span>
                    </div>
                    <div>
                      <span className="block text-on-surface-variant mb-1 text-xs">Scored</span>
                      <span className="font-bold">{data.scored ? 'Yes' : 'No'}</span>
                    </div>
                    <div>
                      <span className="block text-on-surface-variant mb-1 text-xs">Dispatch Date</span>
                      <span className="font-bold">{data.dispatch_date || 'TBD'}</span>
                    </div>
                    <div>
                      <span className="block text-on-surface-variant mb-1 text-xs">Reason Code</span>
                      <span className="font-mono text-xs">{data.reason_code}</span>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          ) : null}

        </div>
      </div>
      
      {/* Footer */}
      <footer className="bg-surface-container border-t border-outline-variant mt-auto py-6">
        <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop text-center">
          <p className="text-sm text-on-surface-variant">
            © 2026 Kopargaon Municipal Council | Class 'B' Local Body, Ahilyanagar District
          </p>
        </div>
      </footer>
    </div>
  );
}
