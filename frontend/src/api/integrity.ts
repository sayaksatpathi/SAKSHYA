import { fetchApi } from './client';

export interface ChainStatus {
  valid: boolean;
  chain_head: string;
  error?: string;
  verified_events: number;
}

export interface MerkleStatus {
  valid: boolean;
  root_hash: string;
  leaf_count: number;
  error?: string;
}

export interface TrustReceipt {
  id: string;
  chain_head: string;
  merkle_root?: string;
  signature: string;
  algorithm: string;
  authority_id: string;
  timestamp: string;
}

export interface TrustVerification {
  valid: boolean;
  receipt?: TrustReceipt;
  error?: string;
}

export const verifyChain = (caseId: string) => fetchApi<ChainStatus>(`/cases/${caseId}/verify-chain`, { method: 'POST' });
export const verifyMerkle = (caseId: string) => fetchApi<MerkleStatus>(`/cases/${caseId}/verify-merkle`, { method: 'POST' });
export const requestTrustSeal = (caseId: string) => fetchApi<TrustReceipt>(`/cases/${caseId}/trust-sign`, { method: 'POST' });
export const verifyTrustSeal = (caseId: string) => fetchApi<TrustVerification>(`/cases/${caseId}/trust-verify`, { method: 'POST' });
export const simulateTamper = (caseId: string) => fetchApi<{message: string}>(`/cases/${caseId}/simulate-tamper`, { method: 'POST' });

export interface CertificateVerifyResponse {
  certificate_exists: boolean;
  certificate_content_hash_valid: boolean;
  evidence_hash_matches: boolean;
  analysis_hash_matches: boolean;
  merkle_root_matches: boolean;
  trust_reference_valid: boolean;
  report_hash_matches: boolean;
  signature_status: string;
  overall_integrity_status: string;
}

export const createCertificate = (caseId: string, payload: any) => fetchApi<any>(`/cases/${caseId}/certificates`, { method: 'POST', body: JSON.stringify(payload) });
export const listCertificates = (caseId: string) => fetchApi<any[]>(`/cases/${caseId}/certificates`);
export const getCertificate = (certId: string) => fetchApi<any>(`/certificates/${certId}`);
export const verifyCertificate = (certId: string) => fetchApi<CertificateVerifyResponse>(`/certificates/${certId}/verify`);
export const getEvidence = (caseId: string) => fetchApi<any[]>(`/cases/${caseId}/evidence`);
