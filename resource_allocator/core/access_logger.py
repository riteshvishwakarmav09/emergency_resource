import os
import json
import time
from datetime import datetime

class AccessLogger:
    def __init__(self, data_dir="data", crypto_engine=None):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.log_file = os.path.join(self.data_dir, "access_audit.json")
        self.crypto_engine = crypto_engine
        self._ensure_log_file()

    def _ensure_log_file(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                json.dump([], f)

    def log_event(self, actor: str, role: str, action: str, resource: str, details: str = "", ip_address: str = "127.0.0.1", status: str = "SUCCESS"):
        """Logs an audited system access or operation event."""
        log_entry = {
            "id": f"LOG-{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "actor": actor,
            "role": role,
            "action": action,
            "resource": resource,
            "details": details,
            "ip_address": ip_address,
            "status": status
        }

        logs = self.get_logs(raw=True)
        logs.insert(0, log_entry) # Put newest logs first
        
        # Limit to 500 log records in file
        logs = logs[:500]

        with open(self.log_file, "w") as f:
            json.dump(logs, f, indent=2)

        return log_entry

    def get_logs(self, limit: int = 100, role_filter: str = None, action_filter: str = None, raw: bool = False):
        """Retrieves audit logs with optional filters."""
        if not os.path.exists(self.log_file):
            return []
            
        try:
            with open(self.log_file, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []

        if raw:
            return logs

        filtered = logs
        if role_filter:
            filtered = [l for l in filtered if l.get("role", "").lower() == role_filter.lower()]
        if action_filter:
            filtered = [l for l in filtered if l.get("action", "").lower() == action_filter.lower()]

        return filtered[:limit]
