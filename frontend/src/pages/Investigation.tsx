import { useEffect, useState, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { getCases, type Case } from '../api/cases';
import { getEvidenceForCase, type Evidence } from '../api/evidence';
import { getDetections, analyzeEvidence, type AIResult } from '../api/investigation';
import { analyzeForensics, getForensics, type ForensicFinding } from '../api/forensics';
import { getRecoveredSegments, runRecovery, type RecoveredSegment } from '../api/recovery';
import { Play, Pause, FastForward, ScanSearch, AlertCircle, Maximize2, Search, FileSearch, HardDrive, Cpu } from 'lucide-react';
import { API_BASE_URL } from '../api/client';

export default function Investigation() {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const initialCaseId = searchParams.get('case') || '';
  const initialEvidenceId = searchParams.get('evidence') || '';
  const initialTime = parseFloat(searchParams.get('t') || '0');

  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>(initialCaseId);
  
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  
  const [detections, setDetections] = useState<AIResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [forensicFindings, setForensicFindings] = useState<ForensicFinding[]>([]);
  const [recoveredSegments, setRecoveredSegments] = useState<RecoveredSegment[]>([]);

  
  // Tabs: overview, objects, people, vehicles, plates, faces, cross_camera, anomalies
  const [activeTab, setActiveTab] = useState('overview');
  const [searchQuery, setSearchQuery] = useState('');
  
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    getCases().then(c => {
      setCases(c);
      if (initialCaseId && !c.find(x => x.id === initialCaseId) && c.length > 0) {
        setSelectedCase(c[0].id);
      }
    });
  }, [initialCaseId]);

  useEffect(() => {
    if (selectedCase) {
      getEvidenceForCase(selectedCase).then(list => {
        setEvidenceList(list);
        if (initialEvidenceId) {
          const ev = list.find(e => e.id === initialEvidenceId);
          if (ev) setSelectedEvidence(ev);
        }
      });
    }
  }, [selectedCase, initialEvidenceId]);

  const loadDetections = useCallback(() => {
    if (!selectedEvidence) return;
    setLoading(true);
    let apiFilter = undefined;
    if (activeTab === 'faces') apiFilter = 'face';
    if (activeTab === 'objects') apiFilter = 'object';
    if (activeTab === 'plates') apiFilter = 'plate';
    // 'people' and 'vehicles' would map to specific object labels in a real app
    
    if (activeTab === 'recovery') {
      getRecoveredSegments(selectedEvidence.id)
        .then(res => setRecoveredSegments(res))
        .finally(() => setLoading(false));
    } else if (activeTab === 'anomalies') {
      getForensics(selectedEvidence.id)
        .then(res => setForensicFindings(res))
        .finally(() => setLoading(false));
    } else {
      getDetections(selectedEvidence.id, apiFilter)
        .then(res => setDetections(res.results))
        .finally(() => setLoading(false));
    }
  }, [selectedEvidence, activeTab]);

  useEffect(() => {
    if (selectedEvidence) {
      // eslint-disable-next-line react/set-state-in-effect
      loadDetections();
    }
  }, [selectedEvidence, loadDetections]);

  useEffect(() => {
    if (videoRef.current && initialTime > 0) {
      const handleCanPlay = () => {
        if (videoRef.current) {
          videoRef.current.currentTime = initialTime;
          videoRef.current.removeEventListener('canplay', handleCanPlay);
        }
      };
      videoRef.current.addEventListener('canplay', handleCanPlay);
    }
  }, [selectedEvidence, initialTime]);



  const handleAnalyze = async () => {
    if (!selectedEvidence) return;
    setAnalyzing(true);
    try {
      await analyzeEvidence(selectedEvidence.id);
      loadDetections();
    } catch (err: any) {
      alert(`Analysis failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleForensics = async () => {
    if (!selectedEvidence) return;
    setAnalyzing(true);
    try {
      const findings = await analyzeForensics(selectedEvidence.id);
      setForensicFindings(findings);
    } catch (err: any) {
      alert(`Forensics failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRecovery = async () => {
    if (!selectedEvidence) return;
    setAnalyzing(true);
    try {
      const segments = await runRecovery(selectedEvidence.id);
      setRecoveredSegments(segments);
    } catch (err: any) {
      alert(`Recovery failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'objects', label: 'Objects' },
    { id: 'people', label: 'People' },
    { id: 'vehicles', label: 'Vehicles' },
    { id: 'plates', label: 'Plates' },
    { id: 'faces', label: 'Faces' },
    { id: 'cross_camera', label: 'Cross-Camera' },
    { id: 'anomalies', label: 'Anomalies' },
    { id: 'recovery', label: 'Recovery' },
  ];

  return (
    <div className="h-full flex flex-col space-y-4">
      {/* Search Bar & Top Controls */}
      <div className="flex items-center space-x-4 bg-slate-900 border border-slate-800 p-4 rounded-lg">
        <select 
          className="bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-sm"
          value={selectedCase}
          onChange={e => setSelectedCase(e.target.value)}
        >
          <option value="">Select Case...</option>
          {cases.map(c => <option key={c.id} value={c.id}>{c.case_number}</option>)}
        </select>

        <select 
          className="bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-sm flex-1 max-w-sm"
          value={selectedEvidence?.id || ''}
          onChange={e => setSelectedEvidence(evidenceList.find(ev => ev.id === e.target.value) || null)}
          disabled={!selectedCase}
        >
          <option value="">Select Evidence...</option>
          {evidenceList.map(ev => <option key={ev.id} value={ev.id}>{ev.original_filename}</option>)}
        </select>
        
        <div className="flex-1 max-w-md relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search people, vehicles, plates, track IDs..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-md pl-9 pr-4 py-1.5 text-sm focus:outline-none focus:border-indigo-500"
            />
        </div>

        <button 
          onClick={handleAnalyze}
          disabled={!selectedEvidence || analyzing}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white px-4 py-1.5 rounded-md text-sm font-medium flex items-center transition-colors ml-auto"
        >
          {analyzing ? 'Analyzing...' : <><ScanSearch className="w-4 h-4 mr-2" /> Run AI Analysis</>}
        </button>
      </div>

      {!selectedEvidence ? (
        <div className="flex-1 border-2 border-dashed border-slate-800 rounded-lg flex items-center justify-center text-slate-500">
          Select a case and evidence to begin investigation
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Main Content Area */}
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 overflow-hidden mb-4">
            {/* Video Area */}
            <div className="lg:col-span-3 bg-black border border-slate-800 rounded-lg flex flex-col relative overflow-hidden">
                <div className="absolute top-4 left-4 bg-black/60 px-3 py-1 rounded text-xs font-mono backdrop-blur-sm z-10 flex items-center">
                    <span className="w-2 h-2 rounded-full bg-red-500 mr-2 animate-pulse"></span>
                    CAM-01
                </div>
                
                <div className="flex-1 flex items-center justify-center bg-slate-900 relative">
                    <video 
                    ref={videoRef}
                    className="w-full h-full object-contain"
                    controls
                    poster="/placeholder.png"
                    crossOrigin="anonymous"
                    >
                    <source src={`${API_BASE_URL}/evidence/${selectedEvidence.id}/stream`} type="video/mp4" />
                    Your browser does not support the video tag.
                    </video>
                </div>

                <div className="bg-slate-900 border-t border-slate-800 p-3 flex items-center justify-between">
                    <div className="flex items-center space-x-3 text-slate-300">
                    <button className="hover:text-white"><Play className="w-5 h-5" /></button>
                    <button className="hover:text-white"><Pause className="w-5 h-5" /></button>
                    <button className="hover:text-white"><FastForward className="w-5 h-5" /></button>
                    <span className="text-xs font-mono">00:00:00 / {formatTime(selectedEvidence.duration || 0)}</span>
                    </div>
                    <button className="text-slate-300 hover:text-white"><Maximize2 className="w-5 h-5" /></button>
                </div>
            </div>

            {/* AI Findings Tabs & Panel */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg flex flex-col overflow-hidden">
              <div className="flex border-b border-slate-800 overflow-x-auto custom-scrollbar bg-slate-900/50">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                            activeTab === tab.id 
                            ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10' 
                            : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                        }`}
                    >
                        {tab.label}
                    </button>
                ))}
              </div>
              
              <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
                {loading ? (
                  <div className="text-center p-4 text-slate-500 text-sm">Loading findings...</div>
                ) : activeTab === 'anomalies' ? (
                  <>
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs text-slate-400 uppercase tracking-wider font-medium">Video Forensics</span>
                      <button onClick={handleForensics} disabled={analyzing} className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1 text-xs rounded border border-slate-700 transition-colors flex items-center">
                        <FileSearch className="w-3 h-3 mr-1" /> Run Forensics
                      </button>
                    </div>
                    {forensicFindings.length === 0 ? (
                      <div className="flex flex-col items-center justify-center p-8 text-slate-500 text-sm text-center">
                        <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
                        <p>No forensic anomalies detected.</p>
                      </div>
                    ) : (
                      forensicFindings.map(f => (
                        <div key={f.id} className="bg-slate-950 border border-slate-800 p-3 rounded hover:border-slate-600 transition-colors shadow-sm">
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center">
                              <span className={`w-2 h-2 rounded-full mr-2 ${f.severity === 'HIGH' ? 'bg-red-500' : f.severity === 'MEDIUM' ? 'bg-amber-500' : 'bg-blue-500'}`}></span>
                              <span className="font-medium capitalize text-sm">{f.type.replace(/_/g, ' ')}</span>
                            </div>
                            <span className="text-xs font-mono text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded">
                              {f.timestamp_start !== undefined ? formatTime(f.timestamp_start) : 'N/A'}
                            </span>
                          </div>
                          <div className="text-xs text-slate-400 mt-1 mb-2">{f.description}</div>
                          <div className="flex justify-between text-[10px] text-slate-500 bg-slate-900/40 p-1.5 rounded border border-slate-800/50">
                            <span>Method: {f.method}</span>
                            <span>Severity: {f.severity}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </>
                ) : activeTab === 'recovery' ? (
                  <>
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs text-slate-400 uppercase tracking-wider font-medium">Recovery Engine</span>
                      <button onClick={handleRecovery} disabled={analyzing} className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1 text-xs rounded border border-slate-700 transition-colors flex items-center">
                        <HardDrive className="w-3 h-3 mr-1" /> Run Recovery
                      </button>
                    </div>
                    {recoveredSegments.length === 0 ? (
                      <div className="flex flex-col items-center justify-center p-8 text-slate-500 text-sm text-center">
                        <HardDrive className="w-8 h-8 mb-2 opacity-50" />
                        <p>No recovered artifacts found.</p>
                      </div>
                    ) : (
                      recoveredSegments.map(s => (
                        <div key={s.id} className="bg-slate-950 border border-slate-800 p-3 rounded hover:border-slate-600 transition-colors shadow-sm">
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center">
                              <span className={`w-2 h-2 rounded-full mr-2 ${s.validation_status === 'VALIDATED' ? 'bg-emerald-500' : s.validation_status === 'PARTIAL' ? 'bg-amber-500' : s.validation_status === 'CORRUPTED' ? 'bg-red-500' : 'bg-slate-500'}`}></span>
                              <span className="font-medium capitalize text-sm">Recovered Segment</span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-500 bg-slate-900 px-1 rounded">{s.validation_status}</span>
                          </div>
                          <div className="flex flex-col space-y-1 text-[10px] mt-2 bg-slate-900/40 p-2 rounded border border-slate-800/50 text-slate-400">
                            <div className="flex justify-between"><span>Method:</span><span className="font-mono">{s.recovery_method}</span></div>
                            <div className="flex justify-between"><span>SHA-256:</span><span className="font-mono truncate max-w-[120px]" title={s.sha256}>{s.sha256.substring(0, 16)}...</span></div>
                            <div className="flex justify-between"><span>Size:</span><span>{s.size ? (s.size / 1024).toFixed(1) + ' KB' : 'Unknown'}</span></div>
                          </div>
                        </div>
                      ))
                    )}
                  </>
                ) : activeTab === 'cross_camera' ? (
                  <div className="flex flex-col items-center justify-center p-8 text-slate-500 text-sm h-full text-center">
                    <Cpu className="w-8 h-8 mb-2 opacity-50 text-amber-500" />
                    <h4 className="font-medium text-slate-300 mb-1 uppercase tracking-wider">Cross-Camera Re-ID</h4>
                    <p className="text-amber-500 font-bold mb-2">UNAVAILABLE</p>
                    <p className="text-xs">OSNet/Re-ID model not installed</p>
                  </div>
                ) : detections.length === 0 ? (
                  <div className="flex flex-col items-center justify-center p-8 text-slate-500 text-sm h-full text-center">
                    <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
                    <p>No findings for this category.</p>
                  </div>
                ) : (
                  detections.map(d => (
                    <div key={d.id} className="bg-slate-950 border border-slate-800 p-3 rounded hover:border-slate-600 transition-colors cursor-pointer group shadow-sm">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center">
                          <span className={`w-2 h-2 rounded-full mr-2 ${
                            d.detection_type === 'face' ? 'bg-indigo-500' : 
                            d.detection_type === 'object' ? 'bg-emerald-500' : 
                            d.detection_type === 'plate' ? 'bg-sky-500' : 'bg-amber-500'
                          }`}></span>
                          <span className="font-medium capitalize text-sm">{d.label || d.detection_type}</span>
                        </div>
                        <span className="text-xs font-mono text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded">{formatTime(d.timestamp || 0)}</span>
                      </div>
                      
                      <div className="flex flex-col space-y-1 text-xs mt-2 bg-slate-900/40 p-2 rounded border border-slate-800/50">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Confidence:</span>
                          <span className="text-emerald-400 font-medium">{(d.confidence * 100).toFixed(1)}%</span>
                        </div>
                        {d.track_id && (
                          <div className="flex justify-between">
                            <span className="text-slate-500">Track ID:</span>
                            <span className="text-indigo-400 font-mono font-medium">#{d.track_id}</span>
                          </div>
                        )}
                        <div className="flex justify-between pt-1 border-t border-slate-800/50 mt-1">
                          <span className="text-slate-500">AI Provenance:</span>
                          <span className="text-slate-400 text-[10px]" title="Model Used for Inference">
                              {d.model_name || 'MODEL UNAVAILABLE'} {d.model_version ? `v${d.model_version}` : ''}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Timeline Section */}
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg h-32 flex flex-col shrink-0">
            <div className="text-xs text-slate-400 font-medium mb-2 uppercase tracking-wider flex justify-between">
              <span>Forensic Timeline</span>
              <span className="text-indigo-400">Scale: 1m</span>
            </div>
            <div className="flex-1 bg-slate-950 rounded border border-slate-800 relative overflow-hidden">
              {detections.map((d, i) => {
                const duration = selectedEvidence.duration || 100;
                const pos = ((d.timestamp || 0) / duration) * 100;
                const color = d.detection_type === 'face' ? 'bg-indigo-400' : 
                              d.detection_type === 'object' ? 'bg-emerald-400' : 
                              d.detection_type === 'plate' ? 'bg-sky-400' : 'bg-amber-400';
                
                return (
                  <div 
                    key={i} 
                    className={`absolute top-0 bottom-0 w-1 ${color} opacity-50 hover:opacity-100 cursor-pointer transition-opacity`}
                    style={{ left: `${Math.min(pos, 99)}%` }}
                    title={`${d.detection_type} at ${d.timestamp}s`}
                  ></div>
                );
              })}
              <div className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10" style={{ left: '10%' }}></div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
