/**
 * SAKSHYA — Forensic Evidence Platform
 * Frontend Application Logic
 *
 * Communicates with the SAKSHYA backend API.
 */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : '';

// =============================================================================
// State
// =============================================================================
let currentPage = 'dashboard';
let currentCaseId = null;
let allCases = [];
let timelineFilter = 'all';

// =============================================================================
// Navigation
// =============================================================================

function navigateTo(page) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    // Show target page
    const target = document.getElementById(`page-${page}`);
    if (target) target.classList.remove('hidden');

    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navItem = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (navItem) navItem.classList.add('active');

    // Update title
    const titles = {
        dashboard: 'Dashboard', cases: 'Case Management', evidence: 'Evidence',
        ai: 'AI Investigation', timeline: 'Timeline', integrity: 'Chain & Merkle',
        trust: 'Trust Seal', reports: 'Reports',
    };
    document.getElementById('page-title').textContent = titles[page] || page;

    currentPage = page;
    loadPageData(page);
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// =============================================================================
// API Helpers
// =============================================================================

async function api(endpoint, options = {}) {
    try {
        const url = `${API_BASE}${endpoint}`;
        const resp = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        // Handle PDF responses
        if (resp.headers.get('content-type')?.includes('application/pdf')) {
            return await resp.blob();
        }
        return await resp.json();
    } catch (e) {
        if (e.message.includes('fetch')) {
            console.warn('API unavailable:', endpoint);
            return null;
        }
        throw e;
    }
}

async function apiUpload(endpoint, formData) {
    const url = `${API_BASE}${endpoint}`;
    const resp = await fetch(url, { method: 'POST', body: formData });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return await resp.json();
}

// =============================================================================
// Toast Notifications
// =============================================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// =============================================================================
// Modals
// =============================================================================

function showModal(id) { document.getElementById(id).classList.remove('hidden'); }
function hideModal(id) { document.getElementById(id).classList.add('hidden'); }
function showCreateCase() { showModal('modal-create-case'); }
function showUploadEvidence() { showModal('modal-upload-evidence'); }

// =============================================================================
// Page Data Loaders
// =============================================================================

async function loadPageData(page) {
    switch (page) {
        case 'dashboard': await loadDashboard(); break;
        case 'cases': await loadCases(); break;
        case 'evidence': await populateCaseDropdowns(); break;
        case 'ai': await populateCaseDropdowns(); break;
        case 'timeline': await populateCaseDropdowns(); break;
        case 'integrity': await populateCaseDropdowns(); break;
        case 'trust': await populateCaseDropdowns(); break;
        case 'reports': await populateCaseDropdowns(); break;
    }
}

// =============================================================================
// Dashboard
// =============================================================================

async function loadDashboard() {
    // Health check
    const health = await api('/api/health');
    if (health) {
        updateHealthUI(health);
    } else {
        document.getElementById('health-api').textContent = 'Offline';
        document.getElementById('health-api').className = 'badge badge-error';
    }

    // Load cases
    const casesData = await api('/api/cases');
    if (casesData) {
        allCases = casesData.cases;
        document.getElementById('stat-cases-value').textContent = casesData.total;

        // Count evidence and detections
        let totalEvidence = 0;
        let totalDetections = 0;
        let totalChainEvents = 0;

        for (const c of casesData.cases) {
            totalEvidence += c.evidence_count || 0;
        }

        document.getElementById('stat-evidence-value').textContent = totalEvidence;

        // Load chain events count for the first case
        if (casesData.cases.length > 0) {
            const chainHead = await api(`/api/cases/${casesData.cases[0].id}/chain-head`);
            if (chainHead) {
                totalChainEvents = chainHead.event_count || 0;
            }

            // Load AI detections for first case
            const detections = await api(`/api/cases/${casesData.cases[0].id}/detections`);
            if (detections) {
                totalDetections = detections.total || 0;
            }
        }

        document.getElementById('stat-detections-value').textContent = totalDetections;
        document.getElementById('stat-integrity-value').textContent = totalChainEvents;

        // Recent cases
        renderRecentCases(casesData.cases.slice(0, 5));
    }
}

function updateHealthUI(health) {
    const setHealth = (id, status) => {
        const el = document.getElementById(id);
        if (status === true || status === 'ok' || status === 'operational') {
            el.textContent = 'Online';
            el.className = 'badge badge-success';
        } else if (status === false || status === 'unavailable') {
            el.textContent = 'Unavailable';
            el.className = 'badge badge-warning';
        } else {
            el.textContent = status;
            el.className = 'badge';
        }
    };

    setHealth('health-api', 'ok');
    setHealth('health-db', health.database);
    setHealth('health-trust', health.trust_service);

    if (health.models_available) {
        setHealth('health-face', health.models_available.face_detector);
        setHealth('health-object', health.models_available.object_detector);
    }

    // Update trust badge
    const trustBadge = document.getElementById('trust-badge');
    if (health.trust_service === 'operational') {
        trustBadge.classList.add('online');
        trustBadge.classList.remove('offline');
    } else {
        trustBadge.classList.add('offline');
        trustBadge.classList.remove('online');
    }

    // System status
    const statusDot = document.querySelector('.status-dot');
    statusDot.classList.add('online');
}

function renderRecentCases(cases) {
    const container = document.getElementById('recent-cases');
    if (!cases.length) {
        container.innerHTML = '<div class="empty-state">No cases yet. Create your first case.</div>';
        return;
    }

    container.innerHTML = cases.map(c => `
        <div class="case-card" onclick="selectCase('${c.id}')">
            <div class="case-card-number">${escapeHtml(c.case_number)}</div>
            <div class="case-card-title">${escapeHtml(c.title)}</div>
            <div class="case-card-meta">
                <span>◈ ${c.evidence_count || 0} evidence</span>
                <span>◫ ${escapeHtml(c.status)}</span>
                <span>${formatDate(c.created_at)}</span>
            </div>
        </div>
    `).join('');
}

// =============================================================================
// Cases
// =============================================================================

async function loadCases() {
    const data = await api('/api/cases');
    if (!data) return;
    allCases = data.cases;
    renderCasesList(data.cases);
}

function renderCasesList(cases) {
    const container = document.getElementById('cases-list');
    if (!cases.length) {
        container.innerHTML = '<div class="empty-state">No cases yet. Click "+ New Case" to create one.</div>';
        return;
    }

    container.innerHTML = cases.map(c => `
        <div class="case-card" onclick="selectCase('${c.id}')">
            <div class="case-card-number">${escapeHtml(c.case_number)}</div>
            <div class="case-card-title">${escapeHtml(c.title)}</div>
            <div class="case-card-desc">${escapeHtml(c.description || 'No description')}</div>
            <div class="case-card-meta">
                <span>◈ ${c.evidence_count || 0} evidence</span>
                <span class="badge badge-info">${escapeHtml(c.status)}</span>
                <span>👤 ${escapeHtml(c.investigator)}</span>
                <span>${formatDate(c.created_at)}</span>
            </div>
        </div>
    `).join('');
}

async function createCase(e) {
    e.preventDefault();
    const payload = {
        case_number: document.getElementById('case-number').value,
        title: document.getElementById('case-title').value,
        description: document.getElementById('case-description').value,
        investigator: document.getElementById('case-investigator').value,
    };

    try {
        const result = await api('/api/cases', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        if (result) {
            showToast(`Case ${result.case_number} created successfully`, 'success');
            hideModal('modal-create-case');
            document.querySelector('#modal-create-case form').reset();
            await loadCases();
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function selectCase(caseId) {
    currentCaseId = caseId;
    navigateTo('evidence');
    // Set the evidence case dropdown
    setTimeout(() => {
        const select = document.getElementById('evidence-case-select');
        if (select) {
            select.value = caseId;
            loadCaseEvidence();
        }
    }, 100);
}

// =============================================================================
// Evidence
// =============================================================================

async function populateCaseDropdowns() {
    if (!allCases.length) {
        const data = await api('/api/cases');
        if (data) allCases = data.cases;
    }

    const selects = [
        'evidence-case-select', 'ai-case-select', 'timeline-case-select',
        'integrity-case-select', 'trust-case-select', 'report-case-select',
    ];

    for (const id of selects) {
        const select = document.getElementById(id);
        if (!select) continue;
        const currentValue = select.value;
        select.innerHTML = '<option value="">Select a case...</option>';
        for (const c of allCases) {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = `${c.case_number} — ${c.title}`;
            select.appendChild(opt);
        }
        if (currentValue) select.value = currentValue;
    }
}

async function loadCaseEvidence() {
    const caseId = document.getElementById('evidence-case-select').value;
    const uploadBtn = document.getElementById('btn-upload-evidence');
    const container = document.getElementById('evidence-list');

    if (!caseId) {
        uploadBtn.disabled = true;
        container.innerHTML = '<div class="empty-state">Select a case to view evidence.</div>';
        return;
    }

    uploadBtn.disabled = false;
    currentCaseId = caseId;

    const data = await api(`/api/cases/${caseId}/evidence`);
    if (!data || !data.evidence.length) {
        container.innerHTML = '<div class="empty-state">No evidence in this case yet. Upload evidence to begin.</div>';
        return;
    }

    container.innerHTML = data.evidence.map(ev => `
        <div class="evidence-card">
            <div class="evidence-header">
                <div class="evidence-name">${escapeHtml(ev.original_filename)}</div>
                <div class="evidence-type">${escapeHtml(ev.evidence_type)}</div>
            </div>
            <div class="evidence-meta">
                <div class="evidence-meta-item">
                    <span class="meta-label">Vendor</span>
                    <span class="meta-value">${escapeHtml(ev.source_vendor || 'Unknown')}</span>
                </div>
                <div class="evidence-meta-item">
                    <span class="meta-label">Size</span>
                    <span class="meta-value">${formatBytes(ev.size)}</span>
                </div>
                <div class="evidence-meta-item">
                    <span class="meta-label">Codec</span>
                    <span class="meta-value">${ev.codec || 'N/A'}</span>
                </div>
                <div class="evidence-meta-item">
                    <span class="meta-label">Resolution</span>
                    <span class="meta-value">${ev.resolution || 'N/A'}</span>
                </div>
                <div class="evidence-meta-item">
                    <span class="meta-label">Duration</span>
                    <span class="meta-value">${ev.duration ? formatDuration(ev.duration) : 'N/A'}</span>
                </div>
                <div class="evidence-meta-item">
                    <span class="meta-label">Status</span>
                    <span class="meta-value">${escapeHtml(ev.status)}</span>
                </div>
            </div>
            <div class="evidence-hash">SHA-256: ${ev.sha256}</div>
            <div class="evidence-actions">
                <button class="btn btn-sm" onclick="verifyEvidence('${ev.id}')">⟳ Verify Hash</button>
                <button class="btn btn-sm" onclick="recoverEvidence('${ev.id}')">⟳ Recover</button>
                <button class="btn btn-sm" onclick="analyzeEvidence('${ev.id}')">◎ Analyze AI</button>
                <button class="btn btn-sm" onclick="viewSegments('${ev.id}')">◈ Segments</button>
            </div>
        </div>
    `).join('');
}

async function uploadEvidence(e) {
    e.preventDefault();
    const caseId = document.getElementById('evidence-case-select').value;
    if (!caseId) {
        showToast('Select a case first', 'warning');
        return;
    }

    const fileInput = document.getElementById('evidence-file');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('source_device', document.getElementById('evidence-device').value);
    formData.append('source_vendor', document.getElementById('evidence-vendor').value);
    formData.append('evidence_type', 'video');

    const btn = document.getElementById('btn-upload-submit');
    btn.disabled = true;
    btn.textContent = 'Uploading & Hashing...';

    try {
        const result = await apiUpload(`/api/cases/${caseId}/evidence`, formData);
        if (result) {
            showToast(`Evidence uploaded. SHA-256: ${result.sha256.substring(0, 16)}...`, 'success');
            hideModal('modal-upload-evidence');
            await loadCaseEvidence();
        }
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Upload & Hash';
    }
}

async function verifyEvidence(evidenceId) {
    try {
        const result = await api(`/api/evidence/${evidenceId}/verify`);
        if (result) {
            if (result.valid) {
                showToast('HASH VERIFIED — Evidence integrity confirmed', 'success');
            } else {
                showToast(`INTEGRITY FAILURE: ${result.detail}`, 'error');
            }
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function recoverEvidence(evidenceId) {
    showToast('Starting recovery simulation...', 'info');
    try {
        const result = await api(`/api/evidence/${evidenceId}/recover?use_demo=true`, { method: 'POST' });
        if (result && result.length > 0) {
            showToast(`Recovery complete: ${result.length} segments found`, 'success');
            await loadCaseEvidence();
        } else {
            showToast('No segments recovered', 'warning');
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function analyzeEvidence(evidenceId) {
    showToast('Running AI analysis...', 'info');
    try {
        const result = await api(`/api/evidence/${evidenceId}/analyze?use_demo=true`, { method: 'POST' });
        if (result) {
            showToast(`AI analysis complete: ${result.total} detections found`, 'success');
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// =============================================================================
// AI Investigation
// =============================================================================

async function loadAICase() {
    const caseId = document.getElementById('ai-case-select').value;
    const container = document.getElementById('ai-content');

    if (!caseId) {
        container.innerHTML = '<div class="empty-state">Select a case to view AI analysis results.</div>';
        return;
    }

    const data = await api(`/api/cases/${caseId}/detections`);
    if (!data || !data.results.length) {
        container.innerHTML = `
            <div class="empty-state">
                No AI detections found for this case.<br>
                <button class="btn btn-primary" style="margin-top:12px" onclick="runCaseAnalysis('${caseId}')">
                    Run Demo AI Analysis
                </button>
            </div>
        `;
        return;
    }

    // Group by type
    const grouped = {};
    for (const r of data.results) {
        if (!grouped[r.detection_type]) grouped[r.detection_type] = [];
        grouped[r.detection_type].push(r);
    }

    let html = `<div class="card"><div class="card-header"><h3>AI Detection Summary</h3>
        <span class="badge badge-info">${data.total} total detections</span></div>
        <div class="card-body">
        <p style="font-size:11px;color:var(--text-muted);margin-bottom:12px">
            ⚠ AI results are investigative aids, not definitive identifications.
            Similarity scores do not prove identity.
        </p>`;

    for (const [type, results] of Object.entries(grouped)) {
        html += `<h4 style="margin:16px 0 8px;font-size:13px;color:var(--accent-cyan);text-transform:uppercase">
            ${escapeHtml(type)} (${results.length})</h4>`;

        for (const r of results.slice(0, 20)) {
            html += `
            <div class="ai-detection-card ${type}">
                <div class="ai-detection-type">${escapeHtml(type)}</div>
                <div class="ai-detection-info">
                    <div class="ai-detection-label">${escapeHtml(r.label || type)}</div>
                    <div class="ai-detection-meta">
                        Frame ${r.frame_number || 'N/A'} · ${r.timestamp ? formatTime(r.timestamp) : 'N/A'}
                        ${r.track_id ? ` · Track ${r.track_id}` : ''}
                        · ${r.model_name || 'Unknown model'}
                    </div>
                </div>
                <div class="ai-confidence" style="color:${r.confidence >= 0.8 ? 'var(--accent-green)' : 'var(--accent-amber)'}">
                    ${(r.confidence * 100).toFixed(0)}%
                </div>
            </div>`;
        }
    }

    html += '</div></div>';
    container.innerHTML = html;
}

async function runCaseAnalysis(caseId) {
    // Get evidence for this case and run analysis on each
    const evData = await api(`/api/cases/${caseId}/evidence`);
    if (!evData || !evData.evidence.length) {
        showToast('No evidence in this case', 'warning');
        return;
    }

    for (const ev of evData.evidence) {
        await api(`/api/evidence/${ev.id}/analyze?use_demo=true`, { method: 'POST' });
    }
    showToast('Demo AI analysis complete', 'success');
    await loadAICase();
}

// =============================================================================
// Timeline
// =============================================================================

async function loadTimeline() {
    const caseId = document.getElementById('timeline-case-select').value;
    const container = document.getElementById('timeline-content');

    if (!caseId) {
        container.innerHTML = '<div class="empty-state">Select a case to view timeline.</div>';
        return;
    }

    // Get all evidence for the case
    const evData = await api(`/api/cases/${caseId}/evidence`);
    if (!evData) return;

    let allEvents = [];

    for (const ev of evData.evidence) {
        const timeline = await api(`/api/evidence/${ev.id}/timeline`);
        if (timeline && timeline.events) {
            for (const event of timeline.events) {
                event.camera = ev.source_device || ev.original_filename;
                allEvents.push(event);
            }
        }
    }

    // Add chain events
    const chain = await api(`/api/cases/${caseId}/chain`);
    if (chain) {
        for (const ev of chain) {
            allEvents.push({
                timestamp: new Date(ev.timestamp).getTime() / 1000,
                event_type: 'chain',
                label: ev.event_type,
                confidence: null,
                camera: null,
                meta_data: { actor: ev.actor, hash: ev.event_hash },
            });
        }
    }

    // Sort by timestamp
    allEvents.sort((a, b) => a.timestamp - b.timestamp);

    renderTimeline(allEvents);
}

function renderTimeline(events) {
    const container = document.getElementById('timeline-content');

    const filtered = timelineFilter === 'all'
        ? events
        : events.filter(e => e.event_type === timelineFilter);

    if (!filtered.length) {
        container.innerHTML = '<div class="empty-state">No timeline events found.</div>';
        return;
    }

    container.innerHTML = filtered.map(ev => `
        <div class="timeline-event">
            <div class="timeline-dot ${ev.event_type}"></div>
            <div class="timeline-time">${formatTime(ev.timestamp)}</div>
            <div class="timeline-info">
                <div class="timeline-label">${escapeHtml(ev.label)}</div>
                <div class="timeline-detail">
                    ${ev.camera ? `Camera: ${escapeHtml(ev.camera)}` : ''}
                    ${ev.confidence ? ` · Confidence: ${(ev.confidence * 100).toFixed(0)}%` : ''}
                    ${ev.meta_data?.actor ? ` · Actor: ${escapeHtml(ev.meta_data.actor)}` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function filterTimeline(filter, btn) {
    timelineFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadTimeline();
}

// =============================================================================
// Integrity
// =============================================================================

async function loadIntegrity() {
    const caseId = document.getElementById('integrity-case-select').value;
    const container = document.getElementById('integrity-content');

    if (!caseId) {
        container.innerHTML = '<div class="empty-state">Select a case to view integrity verification.</div>';
        return;
    }

    // Get chain data
    const chainHead = await api(`/api/cases/${caseId}/chain-head`);
    const chain = await api(`/api/cases/${caseId}/chain`);
    const merkle = await api(`/api/cases/${caseId}/merkle`);
    const trust = await api(`/api/cases/${caseId}/trust-receipts`);

    let html = '';

    // Chain Head
    html += `
    <div class="card">
        <div class="card-header">
            <h3>Chain of Custody</h3>
            <button class="btn btn-primary btn-sm" onclick="verifyChain('${caseId}')">⟳ Verify Chain</button>
        </div>
        <div class="card-body">
            <div class="integrity-section">
                <div class="integrity-header">
                    <span style="font-size:12px;color:var(--text-secondary)">Chain Head (SHA-256)</span>
                    <span class="badge badge-info">${chainHead?.event_count || 0} events</span>
                </div>
                <div class="integrity-value">${chainHead?.chain_head || 'No chain events'}</div>
            </div>
    `;

    // Chain events
    if (chain && chain.length) {
        html += '<div style="margin-top:16px">';
        html += '<div class="chain-event-row" style="font-weight:600;color:var(--text-muted);font-size:11px">' +
            '<div>#</div><div>Event</div><div>Actor</div><div>Hash</div></div>';

        for (const ev of chain) {
            html += `
                <div class="chain-event-row">
                    <div class="seq">${ev.sequence_number}</div>
                    <div class="event-type">${escapeHtml(ev.event_type)}</div>
                    <div>${escapeHtml(ev.actor)}</div>
                    <div class="hash">${ev.event_hash.substring(0, 24)}...</div>
                </div>`;
        }
        html += '</div>';
    }

    html += '</div></div>';

    // Merkle Tree
    html += `
    <div class="card">
        <div class="card-header">
            <h3>Merkle Tree</h3>
            <button class="btn btn-primary btn-sm" onclick="buildMerkle('${caseId}')">⟳ Build Merkle</button>
        </div>
        <div class="card-body">`;

    if (merkle && merkle.length) {
        const latest = merkle[0];
        html += `
            <div class="integrity-section">
                <div class="integrity-header">
                    <span style="font-size:12px;color:var(--text-secondary)">Merkle Root (SHA-256)</span>
                    <span class="badge badge-success">${latest.leaf_count} leaves</span>
                </div>
                <div class="integrity-value">${latest.root_hash}</div>
                <div style="font-size:11px;color:var(--text-muted);margin-top:8px">
                    Algorithm: ${latest.algorithm} · Created: ${formatDate(latest.created_at)}
                </div>
            </div>
            <button class="btn btn-sm" onclick="verifyMerkle('${caseId}', '${latest.id}')">Verify Merkle Root</button>
        `;
    } else {
        html += '<div class="empty-state">No Merkle tree built yet. Click "Build Merkle" to create one.</div>';
    }

    html += '</div></div>';

    container.innerHTML = html;
}

async function verifyChain(caseId) {
    try {
        const result = await api(`/api/cases/${caseId}/verify-chain`, { method: 'POST' });
        if (result) {
            if (result.valid) {
                showToast(`CHAIN VALID — ${result.verified_events} events verified`, 'success');
            } else {
                showToast(`CHAIN VERIFICATION FAILED at event #${result.first_failure}: ${result.failure_detail}`, 'error');
            }
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function buildMerkle(caseId) {
    try {
        const result = await api(`/api/cases/${caseId}/merkle`, { method: 'POST' });
        if (result) {
            showToast(`Merkle root built: ${result.root_hash.substring(0, 16)}...`, 'success');
            await loadIntegrity();
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function verifyMerkle(caseId, merkleId) {
    try {
        const result = await api(`/api/cases/${caseId}/merkle/${merkleId}/verify`, { method: 'POST' });
        if (result) {
            if (result.valid) {
                showToast('MERKLE VERIFIED — Root hash matches computed root', 'success');
            } else {
                showToast('MERKLE VERIFICATION FAILED — Root hash mismatch', 'error');
            }
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// =============================================================================
// Trust
// =============================================================================

async function loadTrust() {
    const caseId = document.getElementById('trust-case-select').value;
    const container = document.getElementById('trust-content');

    if (!caseId) {
        container.innerHTML = '<div class="empty-state">Select a case to view trust sealing status.</div>';
        return;
    }

    const receipts = await api(`/api/cases/${caseId}/trust-receipts`);

    let html = `
    <div class="card">
        <div class="card-header">
            <h3>Independent Trust Seal</h3>
            <button class="btn btn-primary btn-sm" onclick="requestTrustSign('${caseId}')">⟳ Request Trust Signature</button>
        </div>
        <div class="card-body">
            <p style="font-size:11px;color:var(--accent-amber);margin-bottom:16px">
                ⚠ This prototype trust service is NOT a government certification authority.
                It demonstrates the architecture of independent cryptographic trust anchoring.
            </p>`;

    if (receipts && receipts.length) {
        const latest = receipts[0];
        const isVerified = latest.verification_status === 'VERIFIED';
        const isSigned = latest.verification_status === 'SIGNED';

        html += `
            <div class="trust-card">
                <div class="trust-seal ${isVerified ? '' : (isSigned ? '' : 'unavailable')}">◇</div>
                <h4 style="margin-bottom:8px">Trust Seal ${isVerified ? 'VERIFIED' : isSigned ? 'SIGNED' : 'PENDING'}</h4>
                <div style="text-align:left;margin-top:16px">
                    <div class="evidence-meta-item" style="margin:6px 0">
                        <span class="meta-label">Authority</span>
                        <span class="meta-value">${escapeHtml(latest.authority_id)}</span>
                    </div>
                    <div class="evidence-meta-item" style="margin:6px 0">
                        <span class="meta-label">Algorithm</span>
                        <span class="meta-value">${escapeHtml(latest.algorithm)}</span>
                    </div>
                    <div class="evidence-meta-item" style="margin:6px 0">
                        <span class="meta-label">Chain Head</span>
                        <span class="meta-value" style="font-size:10px">${latest.chain_head.substring(0, 32)}...</span>
                    </div>
                    <div class="evidence-meta-item" style="margin:6px 0">
                        <span class="meta-label">Signature</span>
                        <span class="meta-value" style="font-size:10px">${latest.signature.substring(0, 32)}...</span>
                    </div>
                    <div class="evidence-meta-item" style="margin:6px 0">
                        <span class="meta-label">Timestamp</span>
                        <span class="meta-value">${formatDate(latest.timestamp)}</span>
                    </div>
                </div>
                <div style="margin-top:16px">
                    <button class="btn btn-success btn-sm" onclick="verifyTrust('${caseId}')">
                        ◆ Verify Trust Signature
                    </button>
                </div>
            </div>`;
    } else {
        html += `
            <div class="trust-card">
                <div class="trust-seal unavailable">◇</div>
                <h4>TRUST SEAL: NOT AVAILABLE</h4>
                <p style="font-size:12px;color:var(--text-muted);margin-top:8px">
                    No trust receipt has been issued for this case.
                    Ensure the trust service is running and click "Request Trust Signature".
                </p>
            </div>`;
    }

    html += '</div></div>';
    container.innerHTML = html;
}

async function requestTrustSign(caseId) {
    try {
        const result = await api(`/api/cases/${caseId}/trust-sign`, { method: 'POST' });
        if (result) {
            showToast('Trust signature issued successfully', 'success');
            await loadTrust();
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function verifyTrust(caseId) {
    try {
        const result = await api(`/api/cases/${caseId}/trust-verify`, { method: 'POST' });
        if (result) {
            if (result.valid) {
                showToast('SIGNATURE VERIFIED — Trust seal confirmed', 'success');
            } else {
                showToast('SIGNATURE INVALID — Trust seal verification failed', 'error');
            }
            await loadTrust();
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// =============================================================================
// Reports
// =============================================================================

async function loadReportCase() {
    const caseId = document.getElementById('report-case-select').value;
    const container = document.getElementById('report-content');

    if (!caseId) {
        container.innerHTML = '<div class="empty-state">Select a case to generate reports.</div>';
        return;
    }

    const caseData = allCases.find(c => c.id === caseId);

    container.innerHTML = `
    <div class="card">
        <div class="card-header">
            <h3>Forensic Report Generation</h3>
        </div>
        <div class="card-body">
            <div style="margin-bottom:16px">
                <p style="font-size:13px">Generate a complete forensic PDF report for case
                    <strong>${escapeHtml(caseData?.case_number || caseId)}</strong></p>
                <p style="font-size:11px;color:var(--text-muted);margin-top:8px">
                    The report includes: case information, evidence details, SHA-256 hashes,
                    AI analysis results, chain of custody, Merkle root, trust signature,
                    and legal certificate template.
                </p>
            </div>
            <button class="btn btn-primary btn-lg" onclick="generateReport('${caseId}')">
                ◰ Generate PDF Report
            </button>
        </div>
    </div>`;
}

async function generateReport(caseId) {
    showToast('Generating forensic report...', 'info');
    try {
        const blob = await api(`/api/cases/${caseId}/report`, { method: 'POST' });
        if (blob instanceof Blob) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `SAKSHYA_Report.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('Report generated and downloaded', 'success');
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// =============================================================================
// Utility Functions
// =============================================================================

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatTime(seconds) {
    if (seconds === null || seconds === undefined) return 'N/A';
    if (seconds > 1e9) {
        // Epoch timestamp
        const d = new Date(seconds * 1000);
        return d.toLocaleTimeString('en-IN');
    }
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
}

function formatDuration(seconds) {
    if (!seconds) return 'N/A';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
}

function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
    }
    return `${size.toFixed(1)} ${units[i]}`;
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    navigateTo('dashboard');
});
