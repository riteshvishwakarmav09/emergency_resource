// THE ALLOCATOR — Decision Support & Recommendation UI Controller
class DecisionUIController {
    constructor() {
        this.currentPlan = null;
    }

    async loadRecommendation(incidentId) {
        const container = document.getElementById("recommendationResultsContainer");
        container.innerHTML = `<div class="p-3 text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Calculating optimal dispatch recommendations...</div>`;

        try {
            const res = await fetch(`/api/recommendations/${incidentId}`);
            const data = await res.json();

            if (data.error) {
                container.innerHTML = `<div class="p-3 text-critical">${data.error}</div>`;
                return;
            }

            this.currentPlan = data;
            this.renderPlanCard(data);
        } catch (err) {
            container.innerHTML = `<div class="p-3 text-critical">Failed to reach decision engine.</div>`;
        }
    }

    renderPlanCard(plan) {
        const container = document.getElementById("recommendationResultsContainer");

        let deficitsHtml = "";
        if (plan.deficits && plan.deficits.length > 0) {
            deficitsHtml = `
                <div class="vault-notice mb-3" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); color: #f87171;">
                    <strong>Shortage Warnings:</strong>
                    <ul style="margin-left: 18px; margin-top: 4px;">
                        ${plan.deficits.map(d => `
                            <li>
                                <strong>${d.resource_name}</strong>: Required ${d.required}, available ${d.available} (Deficit: -${d.deficit})
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }

        let matrixRows = "";
        if (plan.allocated_summary) {
            plan.allocated_summary.forEach(summary => {
                summary.allocations.forEach(alloc => {
                    matrixRows += `
                        <tr>
                            <td><strong>${summary.need_name}</strong></td>
                            <td><span class="code-pill">${alloc.resource_id}</span> ${alloc.resource_name}</td>
                            <td>${alloc.depot_name}</td>
                            <td><strong>${alloc.quantity}</strong></td>
                            <td>${alloc.distance_km} km</td>
                            <td>${alloc.eta_minutes} mins</td>
                        </tr>
                    `;
                });
            });
        }

        const rationalesHtml = plan.rationales ? plan.rationales.map(r => `<p style="margin-bottom: 4px; font-size: 12px; color: var(--text-muted);">${r}</p>`).join('') : "";

        container.innerHTML = `
            <div class="table-card" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 18px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; margin-bottom: 14px;">
                    <div>
                        <span class="inc-tag ${plan.severity.toLowerCase()}">${plan.severity}</span>
                        <h3 style="font-size: 16px; font-weight: 600; margin-top: 6px;">
                            ${plan.incident_title}
                        </h3>
                        <span style="font-size: 11px; color: var(--text-muted);">
                            Response Window: <strong>${plan.estimated_response_window}</strong>
                        </span>
                    </div>

                    <div style="text-align: right;">
                        <span style="font-size: 24px; font-weight: 700; color: var(--accent-emerald);">${plan.readiness_impact_score}%</span>
                        <span style="display: block; font-size: 11px; color: var(--text-muted);">Readiness Score</span>
                    </div>
                </div>

                <div class="mb-3">
                    ${rationalesHtml}
                </div>

                ${deficitsHtml}

                <h4 style="font-size: 13px; font-weight: 600; margin: 14px 0 8px 0;">
                    Dispatch Allocation Plan
                </h4>

                <table class="dispatch-matrix-table">
                    <thead>
                        <tr>
                            <th>Category Need</th>
                            <th>Resource</th>
                            <th>Source Depot</th>
                            <th>Quantity</th>
                            <th>Distance</th>
                            <th>Est. ETA</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${matrixRows || '<tr><td colspan="6" class="text-muted">No resource allocations available.</td></tr>'}
                    </tbody>
                </table>

                <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
                    <button class="btn btn-primary" id="btnApproveDispatch">
                        <i class="fa-solid fa-check"></i> Approve & Execute Dispatch
                    </button>
                </div>
            </div>
        `;

        document.getElementById("btnApproveDispatch")?.addEventListener("click", () => this.approveDispatch());
    }

    async approveDispatch() {
        if (!this.currentPlan) return;

        const allocationsPayload = [];
        this.currentPlan.allocated_summary.forEach(summary => {
            summary.allocations.forEach(alloc => {
                allocationsPayload.push({
                    resource_id: alloc.resource_id,
                    resource_name: alloc.resource_name,
                    depot_name: alloc.depot_name,
                    quantity: alloc.quantity
                });
            });
        });

        try {
            const res = await fetch("/api/recommendations/approve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    incident_id: this.currentPlan.incident_id,
                    allocations: allocationsPayload
                })
            });

            const result = await res.json();
            if (res.ok) {
                window.app.showToast("Dispatch Plan Approved", "success");
                window.app.loadDashboardData();
                window.app.loadResources();
            } else {
                window.app.showToast(result.error || "Approval failed", "error");
            }
        } catch (err) {
            window.app.showToast("Network error executing approval", "error");
        }
    }
}

window.decisionUI = new DecisionUIController();
