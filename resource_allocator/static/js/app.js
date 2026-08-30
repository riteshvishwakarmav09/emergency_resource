// THE ALLOCATOR — Main Application Controller
class EmergencyApp {
    constructor() {
        this.currentUser = { role: 'Admin', full_name: 'Commander Sarah Vance' };
        this.vaultDecrypted = false;
        this.categories = [];
        this.depots = [];
        this.incidents = [];
        this.init();
    }

    init() {
        this.setupTabNavigation();
        this.setupEventListeners();
        this.loadInitialData();

        // Initialize GIS map after DOM layout ready
        setTimeout(() => {
            window.gisEngine.init();
            window.gisEngine.renderDepotsAndIncidents(this.depots, this.incidents);
        }, 300);
    }

    setupTabNavigation() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetTab = btn.getAttribute('data-tab');
                document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

                btn.classList.add('active');
                document.getElementById(targetTab)?.classList.add('active');

                // Trigger specific tab reloads
                if (targetTab === 'tab-dashboard') this.loadDashboardData();
                if (targetTab === 'tab-recommendations') this.populateIncidentSelector();
                if (targetTab === 'tab-resources') this.loadResources();
                if (targetTab === 'tab-categories') this.loadCategories();
                if (targetTab === 'tab-audit') this.loadAuditLogs();
                if (targetTab === 'tab-backups') this.loadBackups();
            });
        });
    }

    setupEventListeners() {
        // Switch Role Modal
        document.getElementById('btnSwitchRole')?.addEventListener('click', () => {
            document.getElementById('modalAuth')?.classList.add('active');
        });

        document.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
            });
        });

        // Role Card Selection
        document.querySelectorAll('.role-option-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.role-option-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');
            });
        });

        document.getElementById('btnConfirmRoleSwitch')?.addEventListener('click', () => this.executeRoleSwitch());

        // Decrypt Toggle
        document.getElementById('btnToggleDecrypt')?.addEventListener('click', () => this.toggleVaultDecryption());

        // Incident Creation Modal
        document.getElementById('btnDeclareIncident')?.addEventListener('click', () => {
            document.getElementById('modalIncident')?.classList.add('active');
        });

        document.getElementById('formAddIncident')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleDeclareIncident();
        });

        // Add Resource Modal
        document.getElementById('btnAddResource')?.addEventListener('click', () => {
            this.populateResourceModalSelects();
            document.getElementById('modalResource')?.classList.add('active');
        });

        document.getElementById('formAddResource')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleAddResource();
        });

        // Add Category Modal
        document.getElementById('btnCreateCategory')?.addEventListener('click', () => {
            document.getElementById('modalCategory')?.classList.add('active');
        });

        document.getElementById('formCategory')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleAddCategory();
        });

        // Simulation Slider
        const simSlider = document.getElementById('simSeverity');
        simSlider?.addEventListener('input', (e) => {
            document.getElementById('simSeverityValue').textContent = `${e.target.value}x Load`;
        });

        document.getElementById('btnRunSimulation')?.addEventListener('click', () => this.runSimulation());

        // Refresh Recs
        document.getElementById('btnRefreshRecs')?.addEventListener('click', () => {
            const selectedIncId = document.getElementById('selectRecIncident')?.value;
            if (selectedIncId) window.decisionUI.loadRecommendation(selectedIncId);
        });

        // Backup & Restore
        document.getElementById('btnCreateBackup')?.addEventListener('click', () => this.createBackup());
        document.getElementById('restoreBackupForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.restoreBackup();
        });

        document.getElementById('btnExportAuditLogs')?.addEventListener('click', () => {
            window.location.href = '/api/logs/export';
        });
    }

    async loadInitialData() {
        await this.checkAuthStatus();
        await this.loadDashboardData();
        await this.loadCategories();
    }

    async checkAuthStatus() {
        try {
            const res = await fetch('/api/auth/me');
            const data = await res.json();
            if (data.user) {
                this.currentUser = data.user;
                this.updateUserRoleBadge();
            }
        } catch (e) {}
    }

    updateUserRoleBadge() {
        document.getElementById('userNameText').textContent = this.currentUser.full_name;
        document.getElementById('userRoleText').textContent = this.currentUser.role;
    }

    async executeRoleSwitch() {
        const activeCard = document.querySelector('.role-option-card.active');
        if (!activeCard) return;

        const username = activeCard.getAttribute('data-username');
        const password = activeCard.getAttribute('data-pass');

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await res.json();
            if (res.ok) {
                this.currentUser = data.user;
                this.updateUserRoleBadge();
                this.vaultDecrypted = false;
                document.getElementById('modalAuth')?.classList.remove('active');
                this.showToast(`Switched active session role to: ${data.user.role}`, 'success');
                this.loadDashboardData();
                this.loadResources();
            } else {
                this.showToast(data.error || 'Login failed', 'error');
            }
        } catch (e) {
            this.showToast('Authentication network failure', 'error');
        }
    }

    async loadDashboardData() {
        try {
            const res = await fetch('/api/incidents');
            const data = await res.json();
            this.incidents = data.incidents || [];
            this.depots = data.depots || [];

            document.getElementById('statActiveIncidents').textContent = this.incidents.length;
            
            // Render GIS Map
            window.gisEngine.renderDepotsAndIncidents(this.depots, this.incidents);

            // Render Incident Feed
            const feedContainer = document.getElementById('incidentListFeed');
            if (this.incidents.length === 0) {
                feedContainer.innerHTML = `<div class="glass-card text-center p-3 text-muted">No active emergency incidents declared.</div>`;
                return;
            }

            feedContainer.innerHTML = this.incidents.map(inc => `
                <div class="incident-card-item">
                    <div class="inc-header">
                        <span class="inc-title">${inc.title}</span>
                        <span class="inc-tag ${inc.severity.toLowerCase()}">${inc.severity}</span>
                    </div>
                    <p class="inc-desc">${inc.description}</p>
                    <div class="inc-meta">
                        <span><i class="fa-solid fa-location-crosshairs"></i> ${inc.sector}</span>
                        <span><i class="fa-solid fa-users"></i> ${inc.affected_population.toLocaleString()} citizens</span>
                    </div>
                </div>
            `).join('');

            // Also update rec count badge
            document.getElementById('recBadgeCount').textContent = this.incidents.length;
        } catch (err) {
            console.error('Failed loading dashboard incidents', err);
        }
    }

    async loadResources() {
        const tbody = document.getElementById('resourcesTbody');
        tbody.innerHTML = `<tr><td colspan="8" class="text-center p-3"><i class="fa-solid fa-spinner fa-spin"></i> Accessing Encrypted Vault...</td></tr>`;

        try {
            const res = await fetch(`/api/resources?decrypt=${this.vaultDecrypted}`);
            const data = await res.json();
            const resources = data.resources || [];

            let totalUnits = 0;
            resources.forEach(r => totalUnits += r.quantity);
            document.getElementById('statTotalStock').textContent = totalUnits;

            tbody.innerHTML = resources.map(r => `
                <tr>
                    <td><span class="code-pill">${r.id}</span></td>
                    <td><strong>${r.name}</strong></td>
                    <td>${r.category_name}</td>
                    <td><i class="fa-solid fa-warehouse text-cyan"></i> ${r.depot_name}</td>
                    <td><strong>${r.quantity}</strong> ${r.unit}</td>
                    <td><span class="badge ${r.status === 'Available' ? 'badge-info' : 'badge-alert'}">${r.status}</span></td>
                    <td class="${r.is_decrypted ? 'decrypted-text' : 'encrypted-text'}">
                        ${r.is_decrypted ? '<i class="fa-solid fa-lock-open glow-green"></i> ' : '<i class="fa-solid fa-lock"></i> '}
                        ${r.sensitive_specs}
                    </td>
                    <td class="${r.is_decrypted ? 'decrypted-text' : 'encrypted-text'}">
                        ${r.secure_location_code}
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-critical text-center">Failed retrieving resource vault.</td></tr>`;
        }
    }

    async toggleVaultDecryption() {
        if (this.currentUser.role === 'Field Officer') {
            this.showToast('ACCESS DENIED: Field Officer role lacks decryption keys.', 'error');
            return;
        }

        this.vaultDecrypted = !this.vaultDecrypted;
        const btnLabel = document.getElementById('lblDecryptToggle');
        if (this.vaultDecrypted) {
            btnLabel.textContent = 'Encrypt Vault View';
            this.showToast('Vault Payload Decrypted with Session Keys', 'success');
        } else {
            btnLabel.textContent = 'Authorize & Decrypt Vault';
            this.showToast('Vault Masked to Cryptographic Ciphertext', 'info');
        }
        this.loadResources();
    }

    async loadCategories() {
        try {
            const res = await fetch('/api/categories');
            const data = await res.json();
            this.categories = data.categories || [];

            const grid = document.getElementById('categoryGrid');
            grid.innerHTML = this.categories.map(c => `
                <div class="category-card glass-card">
                    <div>
                        <div class="cat-header">
                            <div class="cat-icon-box"><i class="fa-solid fa-${c.icon || 'box'}"></i></div>
                            <span class="cat-title">${c.name}</span>
                        </div>
                        <p class="cat-desc">${c.description}</p>
                    </div>
                    <div class="cat-footer">
                        <span class="text-sub">Priority Weight: <strong>${c.priority_weight}</strong></span>
                        <span class="code-pill">${c.id}</span>
                    </div>
                </div>
            `).join('');
        } catch (e) {}
    }

    populateResourceModalSelects() {
        const catSelect = document.getElementById('resCategory');
        catSelect.innerHTML = this.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');

        const depotSelect = document.getElementById('resDepot');
        depotSelect.innerHTML = this.depots.map(d => `<option value="${d.id}">${d.name} (${d.sector})</option>`).join('');
    }

    async handleAddResource() {
        const payload = {
            name: document.getElementById('resName').value,
            category_id: document.getElementById('resCategory').value,
            depot_id: document.getElementById('resDepot').value,
            quantity: parseInt(document.getElementById('resQty').value),
            min_reserve: parseInt(document.getElementById('resReserve').value),
            sensitive_specs: document.getElementById('resSpecs').value,
            secure_location_code: document.getElementById('resLocation').value
        };

        try {
            const res = await fetch('/api/resources', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                this.showToast('Resource encrypted with AES-256 and saved!', 'success');
                document.getElementById('modalResource')?.classList.remove('active');
                this.loadResources();
            } else {
                const err = await res.json();
                this.showToast(err.error || 'Failed adding resource', 'error');
            }
        } catch (e) {
            this.showToast('Network error', 'error');
        }
    }

    async handleAddCategory() {
        const payload = {
            name: document.getElementById('catName').value,
            description: document.getElementById('catDesc').value,
            icon: document.getElementById('catIcon').value,
            priority_weight: parseFloat(document.getElementById('catWeight').value)
        };

        try {
            const res = await fetch('/api/categories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                this.showToast('Category created successfully', 'success');
                document.getElementById('modalCategory')?.classList.remove('active');
                this.loadCategories();
            } else {
                const err = await res.json();
                this.showToast(err.error || 'Failed creating category', 'error');
            }
        } catch (e) {
            this.showToast('Network error', 'error');
        }
    }

    async handleDeclareIncident() {
        const payload = {
            title: document.getElementById('incTitle').value,
            type: document.getElementById('incType').value,
            severity: document.getElementById('incSeverity').value,
            sector: document.getElementById('incSector').value,
            affected_population: parseInt(document.getElementById('incPopulation').value),
            description: document.getElementById('incDesc').value,
            required_needs: [
                { category_id: "CAT-001", quantity: 10, name: "Mobile ICU Ventilators & Plasma" },
                { category_id: "CAT-003", quantity: 3, name: "Heavy Generators" }
            ]
        };

        try {
            const res = await fetch('/api/incidents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                this.showToast('Emergency Crisis Broadcasted!', 'success');
                document.getElementById('modalIncident')?.classList.remove('active');
                this.loadDashboardData();
            }
        } catch (e) {}
    }

    populateIncidentSelector() {
        const select = document.getElementById('selectRecIncident');
        if (!select) return;

        select.innerHTML = this.incidents.map(i => `
            <option value="${i.id}">${i.title} [${i.severity}]</option>
        `).join('');

        if (this.incidents.length > 0) {
            window.decisionUI.loadRecommendation(this.incidents[0].id);
        }
    }

    async runSimulation() {
        const scenario = document.getElementById('simScenarioType').value;
        const severity = parseFloat(document.getElementById('simSeverity').value);
        const output = document.getElementById('simulationOutput');

        output.innerHTML = `<div class="p-3 text-cyan"><i class="fa-solid fa-spinner fa-spin"></i> Running Monte-Carlo Stress Test...</div>`;

        try {
            const res = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenario, severity })
            });

            const data = await res.json();
            output.innerHTML = `
                <div class="glass-card mt-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h4>System Readiness Score: <strong>${data.overall_preparedness_index}%</strong></h4>
                        <span class="badge ${data.overall_preparedness_index > 75 ? 'badge-info' : 'badge-alert'}">${data.recommendation}</span>
                    </div>
                    <div class="simulation-table-space" style="font-size: 12px; margin-top: 10px;">
                        ${data.breakdown.map(b => `
                            <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-glass);">
                                <span>${b.category_name} (Req: ${b.projected_demand} | Stock: ${b.current_stock})</span>
                                <span><strong>${b.readiness_pct}% Prepared</strong> [${b.status}]</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } catch (e) {
            output.innerHTML = `<div class="text-critical">Simulation failed.</div>`;
        }
    }

    async loadAuditLogs() {
        const tbody = document.getElementById('auditLogsTbody');
        try {
            const res = await fetch('/api/logs');
            const data = await res.json();
            const logs = data.logs || [];

            tbody.innerHTML = logs.map(l => `
                <tr>
                    <td class="code-pill">${new Date(l.timestamp).toLocaleTimeString()}</td>
                    <td><strong>${l.actor}</strong></td>
                    <td><span class="badge badge-info">${l.role}</span></td>
                    <td><strong class="text-cyan">${l.action}</strong></td>
                    <td>${l.resource}</td>
                    <td class="code-pill">${l.ip_address}</td>
                    <td><span class="badge ${l.status === 'SUCCESS' ? 'badge-info' : 'badge-alert'}">${l.status}</span></td>
                    <td style="font-size: 11px; color: var(--text-muted);">${l.details}</td>
                </tr>
            `).join('');
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-critical text-center">Unauthorized to view access logs.</td></tr>`;
        }
    }

    async createBackup() {
        try {
            const res = await fetch('/api/backups/create', { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                this.showToast('AES-256 Encrypted Backup Snapshot Created', 'success');
                this.loadBackups();
            } else {
                this.showToast(data.error || 'Backup creation failed', 'error');
            }
        } catch (e) {
            this.showToast('Network error', 'error');
        }
    }

    async loadBackups() {
        const container = document.getElementById('backupList');
        try {
            const res = await fetch('/api/backups');
            const data = await res.json();
            const backups = data.backups || [];

            if (backups.length === 0) {
                container.innerHTML = `<div class="text-muted p-2">No backup snapshots found.</div>`;
                return;
            }

            container.innerHTML = backups.map(b => `
                <div class="backup-item">
                    <div>
                        <strong style="font-size: 13px;">${b.filename}</strong><br>
                        <span class="text-sub" style="font-size: 11px;">Size: ${(b.size_bytes / 1024).toFixed(1)} KB | ${new Date(b.created_at).toLocaleString()}</span>
                    </div>
                    <a href="/api/backups/download/${b.filename}" class="btn btn-sm btn-outline-cyan">
                        <i class="fa-solid fa-download"></i> Download
                    </a>
                </div>
            `).join('');
        } catch (e) {
            container.innerHTML = `<div class="text-critical p-2">Admin privilege required for backup management.</div>`;
        }
    }

    async restoreBackup() {
        const fileInput = document.getElementById('backupFileInput');
        if (!fileInput.files || fileInput.files.length === 0) return;

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            const res = await fetch('/api/backups/restore', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (res.ok) {
                this.showToast('HMAC Verified! System State Restored Successfully!', 'success');
                this.loadDashboardData();
                this.loadResources();
            } else {
                this.showToast(data.error || 'Restore failed', 'error');
            }
        } catch (e) {
            this.showToast('Failed executing backup restore', 'error');
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fa-solid ${type === 'success' ? 'fa-circle-check text-emerald' : type === 'error' ? 'fa-circle-xmark text-critical' : 'fa-circle-info text-cyan'}"></i>
            <span>${message}</span>
        `;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new EmergencyApp();
});
