import { useEffect, useState } from 'react';
import { getCases, type Case } from '../api/cases';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<any[]>([]);

  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      getCases(),
      fetch('http://localhost:8000/api/ai/models').then(res => res.json()).catch(() => ({ models: [] })),
      fetch('http://localhost:8000/api/stats').then(res => res.json()).catch(() => ({}))
    ])
      .then(([casesData, modelsData, statsData]) => {
        setCases(casesData);
        setModels(modelsData.models || []);
        setStats(statsData);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-slate-400">Loading dashboard...</div>;
  if (error) return <div className="text-red-400 bg-red-900/20 p-4 rounded-md">Error: {error}</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <h3 className="text-slate-400 font-medium text-xs uppercase tracking-wider mb-2">Evidence</h3>
          <p className="text-2xl font-bold text-slate-200">{stats?.evidence_count || 0}</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <h3 className="text-slate-400 font-medium text-xs uppercase tracking-wider mb-2">Recovered Artifacts</h3>
          <p className="text-2xl font-bold text-slate-200">{stats?.recovered_artifacts || 0}</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <h3 className="text-slate-400 font-medium text-xs uppercase tracking-wider mb-2">AI Analyses</h3>
          <p className="text-2xl font-bold text-slate-200">{stats?.ai_analyses || 0}</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <h3 className="text-slate-400 font-medium text-xs uppercase tracking-wider mb-2">Forensic Findings</h3>
          <p className="text-2xl font-bold text-slate-200">{stats?.forensic_findings || 0}</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <h3 className="text-slate-400 font-medium text-xs uppercase tracking-wider mb-2">Cameras</h3>
          <p className="text-2xl font-bold text-slate-200">{stats?.cameras || 0}</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <h3 className="text-slate-400 font-medium text-xs uppercase tracking-wider mb-2">Integrity</h3>
          <p className={`text-xl font-bold ${stats?.integrity_status === 'VALID' ? 'text-emerald-400' : 'text-red-400'}`}>{stats?.integrity_status || 'UNKNOWN'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Recent Cases */}
        <div className="md:col-span-2 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800">
            <h2 className="text-lg font-medium">Recent Cases</h2>
            </div>
            {cases.length === 0 ? (
            <div className="p-6 text-slate-400 text-center">No cases found.</div>
            ) : (
            <ul className="divide-y divide-slate-800">
                {cases.slice(0, 5).map((c) => (
                <li key={c.id} className="p-6 hover:bg-slate-800/50 transition-colors">
                    <div className="flex justify-between items-center">
                    <div>
                        <Link to={`/cases/${c.id}`} className="text-indigo-400 hover:text-indigo-300 font-medium text-lg">
                        {c.case_number}: {c.title}
                        </Link>
                        <div className="text-sm text-slate-500 mt-1">
                        Investigator: {c.investigator} | Created: {new Date(c.created_at).toLocaleDateString()}
                        </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        c.status === 'OPEN' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
                    }`}>
                        {c.status}
                    </span>
                    </div>
                </li>
                ))}
            </ul>
            )}
        </div>

        {/* AI Status */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                <h2 className="text-lg font-medium">AI Status</h2>
            </div>
            <div className="p-6 flex-1 bg-slate-950">
                <div className="space-y-3 font-mono text-sm">
                    {models.length === 0 && <div className="text-slate-500">Connecting to Engine...</div>}
                    {[
                        { key: 'object_detection', label: 'OBJECT DETECTION', type: 'model' },
                        { key: 'tracking', label: 'TRACKING', type: 'model' },
                        { key: 'face_detection', label: 'FACE DETECTION', type: 'model' },
                        { key: 'face_recognition', label: 'FACE SEARCH', type: 'model' },
                        { key: 'ocr', label: 'ANPR', type: 'model' },
                        { key: 'reid', label: 'CROSS-CAMERA RE-ID', type: 'model' },
                        { key: 'forensics', label: 'VIDEO FORENSICS', type: 'service', status: 'READY' },
                        { key: 'recovery', label: 'RECOVERY', type: 'service', status: 'READY' }
                    ].map(cap => {
                        let status = 'UNAVAILABLE';
                        if (cap.type === 'service') {
                            status = cap.status || 'READY';
                        } else {
                            const model = models.find(m => m.task === cap.key);
                            if (model && model.status === 'AVAILABLE') status = 'READY';
                        }
                        
                        return (
                            <div key={cap.key} className="flex justify-between items-center pb-2 border-b border-slate-800/50">
                                <span className="text-slate-300">{cap.label}</span>
                                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                                    status === 'READY' ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'
                                }`}>
                                    {status}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}
