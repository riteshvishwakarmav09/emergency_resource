import math

class DecisionEngine:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates distance in kilometers between two geographic points."""
        R = 6371.0 # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)

    def calculate_eta_minutes(self, distance_km: float, transport_type: str = "road") -> int:
        """Estimates travel time in minutes based on transit mode."""
        speed_kmh = {
            "air": 220,     # Helicopter / MedEvac
            "express": 80,  # Emergency vehicle with sirens
            "road": 50,     # Heavy convoy / trucks
            "water": 35     # Rescue boats
        }.get(transport_type, 50)

        hours = distance_km / max(speed_kmh, 1)
        return max(5, int(hours * 60) + 10) # 10 min base loading buffer

    def analyze_incident_recommendations(self, incident_id: str, role: str = "Dispatcher") -> dict:
        """
        Main Decision-Support algorithm: Analyzes an active incident, inspects depot inventories,
        calculates optimal dispatch recommendations, and identifies resource deficits.
        """
        incidents = self.db.get_incidents()
        incident = next((i for i in incidents if i["id"] == incident_id), None)
        if not incident:
            return {"error": f"Incident '{incident_id}' not found."}

        inc_lat = incident.get("lat", 34.0522)
        inc_lng = incident.get("lng", -118.2437)

        depots = {d["id"]: d for d in self.db.get_depots()}
        resources = self.db.get_resources(decrypt=False, role=role)
        categories = {c["id"]: c for c in self.db.get_categories()}

        # Group resources by category and depot
        cat_map = {}
        for r in resources:
            cid = r["category_id"]
            if cid not in cat_map:
                cat_map[cid] = []
            cat_map[cid].append(r)

        recommendations = []
        deficits = []
        overall_impact_score = 100.0
        allocated_summary = []

        required_needs = incident.get("required_needs", [])

        for need in required_needs:
            target_cat_id = need.get("category_id")
            target_qty = need.get("quantity", 1)
            need_name = need.get("name", "Emergency Resource")

            cat_info = categories.get(target_cat_id, {})
            cat_weight = cat_info.get("priority_weight", 1.0)

            # Candidate resources across all depots matching category
            candidates = cat_map.get(target_cat_id, [])

            if not candidates:
                deficits.append({
                    "category_id": target_cat_id,
                    "resource_name": need_name,
                    "required": target_qty,
                    "available": 0,
                    "deficit": target_qty,
                    "severity": "CRITICAL - NO STOCK AVAILABLE"
                })
                overall_impact_score -= 25.0
                continue

            # Score each candidate depot resource based on:
            # 1. Available quantity above reserve
            # 2. Distance to incident site
            candidate_scores = []
            for res in candidates:
                depot = depots.get(res["depot_id"], {})
                dep_lat = depot.get("lat", inc_lat)
                dep_lng = depot.get("lng", inc_lng)

                dist_km = self.haversine_distance(inc_lat, inc_lng, dep_lat, dep_lng)
                
                # Transport type heuristic
                trans_type = "air" if "Helicopter" in res["name"] else "express"
                eta_min = self.calculate_eta_minutes(dist_km, trans_type)

                avail_qty = res["quantity"]
                reserve_qty = res.get("min_reserve", 0)
                usable_qty = max(0, avail_qty - reserve_qty)

                # Composite score formula: (Usable Quantity * 10) - (Distance in KM * 2) - (ETA * 0.5)
                comp_score = (usable_qty * 10.0) - (dist_km * 2.0) - (eta_min * 0.5) + (cat_weight * 50.0)

                candidate_scores.append({
                    "resource": res,
                    "depot": depot,
                    "distance_km": dist_km,
                    "eta_minutes": eta_min,
                    "usable_qty": usable_qty,
                    "total_qty": avail_qty,
                    "score": comp_score
                })

            # Sort candidate sources by composite score descending
            candidate_scores.sort(key=lambda x: x["score"], reverse=True)

            # Fulfillment matching
            fulfilled_qty = 0
            allocations_for_need = []

            for cand in candidate_scores:
                if fulfilled_qty >= target_qty:
                    break

                rem_needed = target_qty - fulfilled_qty
                res = cand["resource"]
                
                # Take up to usable_qty, or if critical emergency take total_qty if needed
                take_qty = min(rem_needed, cand["usable_qty"])
                if take_qty == 0 and cand["total_qty"] > 0 and incident.get("severity") == "CRITICAL":
                    # Critical emergency override - breach minimum reserve
                    take_qty = min(rem_needed, cand["total_qty"])

                if take_qty > 0:
                    fulfilled_qty += take_qty
                    allocations_for_need.append({
                        "resource_id": res["id"],
                        "resource_name": res["name"],
                        "depot_id": cand["depot"].get("id"),
                        "depot_name": cand["depot"].get("name"),
                        "quantity": take_qty,
                        "distance_km": cand["distance_km"],
                        "eta_minutes": cand["eta_minutes"],
                        "reserve_overridden": take_qty > cand["usable_qty"]
                    })

            if fulfilled_qty < target_qty:
                unmet = target_qty - fulfilled_qty
                deficits.append({
                    "category_id": target_cat_id,
                    "resource_name": need_name,
                    "required": target_qty,
                    "available": fulfilled_qty,
                    "deficit": unmet,
                    "severity": "PARTIAL DEFICIT"
                })
                overall_impact_score -= (unmet / target_qty) * 20.0

            if allocations_for_need:
                allocated_summary.append({
                    "need_name": need_name,
                    "target_quantity": target_qty,
                    "fulfilled_quantity": fulfilled_qty,
                    "allocations": allocations_for_need
                })

        # Build rationales & action plan
        rationales = []
        if deficits:
            rationales.append(f"⚠️ Warning: Detected {len(deficits)} resource deficit(s) across depots. Immediate inter-agency request recommended.")
        else:
            rationales.append("✅ Optimal Dispatch Path Identified: 100% of required crisis resources are ready for immediate deployment.")

        fastest_eta = min([a["eta_minutes"] for s in allocated_summary for a in s["allocations"]], default=15)
        slowest_eta = max([a["eta_minutes"] for s in allocated_summary for a in s["allocations"]], default=45)

        recommendation_plan = {
            "incident_id": incident["id"],
            "incident_title": incident["title"],
            "severity": incident.get("severity", "HIGH"),
            "urgency_score": incident.get("urgency_score", 8.0),
            "generated_at": incident.get("created_at"),
            "readiness_impact_score": max(10.0, round(overall_impact_score, 1)),
            "estimated_response_window": f"{fastest_eta} - {slowest_eta} min",
            "allocated_summary": allocated_summary,
            "deficits": deficits,
            "rationales": rationales,
            "recommended_action": "APPROVE_DISPATCH_PLAN" if not deficits else "APPROVE_WITH_DEFICIT_OVERRIDE"
        }

        return recommendation_plan

    def suggest_stock_rebalancing(self) -> list:
        """
        Analyzes depots with excess stock vs depots located in high-risk zones,
        suggesting proactive stock transfers.
        """
        depots = self.db.get_depots()
        resources = self.db.get_resources(decrypt=False)
        incidents = [i for i in self.db.get_incidents() if i.get("status") == "ACTIVE"]

        if not incidents:
            return []

        # Find sectors with active high-severity incidents
        high_risk_sectors = set(i.get("sector") for i in incidents if i.get("severity") in ["CRITICAL", "HIGH"])

        suggestions = []
        for r in resources:
            depot_id = r.get("depot_id")
            depot = next((d for d in depots if d["id"] == depot_id), {})
            depot_sector = depot.get("sector", "")

            # If resource is in a low-risk sector and has surplus (> 2x reserve)
            if depot_sector not in high_risk_sectors and r["quantity"] > (r.get("min_reserve", 0) * 2):
                surplus = r["quantity"] - (r.get("min_reserve", 0) * 2)
                
                # Find target depot in high risk sector
                target_depot = next((d for d in depots if d.get("sector") in high_risk_sectors), None)
                if target_depot and surplus > 0:
                    suggestions.append({
                        "resource_id": r["id"],
                        "resource_name": r["name"],
                        "from_depot": depot.get("name"),
                        "to_depot": target_depot.get("name"),
                        "transfer_quantity": min(surplus, 10),
                        "reason": f"Proactive relocation to high-risk zone '{target_depot.get('sector')}' due to active disaster activity."
                    })

        return suggestions

    def run_scenario_simulation(self, scenario_type: str, severity_multiplier: float = 1.5) -> dict:
        """
        Simulates hypothetical emergency scenarios to assess system preparedness and bottleneck points.
        """
        resources = self.db.get_resources(decrypt=False)
        categories = {c["id"]: c["name"] for c in self.db.get_categories()}

        # Preset scenario demand multipliers
        demands = {
            "Earthquake": {"Medical & Trauma": 40, "Rescue & Fleet Vehicles": 15, "Power & Energy": 8, "Shelter & Sanitation": 30},
            "Flood": {"Water & Rations": 50, "Rescue & Fleet Vehicles": 12, "Shelter & Sanitation": 25, "Medical & Trauma": 20},
            "Wildfire": {"HAZMAT & Firefighting": 30, "Specialized Personnel": 20, "Medical & Trauma": 15, "Rescue & Fleet Vehicles": 10},
            "Epidemic": {"Medical & Trauma": 100, "HAZMAT & Firefighting": 50, "Specialized Personnel": 25}
        }.get(scenario_type, {"Medical & Trauma": 30, "Water & Rations": 30})

        simulation_results = []
        total_shortfalls = 0

        for cat_name, base_demand in demands.items():
            req_qty = int(base_demand * severity_multiplier)
            
            # Sum available stock across all depots
            matching_resources = [r for r in resources if r.get("category_name") == cat_name]
            total_stock = sum(r.get("quantity", 0) for r in matching_resources)

            shortfall = max(0, req_qty - total_stock)
            if shortfall > 0:
                total_shortfalls += shortfall

            readiness_pct = min(100.0, round((total_stock / max(req_qty, 1)) * 100, 1))

            simulation_results.append({
                "category_name": cat_name,
                "projected_demand": req_qty,
                "current_stock": total_stock,
                "shortfall": shortfall,
                "readiness_pct": readiness_pct,
                "status": "PREPARED" if shortfall == 0 else ("CRITICAL SHORTAGE" if readiness_pct < 50 else "MODERATE DEFICIT")
            })

        overall_readiness = max(0.0, round(100.0 - (total_shortfalls * 2.0), 1))

        return {
            "scenario": scenario_type,
            "severity_multiplier": severity_multiplier,
            "overall_preparedness_index": overall_readiness,
            "breakdown": simulation_results,
            "recommendation": "System fully capable of absorbing scenario load." if overall_readiness > 80 else "Stock pre-positioning and emergency procurement required."
        }
