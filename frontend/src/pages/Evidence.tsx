import { useEffect, useState, useRef } from 'react';
import { getCases, type Case } from '../api/cases';
import { uploadEvidence, getEvidenceForCase, type Evidence as EvidenceItem } from '../api/evidence';
import { UploadCloud, Film, HardDrive, CheckCircle } from 'lucide-react';
import { format } from 'date-fns';

export default function Evidence() {
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCases().then(data => {
      setCases(data);
      if (data.length > 0) {
        setSelectedCaseId(data[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      getEvidenceForCase(selectedCaseId)
        .then(setEvidenceList)
        .finally(() => setLoading(false));
    }
  }, [selectedCaseId]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0 || !selectedCaseId) return;
    const file = e.target.files[0];
    setUploading(true);
    
    try {
      const newEv = await uploadEvidence(selectedCaseId, file, {
        source_device: 'Web Upload',
        evidence_type: 'video'
      });
      setEvidenceList([...evidenceList, newEv]);
      alert('Evidence imported successfully!');
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center">
          <Film className="w-6 h-6 mr-3 text-emerald-400" />
          Evidence
        </h1>
        <div className="flex items-center space-x-3">
          <label className="text-sm font-medium text-slate-400">Target Case:</label>
          <select 
            className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
            value={selectedCaseId}
            onChange={(e) => {
              setSelectedCaseId(e.target.value);
              setLoading(true);
            }}
          >
            <option value="">Select Case...</option>
            {cases.map(c => <option key={c.id} value={c.id}>{c.case_number}</option>)}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Zone */}
        <div className="lg:col-span-1">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg h-full flex flex-col justify-center items-center text-center border-dashed border-2 relative overflow-hidden group hover:border-indigo-500/50 transition-colors">
            <input 
              type="file" 
              ref={fileInputRef}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
              onChange={handleUpload}
              disabled={uploading || !selectedCaseId}
            />
            {uploading ? (
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin mx-auto"></div>
                <div className="text-indigo-400 font-medium">Acquiring Evidence...</div>
                <div className="text-xs text-slate-500">Computing SHA-256 hash...</div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto group-hover:bg-indigo-500/10 transition-colors">
                  <UploadCloud className="w-8 h-8 text-slate-400 group-hover:text-indigo-400" />
                </div>
                <div>
                  <div className="font-medium text-slate-200">Drop video file here</div>
                  <div className="text-sm text-slate-500 mt-1">or click to browse</div>
                </div>
                <div className="text-xs text-slate-600">
                  Supported: MP4, AVI, MKV, JPG, DD (Max 2GB)
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Evidence List */}
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            <div className="bg-slate-900 border border-slate-800 p-8 rounded-lg text-center text-slate-400">Loading...</div>
          ) : evidenceList.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 p-8 rounded-lg text-center text-slate-400 flex flex-col items-center justify-center h-full">
              <HardDrive className="w-12 h-12 text-slate-700 mb-3" />
              No evidence acquired for this case yet.
            </div>
          ) : (
            evidenceList.map(ev => (
              <div key={ev.id} className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
                  <div className="flex items-center">
                    <Film className="w-5 h-5 text-emerald-400 mr-3" />
                    <span className="font-medium text-slate-200 truncate max-w-sm" title={ev.original_filename}>{ev.original_filename}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs px-2 py-1 rounded">HASH RECORDED</span>
                    {ev.status === 'SEALED' && (
                      <span className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs px-2 py-1 rounded flex items-center">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        EVIDENCE SEALED
                      </span>
                    )}
                  </div>
                </div>
                <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-950/50 text-sm">
                  <div>
                    <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">Acquired At</div>
                    <div className="text-slate-200">{format(new Date(ev.acquired_at), 'MMM d, yyyy HH:mm')}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">Size</div>
                    <div className="text-slate-200">{formatBytes(ev.size)}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">MIME Type</div>
                    <div className="text-slate-200">{ev.mime_type || 'Unknown'}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">Source / Vendor</div>
                    <div className="text-slate-200">{ev.source_device || 'Unknown'} / {ev.source_vendor || 'Unknown'}</div>
                  </div>
                  {ev.evidence_type === 'video' && (
                    <>
                      <div>
                        <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">Duration</div>
                        <div className="text-slate-200">{ev.duration ? `${ev.duration.toFixed(2)}s` : 'Unknown'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">Resolution</div>
                        <div className="text-slate-200">{ev.resolution || 'Unknown'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">FPS</div>
                        <div className="text-slate-200">{ev.fps ? ev.fps.toFixed(2) : 'Unknown'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">Codec</div>
                        <div className="text-slate-200">{ev.codec || 'Unknown'}</div>
                      </div>
                    </>
                  )}
                  <div className="col-span-2 md:col-span-4">
                    <div className="text-slate-500 text-xs uppercase tracking-wider mb-1">SHA-256 Hash</div>
                    <div className="font-mono text-emerald-400 truncate" title={ev.sha256}>{ev.sha256}</div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
