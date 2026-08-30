// THE ALLOCATOR — Standalone & Leaflet GIS Engine
class GISMapEngine {
    constructor(elementId) {
        this.elementId = elementId;
        this.depots = [];
        this.incidents = [];
    }

    init() {
        const container = document.getElementById(this.elementId);
        if (!container) return;

        // Try initializing Leaflet if available & connected, else fallback to SVG canvas
        if (window.L && window.L.map) {
            try {
                this.map = L.map(this.elementId, { zoomControl: true, attributionControl: false }).setView([34.0522, -118.2437], 10);
                const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 });
                tiles.addTo(this.map);
                
                let tileFailed = false;
                tiles.on('tileerror', () => {
                    if (!tileFailed) {
                        tileFailed = true;
                        this.renderSVGCanvasMap();
                    }
                });
                return;
            } catch (e) {
                console.warn('Leaflet init warning, using SVG map canvas.');
            }
        }
        
        // Fallback: Standalone High-Performance SVG Canvas Map
        this.renderSVGCanvasMap();
    }

    renderDepotsAndIncidents(depots, incidents) {
        this.depots = depots || [];
        this.incidents = incidents || [];

        // If Leaflet is active and working
        if (this.map && window.L && !this.isFallbackActive) {
            try {
                if (this.depotMarkers) this.depotMarkers.forEach(m => this.map.removeLayer(m));
                if (this.incidentMarkers) this.incidentMarkers.forEach(m => this.map.removeLayer(m));
                if (this.dispatchLines) this.dispatchLines.forEach(l => this.map.removeLayer(l));
                
                this.depotMarkers = [];
                this.incidentMarkers = [];
                this.dispatchLines = [];

                depots.forEach(d => {
                    const m = L.marker([d.lat, d.lng]).addTo(this.map);
                    m.bindPopup(`<b>${d.name}</b><br>${d.sector}`);
                    this.depotMarkers.push(m);
                });

                incidents.forEach(inc => {
                    const m = L.marker([inc.lat, inc.lng]).addTo(this.map);
                    m.bindPopup(`<b>${inc.title}</b><br>Severity: ${inc.severity}`);
                    this.incidentMarkers.push(m);
                });
                return;
            } catch (e) {}
        }

        // Render via Standalone SVG Canvas Map
        this.renderSVGCanvasMap();
    }

    renderSVGCanvasMap() {
        this.isFallbackActive = true;
        const container = document.getElementById(this.elementId);
        if (!container) return;

        // Render a high-tech Dark GIS Sector Grid with Depot Nodes & Incident Vectors
        let depotsSvg = "";
        let incidentsSvg = "";
        let linesSvg = "";

        // Map coordinate normalization bounds (LA region lat/lng bounding box)
        const minLat = 33.88, maxLat = 34.20;
        const minLng = -118.55, maxLng = -118.10;

        const project = (lat, lng) => {
            const x = ((lng - minLng) / (maxLng - minLng)) * 100;
            const y = (1 - (lat - minLat) / (maxLat - minLat)) * 100;
            return {
                x: Math.max(5, Math.min(95, x)),
                y: Math.max(5, Math.min(95, y))
            };
        };

        // Draw connections
        this.incidents.forEach(inc => {
            const incPt = project(inc.lat || 34.05, inc.lng || -118.25);
            if (this.depots.length > 0) {
                const depPt = project(this.depots[0].lat, this.depots[0].lng);
                linesSvg += `
                    <line x1="${depPt.x}%" y1="${depPt.y}%" x2="${incPt.x}%" y2="${incPt.y}%"
                          stroke="#3b82f6" stroke-width="2" stroke-dasharray="4 4" opacity="0.7" />
                `;
            }
        });

        // Draw Depots
        this.depots.forEach(d => {
            const pt = project(d.lat, d.lng);
            depotsSvg += `
                <g class="depot-node" transform="translate(0, 0)">
                    <circle cx="${pt.x}%" cy="${pt.y}%" r="10" fill="rgba(59, 130, 246, 0.25)" stroke="#3b82f6" stroke-width="2" />
                    <circle cx="${pt.x}%" cy="${pt.y}%" r="4" fill="#3b82f6" />
                    <text x="${pt.x}%" y="${pt.y + 4}%" fill="#94a3b8" font-size="10" font-weight="600" text-anchor="middle">
                        ${d.name}
                    </text>
                </g>
            `;
        });

        // Draw Incidents
        this.incidents.forEach(inc => {
            const pt = project(inc.lat || 34.07, inc.lng || -118.25);
            const color = inc.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b';
            incidentsSvg += `
                <g class="incident-node">
                    <circle cx="${pt.x}%" cy="${pt.y}%" r="16" fill="${color}22" stroke="${color}" stroke-width="1.5">
                        <animate attributeName="r" values="12;18;12" dur="2s" repeatCount="indefinite" />
                        <animate attributeName="opacity" values="0.8;0.3;0.8" dur="2s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="${pt.x}%" cy="${pt.y}%" r="6" fill="${color}" />
                    <text x="${pt.x}%" y="${pt.y - 3}%" fill="${color}" font-size="11" font-weight="700" text-anchor="middle">
                        ⚠️ ${inc.title}
                    </text>
                </g>
            `;
        });

        container.innerHTML = `
            <div style="position: relative; width: 100%; height: 100%; background: #0f172a; border-radius: 6px; overflow: hidden;">
                <!-- Dark Sector Grid Background -->
                <svg width="100%" height="100%" style="position: absolute; top:0; left:0;">
                    <defs>
                        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.04)" stroke-width="1"/>
                        </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid)" />
                    
                    <!-- Sector Quadrant Dividers -->
                    <line x1="50%" y1="0" x2="50%" y2="100%" stroke="rgba(255, 255, 255, 0.08)" stroke-dasharray="2 4" />
                    <line x1="0" y1="50%" x2="100%" y2="50%" stroke="rgba(255, 255, 255, 0.08)" stroke-dasharray="2 4" />
                    
                    <!-- Sector Labels -->
                    <text x="5%" y="8%" fill="#64748b" font-size="10" font-weight="600">NORTH SECTOR</text>
                    <text x="80%" y="8%" fill="#64748b" font-size="10" font-weight="600">EAST SECTOR</text>
                    <text x="5%" y="95%" fill="#64748b" font-size="10" font-weight="600">WEST SECTOR</text>
                    <text x="80%" y="95%" fill="#64748b" font-size="10" font-weight="600">SOUTH SECTOR</text>

                    <!-- Connections -->
                    ${linesSvg}

                    <!-- Strategic Depots -->
                    ${depotsSvg}

                    <!-- Incidents -->
                    ${incidentsSvg}
                </svg>

                <div style="position: absolute; bottom: 10px; right: 10px; background: rgba(15, 23, 42, 0.85); padding: 4px 8px; border-radius: 4px; border: 1px solid #334155; font-size: 10px; color: #94a3b8;">
                    Standalone GIS Engine • Vector Grid Active
                </div>
            </div>
        `;
    }
}

window.gisEngine = new GISMapEngine('gisMap');
