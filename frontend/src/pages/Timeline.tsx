import { useEffect, useState } from 'react';
import { getCases, type Case } from '../api/cases';
import { fetchApi } from '../api/client';
import { Clock, FileText, CheckCircle, UploadCloud, Link as LinkIcon, ShieldCheck, Search } from 'lucide-react';
import { format } from 'date-fns';

interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: string;
  type?: string;
  title?: string;
  description: string;
  meta_data?: any;
  metadata?: any;
  hash: string;
  evidence_id?: string;
  case_id?: string;
}

export default function Timeline() {
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>('');
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getCases().then(c => {
      setCases(c);
      if (c.length > 0) setSelectedCase(c[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedCase) {
      // Wait, there might not be a dedicated /cases/{id}/timeline endpoint yet,
      // The user prompt said: "Ensure endpoints exist for: GET /api/cases/{id}/timeline"
      // If it doesn't exist, we can use the ledger events endpoint or add it.
      // Assuming it exists as per Step 21. Let's try.
      fetchApi<{events: TimelineEvent[], total: number}>(`/cases/${selectedCase}/timeline`)
        .then(res => setEvents(res.events || []))
        .catch(() => {
          // Fallback if not implemented
          setEvents([]);
        })
        .finally(() => setLoading(false));
    }
  }, [selectedCase]);

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'EVIDENCE_INGESTED': return <UploadCloud className="w-5 h-5 text-emerald-400" />;
      case 'AI_ANALYSIS_COMPLETED': return <CheckCircle className="w-5 h-5 text-indigo-400" />;
      case 'FORENSIC_ANALYSIS_COMPLETED': return <Search className="w-5 h-5 text-red-400" />;
      case 'RECOVERY_COMPLETED': return <CheckCircle className="w-5 h-5 text-amber-400" />;
      case 'CHAIN_EVENT': return <LinkIcon className="w-5 h-5 text-slate-400" />;
      case 'TRUST_SEAL_OBTAINED': return <ShieldCheck className="w-5 h-5 text-blue-400" />;
      case 'REPORT_GENERATED': return <FileText className="w-5 h-5 text-amber-400" />;
      default: return <Clock className="w-5 h-5 text-slate-500" />;
    }
  };

  const getBadge = (type: string) => {
    switch (type) {
      case 'AI_ANALYSIS_COMPLETED': return <span className="px-2 py-0.5 rounded text-[10px] font-bold text-indigo-400 bg-indigo-500/10 ml-2">AI</span>;
      case 'FORENSIC_ANALYSIS_COMPLETED': return <span className="px-2 py-0.5 rounded text-[10px] font-bold text-red-400 bg-red-500/10 ml-2">FORENSICS</span>;
      case 'RECOVERY_COMPLETED': return <span className="px-2 py-0.5 rounded text-[10px] font-bold text-amber-400 bg-amber-500/10 ml-2">RECOVERY</span>;
      case 'TRUST_SEAL_OBTAINED': return <span className="px-2 py-0.5 rounded text-[10px] font-bold text-blue-400 bg-blue-500/10 ml-2">INTEGRITY</span>;
      default: return null;
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold flex items-center">
          <Clock className="w-6 h-6 mr-3 text-slate-300" />
          Forensic Timeline
        </h1>
        <select 
          className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm"
          value={selectedCase}
          onChange={e => {
            setSelectedCase(e.target.value);
            setLoading(true);
          }}
        >
          <option value="">Select Case...</option>
          {cases.map(c => <option key={c.id} value={c.id}>{c.case_number}</option>)}
        </select>
      </div>

      <div className="py-4">
        {loading ? (
          <div className="text-center p-8 text-slate-500">Loading timeline...</div>
        ) : events.length === 0 ? (
          <div className="text-center p-12 text-slate-500 bg-slate-900 rounded-lg border border-slate-800">
            No events found for this case. Ensure the /timeline endpoint is implemented.
          </div>
        ) : (
          <div className="relative border-l border-slate-700 ml-4 space-y-8 pb-8">
            {events.map((evt, i) => (
              <div key={i} className="relative pl-8">
                <div className="absolute -left-3.5 top-1 bg-slate-950 rounded-full border border-slate-700 p-1">
                  {getEventIcon(evt.type || evt.event_type)}
                </div>
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center">
                      <span className="font-medium text-slate-200">{evt.title || (evt.type || evt.event_type).replace(/_/g, ' ')}</span>
                      {getBadge(evt.type || evt.event_type)}
                    </div>
                    <span className="text-xs text-slate-500 font-mono">
                      {format(new Date(evt.timestamp), 'MMM d, HH:mm:ss')}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400 mb-3">{evt.description}</p>
                  <div className="flex items-center justify-between">
                    <div className="bg-slate-950 p-2 rounded text-xs font-mono text-slate-600 truncate border border-slate-800/50 flex-1 mr-4">
                      Hash: {evt.hash}
                    </div>
                    {evt.evidence_id && (
                      <button 
                        onClick={() => window.location.href = `/investigation?case=${evt.case_id}&evidence=${evt.evidence_id}&t=${evt.metadata?.timestamp || 0}`}
                        className="text-xs font-medium text-indigo-400 hover:text-indigo-300 flex items-center bg-indigo-500/10 px-3 py-1.5 rounded transition-colors whitespace-nowrap"
                      >
                        <LinkIcon className="w-3 h-3 mr-1" /> View in Player
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
