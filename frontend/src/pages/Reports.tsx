import { useEffect, useState } from 'react';
import { getCases, type Case } from '../api/cases';
import { generateReport, getReportUrl, type Report } from '../api/reports';
import { FileText, Download, Hash } from 'lucide-react';

export default function Reports() {
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>('');
  
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState<Report | null>(null);

  useEffect(() => {
    getCases().then(setCases);
  }, []);

  const handleGenerate = async () => {
    if (!selectedCase) return;
    setGenerating(true);
    setReport(null);
    try {
      const rep = await generateReport(selectedCase);
      setReport(rep);
    } catch (err: any) {
      alert(`Report generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold flex items-center">
          <FileText className="w-6 h-6 mr-3 text-amber-400" />
          Forensic Reports
        </h1>
      </div>

      <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg">
        <div className="max-w-md mx-auto space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">Select Case</label>
            <select 
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
              value={selectedCase}
              onChange={e => setSelectedCase(e.target.value)}
            >
              <option value="">Choose...</option>
              {cases.map(c => <option key={c.id} value={c.id}>{c.case_number}</option>)}
            </select>
          </div>
          
          <button 
            onClick={handleGenerate}
            disabled={!selectedCase || generating}
            className="w-full bg-amber-600 hover:bg-amber-500 disabled:bg-slate-800 disabled:text-slate-500 text-white px-4 py-2 rounded-md font-medium flex justify-center items-center transition-colors"
          >
            {generating ? (
              <>Generating PDF Document...</>
            ) : (
              <><FileText className="w-4 h-4 mr-2" /> Generate Official Report</>
            )}
          </button>
        </div>
      </div>

      {report && (
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg mt-6 text-center animate-in fade-in slide-in-from-bottom-4">
          <FileText className="w-16 h-16 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-200 mb-2">Report Generated Successfully</h2>
          <p className="text-slate-400 mb-6 max-w-md mx-auto">
            The forensic report has been compiled including the cryptographic chain of custody, AI findings, and trust seal verifications.
          </p>
          
          <div className="flex flex-col items-center justify-center space-y-4">
            <a 
              href={getReportUrl(selectedCase)}
              target="_blank"
              rel="noreferrer"
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-full font-medium flex items-center transition-colors"
            >
              <Download className="w-4 h-4 mr-2" /> Download PDF Report
            </a>
            
            <div className="bg-slate-950 px-4 py-2 rounded border border-slate-800 flex items-center text-sm font-mono text-slate-400">
              <Hash className="w-4 h-4 mr-2 text-slate-500" />
              <span className="truncate max-w-[200px] md:max-w-md">{report.sha256}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
