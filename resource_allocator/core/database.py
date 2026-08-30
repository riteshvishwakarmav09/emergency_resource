import os
import json
import time
from datetime import datetime
from core.crypto_engine import CryptoEngine

class Database:
    def __init__(self, data_dir="data", crypto_engine=None):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_file = os.path.join(self.data_dir, "encrypted_store.db")
        self.crypto = crypto_engine or CryptoEngine(key_dir=self.data_dir)
        self._initialize_db()

    def _initialize_db(self):
        if not os.path.exists(self.db_file):
            seed_data = self._generate_seed_data()
            self._write_db(seed_data)

    def _write_db(self, data: dict):
        with open(self.db_file, "w") as f:
            json.dump(data, f, indent=2)

    def _read_db(self) -> dict:
        if not os.path.exists(self.db_file):
            return self._generate_seed_data()
        try:
            with open(self.db_file, "r") as f:
                return json.load(f)
        except Exception:
            return self._generate_seed_data()

    def _generate_seed_data(self) -> dict:
        admin_pass, admin_salt = CryptoEngine.hash_password("admin123")
        disp_pass, disp_salt = CryptoEngine.hash_password("dispatcher123")
        field_pass, field_salt = CryptoEngine.hash_password("field123")

        users = [
            {
                "id": "USR-001",
                "username": "admin",
                "full_name": "Commander Sarah Vance",
                "role": "Admin",
                "password_hash": admin_pass,
                "salt": admin_salt
            },
            {
                "id": "USR-002",
                "username": "dispatcher",
                "full_name": "Ops Dispatcher Marcus Kane",
                "role": "Dispatcher",
                "password_hash": disp_pass,
                "salt": disp_salt
            },
            {
                "id": "USR-003",
                "username": "field",
                "full_name": "Field Captain Elena Rostova",
                "role": "Field Officer",
                "password_hash": field_pass,
                "salt": field_salt
            }
        ]

        categories = [
            {"id": "CAT-001", "name": "Medical & Trauma", "description": "Emergency surgery kits, blood plasma, ventilators, life support", "icon": "medkit", "priority_weight": 1.0},
            {"id": "CAT-002", "name": "Rescue & Fleet Vehicles", "description": "Ambulances, off-road rescue trucks, helicopters, motorized boats", "icon": "truck", "priority_weight": 0.9},
            {"id": "CAT-003", "name": "Power & Energy", "description": "High-output diesel generators, battery banks, solar arrays", "icon": "zap", "priority_weight": 0.85},
            {"id": "CAT-004", "name": "Water & Rations", "description": "Water purifiers, bottled water packs, field food rations", "icon": "droplet", "priority_weight": 0.8},
            {"id": "CAT-005", "name": "HAZMAT & Firefighting", "description": "Chemical suits, thermal detectors, foam sprayers", "icon": "flame", "priority_weight": 0.95},
            {"id": "CAT-006", "name": "Shelter & Sanitation", "description": "Inflatable triage tents, thermal blankets, portable sanitation", "icon": "home", "priority_weight": 0.7},
            {"id": "CAT-007", "name": "Specialized Personnel", "description": "Trauma surgeons, USAR search rescue units, K9 units", "icon": "users", "priority_weight": 0.95}
        ]

        depots = [
            {"id": "DEP-001", "name": "Central Command Depot Alpha", "sector": "North Sector", "lat": 34.0522, "lng": -118.2437, "contact": "Depot Admin A"},
            {"id": "DEP-002", "name": "Logistics Hub Bravo", "sector": "East Sector", "lat": 34.0812, "lng": -118.1500, "contact": "Depot Admin B"},
            {"id": "DEP-003", "name": "Coastal Response Station Charlie", "sector": "South Sector", "lat": 33.9500, "lng": -118.3900, "contact": "Depot Admin C"},
            {"id": "DEP-004", "name": "Mountain Operations Hub Delta", "sector": "West Sector", "lat": 34.1500, "lng": -118.4500, "contact": "Depot Admin D"}
        ]

        # Sensitive resources - certain fields will be stored encrypted at rest!
        resources_raw = [
            {
                "id": "RES-101",
                "name": "Mobile ICU Ventilators",
                "category_id": "CAT-001",
                "depot_id": "DEP-001",
                "quantity": 24,
                "min_reserve": 5,
                "unit": "Units",
                "status": "Available",
                "sensitive_specs": "High-pressure oxygen mix. Encryption Key #V109. Bio-hazard sealed.",
                "secure_location_code": "Vault-A-Locker-12"
            },
            {
                "id": "RES-102",
                "name": "Trauma Surgical Kits & Plasma",
                "category_id": "CAT-001",
                "depot_id": "DEP-002",
                "quantity": 150,
                "min_reserve": 30,
                "unit": "Kits",
                "status": "Available",
                "sensitive_specs": "Stored at -20C. Requires specialized cold-chain transport container.",
                "secure_location_code": "ColdRoom-B-04"
            },
            {
                "id": "RES-103",
                "name": "Heavy Off-Road Rescue Vehicles",
                "category_id": "CAT-002",
                "depot_id": "DEP-001",
                "quantity": 8,
                "min_reserve": 2,
                "unit": "Vehicles",
                "status": "Available",
                "sensitive_specs": "Winches: 15-Ton. Winch Codes: #9941. Fuel: Diesel Heavy.",
                "secure_location_code": "Garage-Bay-A1"
            },
            {
                "id": "RES-104",
                "name": "Air Transport Helicopter (MedEvac)",
                "category_id": "CAT-002",
                "depot_id": "DEP-004",
                "quantity": 3,
                "min_reserve": 1,
                "unit": "Aircraft",
                "status": "Available",
                "sensitive_specs": "Tail Numbers: N-401, N-402, N-405. Transponder code: 7700 ready.",
                "secure_location_code": "Hangar-Delta-1"
            },
            {
                "id": "RES-105",
                "name": "500kW Heavy Diesel Generators",
                "category_id": "CAT-003",
                "depot_id": "DEP-002",
                "quantity": 12,
                "min_reserve": 3,
                "unit": "Units",
                "status": "Available",
                "sensitive_specs": "High voltage output. Includes 400ft military-grade cabling.",
                "secure_location_code": "HeavyYard-B-09"
            },
            {
                "id": "RES-106",
                "name": "High-Volume Water Purification Skids",
                "category_id": "CAT-004",
                "depot_id": "DEP-003",
                "quantity": 18,
                "min_reserve": 4,
                "unit": "Systems",
                "status": "Available",
                "sensitive_specs": "10,000 Gallons/hour reverse osmosis. Chemical filter kit included.",
                "secure_location_code": "WaterDepot-C-02"
            },
            {
                "id": "RES-107",
                "name": "HAZMAT Chem-Bio Protection Suits",
                "category_id": "CAT-005",
                "depot_id": "DEP-001",
                "quantity": 300,
                "min_reserve": 50,
                "unit": "Suits",
                "status": "Available",
                "sensitive_specs": "Level-A Pressure suits with SCBA air tanks.",
                "secure_location_code": "HazmatBunker-A-01"
            },
            {
                "id": "RES-108",
                "name": "Rapid Deployment Field Triage Tents",
                "category_id": "CAT-006",
                "depot_id": "DEP-003",
                "quantity": 40,
                "min_reserve": 10,
                "unit": "Structures",
                "status": "Available",
                "sensitive_specs": "50-person capacity per tent with HVAC ports.",
                "secure_location_code": "ShelterRack-C-11"
            },
            {
                "id": "RES-109",
                "name": "Urban Search & Rescue (USAR) Alpha Team",
                "category_id": "CAT-007",
                "depot_id": "DEP-001",
                "quantity": 15,
                "min_reserve": 3,
                "unit": "Personnel",
                "status": "Available",
                "sensitive_specs": "Certified Structural Collapse & K9 Search Specialists.",
                "secure_location_code": "Barracks-Alpha-3"
            }
        ]

        # Encrypt sensitive fields on resources
        encrypted_resources = []
        for r in resources_raw:
            enc_r = self.crypto.encrypt_data_dict(r, ["sensitive_specs", "secure_location_code"])
            encrypted_resources.append(enc_r)

        incidents = [
            {
                "id": "INC-801",
                "title": "Magnitude 7.1 Earthquake - North Sector",
                "type": "Earthquake",
                "severity": "CRITICAL",
                "urgency_score": 9.5,
                "sector": "North Sector",
                "lat": 34.0700,
                "lng": -118.2500,
                "affected_population": 45000,
                "description": "Major structural collapse in urban zone. Municipal grid offline, local trauma center running on failing battery backup. High casualty risk.",
                "required_needs": [
                    {"category_id": "CAT-001", "quantity": 15, "name": "Mobile ICU Ventilators"},
                    {"category_id": "CAT-003", "quantity": 4, "name": "500kW Heavy Diesel Generators"},
                    {"category_id": "CAT-007", "quantity": 10, "name": "USAR Search Team"},
                    {"category_id": "CAT-006", "quantity": 15, "name": "Field Triage Tents"}
                ],
                "status": "ACTIVE",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "INC-802",
                "title": "Coastal Flash Flood & Drinking Water Contamination",
                "type": "Flood",
                "severity": "HIGH",
                "urgency_score": 8.2,
                "sector": "South Sector",
                "lat": 33.9300,
                "lng": -118.3800,
                "affected_population": 22000,
                "description": "Severe storm surge inundated water treatment plant. 22,000 residents without potable water. Floodwaters rising in low districts.",
                "required_needs": [
                    {"category_id": "CAT-004", "quantity": 12, "name": "Water Purification Skids"},
                    {"category_id": "CAT-002", "quantity": 4, "name": "Rescue Boats & Trucks"}
                ],
                "status": "ACTIVE",
                "created_at": datetime.now().isoformat()
            }
        ]

        dispatches = []

        return {
            "users": users,
            "categories": categories,
            "depots": depots,
            "resources": encrypted_resources,
            "incidents": incidents,
            "dispatches": dispatches
        }

    # User Auth Methods
    def get_user_by_username(self, username: str):
        db = self._read_db()
        for u in db.get("users", []):
            if u["username"].lower() == username.lower():
                return u
        return None

    # Category Management
    def get_categories(self):
        return self._read_db().get("categories", [])

    def add_category(self, category_data: dict):
        db = self._read_db()
        category_data["id"] = f"CAT-{int(time.time() * 1000)}"
        db.setdefault("categories", []).append(category_data)
        self._write_db(db)
        return category_data

    def update_category(self, cat_id: str, updated_data: dict):
        db = self._read_db()
        for i, c in enumerate(db.get("categories", [])):
            if c["id"] == cat_id:
                db["categories"][i].update(updated_data)
                self._write_db(db)
                return db["categories"][i]
        return None

    def delete_category(self, cat_id: str):
        db = self._read_db()
        db["categories"] = [c for c in db.get("categories", []) if c["id"] != cat_id]
        self._write_db(db)
        return True

    # Depots
    def get_depots(self):
        return self._read_db().get("depots", [])

    # Resource Management (Encrypted Storage & Retrieval)
    def get_resources(self, decrypt: bool = False, role: str = "Viewer"):
        db = self._read_db()
        resources = db.get("resources", [])
        categories = {c["id"]: c["name"] for c in db.get("categories", [])}
        depots = {d["id"]: d["name"] for d in db.get("depots", [])}

        processed = []
        for r in resources:
            item = r.copy()
            item["category_name"] = categories.get(r.get("category_id"), "Unassigned")
            item["depot_name"] = depots.get(r.get("depot_id"), "Unknown Depot")
            
            # Encrypted check: Decrypt ONLY if authorized and requested
            if decrypt and role in ["Admin", "Dispatcher"]:
                item = self.crypto.decrypt_data_dict(item, ["sensitive_specs", "secure_location_code"])
                item["is_decrypted"] = True
            else:
                item["is_decrypted"] = False
                # Mask sensitive fields when not decrypted
                if "sensitive_specs" in item:
                    item["sensitive_specs"] = "[ENCRYPTED AES-256 PAYLOAD]"
                if "secure_location_code" in item:
                    item["secure_location_code"] = "[ENCRYPTED LOCATION]"

            processed.append(item)
        return processed

    def add_resource(self, resource_data: dict):
        db = self._read_db()
        resource_data["id"] = f"RES-{int(time.time() * 1000)}"
        enc_resource = self.crypto.encrypt_data_dict(resource_data, ["sensitive_specs", "secure_location_code"])
        db.setdefault("resources", []).append(enc_resource)
        self._write_db(db)
        return resource_data

    def update_resource_quantity(self, res_id: str, delta: int):
        db = self._read_db()
        for r in db.get("resources", []):
            if r["id"] == res_id:
                r["quantity"] = max(0, r["quantity"] + delta)
                if r["quantity"] == 0:
                    r["status"] = "Depleted"
                elif r["quantity"] <= r.get("min_reserve", 0):
                    r["status"] = "Low Stock"
                else:
                    r["status"] = "Available"
                self._write_db(db)
                return r
        return None

    # Incidents
    def get_incidents(self):
        return self._read_db().get("incidents", [])

    def add_incident(self, incident_data: dict):
        db = self._read_db()
        incident_data["id"] = f"INC-{int(time.time() * 1000)}"
        incident_data["status"] = "ACTIVE"
        incident_data["created_at"] = datetime.now().isoformat()
        db.setdefault("incidents", []).append(incident_data)
        self._write_db(db)
        return incident_data

    # Dispatches
    def get_dispatches(self):
        return self._read_db().get("dispatches", [])

    def create_dispatch(self, dispatch_data: dict):
        db = self._read_db()
        dispatch_data["id"] = f"DSP-{int(time.time() * 1000)}"
        dispatch_data["dispatched_at"] = datetime.now().isoformat()
        dispatch_data["status"] = "EN_ROUTE"
        
        # Deduct quantity from inventory
        for res_id, qty in dispatch_data.get("allocated_items", {}).items():
            for r in db.get("resources", []):
                if r["id"] == res_id:
                    r["quantity"] = max(0, r["quantity"] - qty)
                    if r["quantity"] == 0:
                        r["status"] = "Depleted"
                    elif r["quantity"] <= r.get("min_reserve", 0):
                        r["status"] = "Low Stock"

        db.setdefault("dispatches", []).append(dispatch_data)
        self._write_db(db)
        return dispatch_data

    # Export Full State for Backup
    def export_full_db_state(self) -> dict:
        return self._read_db()

    # Restore Full State
    def restore_full_db_state(self, state_dict: dict):
        required_keys = ["users", "categories", "depots", "resources", "incidents"]
        for k in required_keys:
            if k not in state_dict:
                raise ValueError(f"Invalid backup payload: missing key '{k}'")
        self._write_db(state_dict)
        return True
