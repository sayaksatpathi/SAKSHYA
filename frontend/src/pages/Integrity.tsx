import { useEffect, useState } from 'react';
import { getCases, type Case } from '../api/cases';
import { verifyChain, verifyMerkle, requestTrustSeal, verifyTrustSeal, simulateTamper, getEvidence, listCertificates, createCertificate, verifyCertificate, type ChainStatus, type MerkleStatus, type TrustVerification } from '../api/integrity';
import { ShieldCheck, CheckCircle2, AlertOctagon, Link2, GitMerge, FileKey2, RefreshCw, AlertTriangle } from 'lucide-react';

export default function Integrity() {
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>('');
  
  const [chainStatus, setChainStatus] = useState<ChainStatus | null>(null);
  const [merkleStatus, setMerkleStatus] = useState<MerkleStatus | null>(null);
  const [trustStatus, setTrustStatus] = useState<TrustVerification | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [tampering, setTampering] = useState(false);

  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [certificates, setCertificates] = useState<any[]>([]);
  const [certVerifications, setCertVerifications] = useState<Record<string, any>>({});

  useEffect(() => {
    getCases().then(setCases);
  }, []);

  const handleVerify = async () => {
    if (!selectedCase) return;
    setVerifying(true);
    setChainStatus(null);
    setMerkleStatus(null);
    setTrustStatus(null);
    
    try {
      const chain = await verifyChain(selectedCase);
      setChainStatus(chain);
      
      const merkle = await verifyMerkle(selectedCase);
      setMerkleStatus(merkle);
      
      const trust = await verifyTrustSeal(selectedCase);
      setTrustStatus(trust);

      // Load Evidence & Certificates
      const evs = await getEvidence(selectedCase);
      setEvidenceList(evs);
      
      const certs = await listCertificates(selectedCase);
      setCertificates(certs);
      setCertVerifications({});
    } catch (err: any) {
      if (err.status === 404) {
        // Trust seal not found, we can request one
      } else if (err.status === 503) {
        alert("TRUST AUTHORITY OFFLINE");
      } else {
        alert(`Verification failed: ${err.message}`);
      }
    } finally {
      setVerifying(false);
    }
  };

  const handleRequestSeal = async () => {
    if (!selectedCase) return;
    try {
      await requestTrustSeal(selectedCase);
      handleVerify();
    } catch (err: any) {
      if (err.status === 503) {
        alert("TRUST AUTHORITY OFFLINE");
      } else {
        alert(`Trust seal request failed: ${err.message}`);
      }
    }
  };

  const handleTamper = async () => {
    if (!selectedCase) return;
    if (!confirm('DEMO ONLY: This will corrupt the first evidence file associated with this case to demonstrate tamper detection. Are you sure?')) return;
    
    setTampering(true);
    try {
      await simulateTamper(selectedCase);
      alert('Evidence tampered! Run Verification to detect the breach.');
    } catch (err: any) {
      alert(`Tamper failed: ${err.message}`);
    } finally {
      setTampering(false);
    }
  };

  const handleGenerateDraft = async (evidence: any) => {
    try {
      await createCertificate(selectedCase, {
        evidence_id: evidence.id,
        electronic_record_identifier: `ER-${evidence.id.substring(0, 8).toUpperCase()}`,
        electronic_record_description: evidence.original_filename
      });
      // Refresh certs
      const certs = await listCertificates(selectedCase);
      setCertificates(certs);
    } catch (err: any) {
      alert(`Failed to generate draft: ${err.message}`);
    }
  };

  const handleVerifyCert = async (certId: string) => {
    try {
      const res = await verifyCertificate(certId);
      setCertVerifications(prev => ({ ...prev, [certId]: res }));
    } catch (err: any) {
      alert(`Failed to verify: ${err.message}`);
    }
  };


  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold flex items-center">
          <ShieldCheck className="w-6 h-6 mr-3 text-blue-400" />
          Integrity & Trust Center
        </h1>
        <div className="flex items-center space-x-3">
          <select 
            className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm"
            value={selectedCase}
            onChange={e => setSelectedCase(e.target.value)}
          >
            <option value="">Select Case to Verify...</option>
            {cases.map(c => <option key={c.id} value={c.id}>{c.case_number}</option>)}
          </select>
          <button 
            onClick={handleVerify}
            disabled={!selectedCase || verifying}
            className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white px-4 py-1.5 rounded-md text-sm font-medium flex items-center transition-colors"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${verifying ? 'animate-spin' : ''}`} />
            Run Verification
          </button>
          
          <button
            onClick={handleTamper}
            disabled={!selectedCase || tampering}
            className="bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 disabled:opacity-50 px-4 py-1.5 rounded-md text-sm font-medium flex items-center transition-colors ml-2"
          >
            <AlertTriangle className={`w-4 h-4 mr-2 ${tampering ? 'animate-pulse' : ''}`} />
            Simulate Tamper
          </button>
        </div>
      </div>

      {!selectedCase ? (
        <div className="text-center p-12 text-slate-500">
          Select a case above to view its cryptographic integrity state.
        </div>
      ) : (
        <div className="space-y-8 py-4">
          
          {/* Step 1: Chain of Custody */}
          <div className="flex items-start">
            <div className="flex flex-col items-center mr-6">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                chainStatus?.valid ? 'bg-emerald-500/20 text-emerald-400 border-2 border-emerald-500/50' : 
                chainStatus?.valid === false ? 'bg-red-500/20 text-red-400 border-2 border-red-500/50' :
                'bg-slate-800 text-slate-500'
              }`}>
                <Link2 className="w-5 h-5" />
              </div>
              <div className="w-0.5 h-full min-h-[4rem] bg-slate-800 my-2"></div>
            </div>
            <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-5">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-lg">Cryptographic Event Chain</h3>
                {chainStatus && (
                  chainStatus.valid ? (
                    <span className="bg-emerald-500/10 text-emerald-400 text-xs px-2 py-1 rounded font-medium flex items-center">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> CHAIN VALID
                    </span>
                  ) : (
                    <span className="bg-red-500/10 text-red-400 text-xs px-2 py-1 rounded font-medium flex items-center">
                      <AlertOctagon className="w-3 h-3 mr-1" /> INTEGRITY FAILURE
                    </span>
                  )
                )}
              </div>
              <p className="text-sm text-slate-400 mb-4">Verifies that no ledger events have been modified, deleted, or reordered since ingestion.</p>
              {chainStatus && chainStatus.valid && (
                <div className="bg-slate-950 p-3 rounded font-mono text-xs text-slate-500 overflow-x-auto">
                  <div className="text-slate-400 mb-1">Chain Head Hash:</div>
                  <div className="text-emerald-400">{chainStatus.chain_head}</div>
                  <div className="mt-2 text-slate-400">Events Verified: {chainStatus.verified_events}</div>
                </div>
              )}
            </div>
          </div>

          {/* Step 2: Merkle Tree */}
          <div className="flex items-start">
            <div className="flex flex-col items-center mr-6">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                merkleStatus?.valid ? 'bg-emerald-500/20 text-emerald-400 border-2 border-emerald-500/50' : 
                merkleStatus?.valid === false ? 'bg-red-500/20 text-red-400 border-2 border-red-500/50' :
                'bg-slate-800 text-slate-500'
              }`}>
                <GitMerge className="w-5 h-5" />
              </div>
              <div className="w-0.5 h-full min-h-[4rem] bg-slate-800 my-2"></div>
            </div>
            <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-5">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-lg">Evidence Merkle Root</h3>
                {merkleStatus && (
                  merkleStatus.valid ? (
                    <span className="bg-emerald-500/10 text-emerald-400 text-xs px-2 py-1 rounded font-medium flex items-center">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> MERKLE VALID
                    </span>
                  ) : (
                    <span className="bg-red-500/10 text-red-400 text-xs px-2 py-1 rounded font-medium flex items-center">
                      <AlertOctagon className="w-3 h-3 mr-1" /> INTEGRITY FAILURE
                    </span>
                  )
                )}
              </div>
              <p className="text-sm text-slate-400 mb-4">Cryptographically anchors all evidence SHA-256 hashes into a single root.</p>
              {merkleStatus && merkleStatus.valid && (
                <div className="bg-slate-950 p-3 rounded font-mono text-xs text-slate-500 overflow-x-auto">
                  <div className="text-slate-400 mb-1">Merkle Root:</div>
                  <div className="text-emerald-400">{merkleStatus.root_hash}</div>
                  <div className="mt-2 text-slate-400">Leaves: {merkleStatus.leaf_count}</div>
                </div>
              )}
            </div>
          </div>

          {/* Step 3: Trust Signature */}
          <div className="flex items-start">
            <div className="flex flex-col items-center mr-6">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                trustStatus?.valid ? 'bg-blue-500/20 text-blue-400 border-2 border-blue-500/50' : 
                trustStatus?.valid === false ? 'bg-red-500/20 text-red-400 border-2 border-red-500/50' :
                'bg-slate-800 text-slate-500'
              }`}>
                <FileKey2 className="w-5 h-5" />
              </div>
            </div>
            <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-5">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-lg">Independent Trust Seal</h3>
                {trustStatus ? (
                  trustStatus.valid ? (
                    <span className="bg-blue-500/10 text-blue-400 text-xs px-2 py-1 rounded font-medium flex items-center">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> SIGNATURE VERIFIED
                    </span>
                  ) : (
                    <span className="bg-red-500/10 text-red-400 text-xs px-2 py-1 rounded font-medium flex items-center">
                      <AlertOctagon className="w-3 h-3 mr-1" /> VERIFICATION FAILED
                    </span>
                  )
                ) : null}
              </div>
              <p className="text-sm text-slate-400 mb-4">Independent cryptographic receipt proving the chain existed at a specific time.</p>
              
              {!trustStatus && chainStatus?.valid ? (
                <button 
                  onClick={handleRequestSeal}
                  className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
                >
                  Request Trust Seal
                </button>
              ) : trustStatus && trustStatus.valid && trustStatus.receipt && (
                <div className="bg-slate-950 p-4 rounded border border-slate-800 text-xs text-slate-400">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="block text-slate-500 uppercase tracking-wider mb-1">Authority</span>
                      <span className="font-medium text-slate-200">{trustStatus.receipt.authority_id}</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 uppercase tracking-wider mb-1">Algorithm</span>
                      <span className="font-medium text-slate-200">{trustStatus.receipt.algorithm}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="block text-slate-500 uppercase tracking-wider mb-1">Timestamp</span>
                      <span className="font-mono text-slate-300">{trustStatus.receipt.timestamp}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="block text-slate-500 uppercase tracking-wider mb-1">Signature</span>
                      <span className="font-mono text-blue-400 break-all">{trustStatus.receipt.signature}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Step 4: BSA Section 63(4) Certificate */}
          <div className="flex items-start">
            <div className="flex flex-col items-center mr-6">
              <div className="w-10 h-10 rounded-full flex items-center justify-center bg-slate-800 text-slate-500">
                <FileKey2 className="w-5 h-5" />
              </div>
            </div>
            <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-5">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-lg">BSA Section 63(4) Certificate Draft</h3>
                <span className="bg-amber-500/10 text-amber-400 text-xs px-2 py-1 rounded font-medium flex items-center">
                  <AlertTriangle className="w-3 h-3 mr-1" /> DRAFT REVIEW REQUIRED
                </span>
              </div>
              <p className="text-sm text-slate-400 mb-4">Generates a structured electronic-record certificate draft binding evidence, AI analysis, Merkle root, and Trust seal.</p>
              
              <div className="space-y-4">
                {evidenceList.map(ev => {
                  const cert = certificates.find(c => c.evidence_id === ev.id);
                  const ver = cert ? certVerifications[cert.certificate_id] : null;
                  
                  return (
                    <div key={ev.id} className="bg-slate-950 p-4 rounded border border-slate-800">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h4 className="font-medium text-slate-200">{ev.original_filename}</h4>
                          <span className="text-xs text-slate-500 font-mono">SHA256: {ev.sha256.substring(0,16)}...</span>
                        </div>
                        
                        {!cert ? (
                          <button
                            onClick={() => handleGenerateDraft(ev)}
                            className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded text-xs font-medium"
                          >
                            Generate Draft
                          </button>
                        ) : (
                          <div className="flex items-center space-x-2">
                            <span className="bg-amber-500/10 text-amber-400 text-xs px-2 py-1 rounded">
                              {cert.certificate_status}
                            </span>
                            <button
                              onClick={() => handleVerifyCert(cert.certificate_id)}
                              className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded text-xs font-medium"
                            >
                              Verify
                            </button>
                          </div>
                        )}
                      </div>
                      
                      {cert && (
                        <div className="mt-3 text-xs text-slate-400 space-y-1">
                          <div><span className="text-slate-500">ID:</span> {cert.certificate_id}</div>
                          <div><span className="text-slate-500">Content Hash:</span> <span className="font-mono">{cert.certificate_content_hash?.substring(0, 32)}...</span></div>
                          
                          {ver && (
                            <div className={`mt-2 p-2 rounded ${ver.overall_integrity_status === 'INVALID' ? 'bg-red-900/30 text-red-300 border border-red-800' : 'bg-emerald-900/30 text-emerald-300 border border-emerald-800'}`}>
                              <div className="font-medium mb-1">Verification: {ver.overall_integrity_status}</div>
                              <ul className="list-disc pl-4 space-y-0.5 opacity-80">
                                <li>Content Hash: {ver.certificate_content_hash_valid ? 'Valid' : 'Invalid'}</li>
                                <li>Evidence Hash: {ver.evidence_hash_matches ? 'Matches' : 'Mismatch'}</li>
                                <li>Merkle Root: {ver.merkle_root_matches ? 'Matches' : 'Mismatch'}</li>
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              
              <div className="text-xs text-slate-500 mt-4 border-t border-slate-800 pt-3">
                <i>Note: Generate the certificate PDF from the "Reports" tab. SAKSHYA does not determine legal admissibility. The certificate must be reviewed and signed by a responsible person.</i>
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
