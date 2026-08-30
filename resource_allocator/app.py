import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, send_file, Response, redirect, url_for
from core.crypto_engine import CryptoEngine
from core.access_logger import AccessLogger
from core.database import Database
from core.decision_engine import DecisionEngine

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(24)

# Initialize Core Services
crypto_engine = CryptoEngine(key_dir="data")
access_logger = AccessLogger(data_dir="data", crypto_engine=crypto_engine)
db = Database(data_dir="data", crypto_engine=crypto_engine)
decision_engine = DecisionEngine(db=db)

# Helper for Session User & Audit Context
def get_current_user():
    if "user" in session:
        return session["user"]
    # Default fallback demo user if not logged in
    return {"username": "admin", "role": "Admin", "full_name": "Commander Sarah Vance"}

def log_audit(action: str, resource: str, details: str = "", status: str = "SUCCESS"):
    user = get_current_user()
    ip_addr = request.remote_addr or "127.0.0.1"
    access_logger.log_event(
        actor=user.get("username", "anonymous"),
        role=user.get("role", "Viewer"),
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_addr,
        status=status
    )

# --- WEB APPLICATION ROUTES ---
@app.route("/")
def index():
    user = get_current_user()
    return render_template("index.html", user=user)

# --- AUTHENTICATION API ---
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    user = db.get_user_by_username(username)
    if not user:
        log_audit("AUTH_LOGIN_FAILED", f"User: {username}", "Invalid username", status="FAILURE")
        return jsonify({"error": "Invalid username or password"}), 401

    if not CryptoEngine.verify_password(password, user["password_hash"], user["salt"]):
        log_audit("AUTH_LOGIN_FAILED", f"User: {username}", "Invalid password", status="FAILURE")
        return jsonify({"error": "Invalid username or password"}), 401

    user_info = {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"]
    }
    session["user"] = user_info
    log_audit("AUTH_LOGIN_SUCCESS", f"User: {username}", f"Role: {user['role']} session established")
    return jsonify({"message": "Login successful", "user": user_info})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    user = get_current_user()
    log_audit("AUTH_LOGOUT", f"User: {user.get('username')}", "User logged out")
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route("/api/auth/me", methods=["GET"])
def me():
    return jsonify({"user": get_current_user()})

# --- CATEGORY MANAGEMENT API ---
@app.route("/api/categories", methods=["GET"])
def get_categories():
    categories = db.get_categories()
    return jsonify({"categories": categories})

@app.route("/api/categories", methods=["POST"])
def add_category():
    user = get_current_user()
    if user.get("role") not in ["Admin", "Dispatcher"]:
        return jsonify({"error": "Unauthorized permission level"}), 403

    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Category name required"}), 400

    new_cat = db.add_category({
        "name": name,
        "description": data.get("description", ""),
        "icon": data.get("icon", "box"),
        "priority_weight": float(data.get("priority_weight", 1.0))
    })

    log_audit("CATEGORY_CREATE", f"Category: {new_cat['id']}", f"Name: {name}")
    return jsonify({"message": "Category created", "category": new_cat})

@app.route("/api/categories/<cat_id>", methods=["PUT"])
def update_category(cat_id):
    user = get_current_user()
    if user.get("role") not in ["Admin", "Dispatcher"]:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    updated = db.update_category(cat_id, data)
    if not updated:
        return jsonify({"error": "Category not found"}), 404

    log_audit("CATEGORY_UPDATE", f"Category: {cat_id}", f"Updated attributes")
    return jsonify({"message": "Category updated", "category": updated})

@app.route("/api/categories/<cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    user = get_current_user()
    if user.get("role") != "Admin":
        return jsonify({"error": "Admin permission required to delete categories"}), 403

    db.delete_category(cat_id)
    log_audit("CATEGORY_DELETE", f"Category: {cat_id}", "Category removed")
    return jsonify({"message": "Category deleted"})

# --- ENCRYPTED RESOURCE VAULT API ---
@app.route("/api/resources", methods=["GET"])
def get_resources():
    user = get_current_user()
    decrypt_param = request.args.get("decrypt", "false").lower() == "true"
    
    # Secure Retrieval Enforcement: Only decrypt if explicitly requested & user has proper role
    resources = db.get_resources(decrypt=decrypt_param, role=user.get("role"))

    if decrypt_param and user.get("role") in ["Admin", "Dispatcher"]:
        log_audit("SECURE_RETRIEVAL_DECRYPT", "Resource Vault", "Decrypted sensitive specifications and locker codes")
    else:
        log_audit("SECURE_RETRIEVAL_ENCRYPTED", "Resource Vault", "Retrieved encrypted resource list")

    return jsonify({"resources": resources, "decrypted": decrypt_param and user.get("role") in ["Admin", "Dispatcher"]})

@app.route("/api/resources", methods=["POST"])
def add_resource():
    user = get_current_user()
    if user.get("role") not in ["Admin", "Dispatcher"]:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    res = db.add_resource({
        "name": data.get("name"),
        "category_id": data.get("category_id"),
        "depot_id": data.get("depot_id", "DEP-001"),
        "quantity": int(data.get("quantity", 0)),
        "min_reserve": int(data.get("min_reserve", 5)),
        "unit": data.get("unit", "Units"),
        "status": "Available",
        "sensitive_specs": data.get("sensitive_specs", "Standard Emergency Payload"),
        "secure_location_code": data.get("secure_location_code", "Vault-Primary")
    })

    log_audit("RESOURCE_CREATE_ENCRYPTED", f"Resource: {res['id']}", f"Encrypted and stored: {data.get('name')}")
    return jsonify({"message": "Resource created with AES-256 encryption", "resource": res})

# --- INCIDENTS & CRISIS DATA ---
@app.route("/api/incidents", methods=["GET"])
def get_incidents():
    incidents = db.get_incidents()
    depots = db.get_depots()
    return jsonify({"incidents": incidents, "depots": depots})

@app.route("/api/incidents", methods=["POST"])
def add_incident():
    user = get_current_user()
    if user.get("role") not in ["Admin", "Dispatcher"]:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    incident = db.add_incident({
        "title": data.get("title"),
        "type": data.get("type", "Disaster"),
        "severity": data.get("severity", "HIGH"),
        "urgency_score": float(data.get("urgency_score", 8.0)),
        "sector": data.get("sector", "North Sector"),
        "lat": float(data.get("lat", 34.05)),
        "lng": float(data.get("lng", -118.25)),
        "affected_population": int(data.get("affected_population", 1000)),
        "description": data.get("description", ""),
        "required_needs": data.get("required_needs", [])
    })

    log_audit("INCIDENT_DECLARED", f"Incident: {incident['id']}", f"Title: {incident['title']} [{incident['severity']}]")
    return jsonify({"message": "Emergency Incident Declared", "incident": incident})

# --- INTELLIGENT DECISION SUPPORT & RECOMMENDATIONS API ---
@app.route("/api/recommendations/<incident_id>", methods=["GET"])
def get_recommendations(incident_id):
    user = get_current_user()
    plan = decision_engine.analyze_incident_recommendations(incident_id, role=user.get("role"))
    
    log_audit("RECOMMENDATION_GENERATE", f"Incident: {incident_id}", 
              f"Calculated readiness score: {plan.get('readiness_impact_score')}%")
    return jsonify(plan)

@app.route("/api/recommendations/approve", methods=["POST"])
def approve_recommendation():
    user = get_current_user()
    if user.get("role") not in ["Admin", "Dispatcher"]:
        return jsonify({"error": "Unauthorized dispatcher role required to approve dispatches"}), 403

    data = request.json or {}
    incident_id = data.get("incident_id")
    allocations = data.get("allocations", [])

    if not allocations:
        return jsonify({"error": "No allocation payload provided"}), 400

    allocated_items = {}
    dispatch_details = []

    for item in allocations:
        res_id = item.get("resource_id")
        qty = item.get("quantity", 0)
        allocated_items[res_id] = qty
        dispatch_details.append(f"{qty}x {item.get('resource_name')} from {item.get('depot_name')}")

    dispatch_record = db.create_dispatch({
        "incident_id": incident_id,
        "approved_by": user.get("full_name"),
        "allocated_items": allocated_items,
        "details": dispatch_details
    })

    log_audit("DISPATCH_APPROVED_EXECUTE", f"Dispatch: {dispatch_record['id']}", 
              f"Incident: {incident_id} | Allocated: {', '.join(dispatch_details)}")

    return jsonify({"message": "Emergency Dispatch Plan Approved & Deployed", "dispatch": dispatch_record})

@app.route("/api/simulate", methods=["POST"])
def run_simulation():
    data = request.json or {}
    scenario = data.get("scenario", "Earthquake")
    severity = float(data.get("severity", 1.5))

    results = decision_engine.run_scenario_simulation(scenario, severity)
    log_audit("SCENARIO_SIMULATION_RUN", f"Scenario: {scenario}", f"Preparedness Index: {results['overall_preparedness_index']}%")
    return jsonify(results)

@app.route("/api/rebalance", methods=["GET"])
def get_rebalance_suggestions():
    suggestions = decision_engine.suggest_stock_rebalancing()
    return jsonify({"suggestions": suggestions})

# --- AUDIT LOGS API ---
@app.route("/api/logs", methods=["GET"])
def get_audit_logs():
    user = get_current_user()
    if user.get("role") not in ["Admin", "Dispatcher"]:
        return jsonify({"error": "Admin or Dispatcher role required"}), 403

    role_filter = request.args.get("role")
    action_filter = request.args.get("action")
    logs = access_logger.get_logs(limit=200, role_filter=role_filter, action_filter=action_filter)
    return jsonify({"logs": logs})

@app.route("/api/logs/export", methods=["GET"])
def export_audit_logs():
    user = get_current_user()
    if user.get("role") != "Admin":
        return jsonify({"error": "Admin access required to export raw audit logs"}), 403

    logs = access_logger.get_logs(limit=500, raw=True)
    log_audit("AUDIT_LOG_EXPORTED", "Audit System", f"Exported {len(logs)} log records")

    json_data = json.dumps(logs, indent=2)
    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename=emergency_audit_logs_{int(time.time())}.json"}
    )

# --- BACKUP & RESTORE API ---
@app.route("/api/backups/create", methods=["POST"])
def create_backup():
    user = get_current_user()
    if user.get("role") != "Admin":
        return jsonify({"error": "Admin authorization required for backup creation"}), 403

    state = db.export_full_db_state()
    state_bytes = json.dumps(state).encode('utf-8')

    # Encrypt the backup payload using Fernet
    encrypted_backup = crypto_engine.encrypt_str(json.dumps(state))
    signature = crypto_engine.generate_backup_signature(encrypted_backup.encode('utf-8'))

    backup_payload = {
        "timestamp": datetime.now().isoformat(),
        "created_by": user.get("username"),
        "signature_hmac": signature,
        "encrypted_data": encrypted_backup
    }

    os.makedirs("data/backups", exist_ok=True)
    filename = f"backup_{int(time.time())}.bak"
    filepath = os.path.join("data/backups", filename)

    with open(filepath, "w") as f:
        json.dump(backup_payload, f, indent=2)

    log_audit("BACKUP_CREATED_ENCRYPTED", f"File: {filename}", "Created AES-256 encrypted database snapshot with HMAC verification")
    return jsonify({"message": "Encrypted backup created successfully", "filename": filename})

@app.route("/api/backups", methods=["GET"])
def list_backups():
    user = get_current_user()
    if user.get("role") != "Admin":
        return jsonify({"error": "Admin access required"}), 403

    backup_dir = "data/backups"
    if not os.path.exists(backup_dir):
        return jsonify({"backups": []})

    backups = []
    for fname in os.listdir(backup_dir):
        if fname.endswith(".bak"):
            fpath = os.path.join(backup_dir, fname)
            size = os.path.getsize(fpath)
            ctime = os.path.getctime(fpath)
            backups.append({
                "filename": fname,
                "size_bytes": size,
                "created_at": datetime.fromtimestamp(ctime).isoformat()
            })

    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify({"backups": backups})

@app.route("/api/backups/download/<filename>", methods=["GET"])
def download_backup(filename):
    user = get_current_user()
    if user.get("role") != "Admin":
        return jsonify({"error": "Admin access required"}), 403

    fpath = os.path.join("data/backups", filename)
    if not os.path.exists(fpath):
        return jsonify({"error": "Backup file not found"}), 404

    log_audit("BACKUP_DOWNLOADED", f"File: {filename}", "Backup file downloaded")
    return send_file(fpath, as_attachment=True)

@app.route("/api/backups/restore", methods=["POST"])
def restore_backup():
    user = get_current_user()
    if user.get("role") != "Admin":
        return jsonify({"error": "Admin authorization required for backup restore"}), 403

    if 'file' not in request.files:
        return jsonify({"error": "No backup file uploaded"}), 400

    file = request.files['file']
    try:
        payload = json.load(file.stream)
        sig = payload.get("signature_hmac")
        enc_data = payload.get("encrypted_data")

        # Verify HMAC signature integrity
        if not crypto_engine.verify_backup_signature(enc_data.encode('utf-8'), sig):
            log_audit("BACKUP_RESTORE_FAILED", "Backup Engine", "HMAC Signature mismatch! File corrupted or tampered.", status="FAILURE")
            return jsonify({"error": "Backup integrity verification failed (HMAC Mismatch). File may be tampered."}), 400

        # Decrypt payload
        decrypted_json = crypto_engine.decrypt_str(enc_data)
        state_dict = json.loads(decrypted_json)

        db.restore_full_db_state(state_dict)
        log_audit("BACKUP_RESTORE_SUCCESS", "Backup Engine", "System state successfully restored from encrypted snapshot")
        return jsonify({"message": "System state successfully restored from backup snapshot!"})
    except Exception as e:
        log_audit("BACKUP_RESTORE_ERROR", "Backup Engine", str(e), status="FAILURE")
        return jsonify({"error": f"Failed to restore backup: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
