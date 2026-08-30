import unittest
import os
import shutil
import json
from core.crypto_engine import CryptoEngine
from core.access_logger import AccessLogger
from core.database import Database
from core.decision_engine import DecisionEngine

class TestEmergencyResourceAllocator(unittest.TestCase):
    def setUp(self):
        self.test_dir = "data_test_temp"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)

        self.crypto = CryptoEngine(key_dir=self.test_dir)
        self.logger = AccessLogger(data_dir=self.test_dir, crypto_engine=self.crypto)
        self.db = Database(data_dir=self.test_dir, crypto_engine=self.crypto)
        self.decision = DecisionEngine(db=self.db)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_crypto_engine(self):
        secret_text = "Sensitive Medical Payload Locker #99"
        encrypted = self.crypto.encrypt_str(secret_text)
        self.assertNotEqual(secret_text, encrypted)
        
        decrypted = self.crypto.decrypt_str(encrypted)
        self.assertEqual(secret_text, decrypted)

        pwd = "securepassword123"
        pwd_hash, salt = CryptoEngine.hash_password(pwd)
        self.assertTrue(CryptoEngine.verify_password(pwd, pwd_hash, salt))
        self.assertFalse(CryptoEngine.verify_password("wrongpass", pwd_hash, salt))

    def test_access_logger(self):
        log_entry = self.logger.log_event("admin", "Admin", "TEST_ACTION", "Resource-1", "Unit test detail")
        self.assertEqual(log_entry["actor"], "admin")

        logs = self.logger.get_logs(role_filter="Admin")
        self.assertGreaterEqual(len(logs), 1)

    def test_database_and_encryption(self):
        resources_encrypted = self.db.get_resources(decrypt=False)
        self.assertGreater(len(resources_encrypted), 0)
        first = resources_encrypted[0]
        self.assertIn("ENCRYPTED", first["sensitive_specs"])

        resources_decrypted = self.db.get_resources(decrypt=True, role="Admin")
        first_dec = resources_decrypted[0]
        self.assertNotIn("ENCRYPTED", first_dec["sensitive_specs"])

    def test_decision_engine(self):
        incidents = self.db.get_incidents()
        self.assertGreater(len(incidents), 0)
        inc_id = incidents[0]["id"]

        plan = self.decision.analyze_incident_recommendations(inc_id, role="Dispatcher")
        self.assertIn("readiness_impact_score", plan)
        self.assertIn("allocated_summary", plan)

    def test_simulation(self):
        sim = self.decision.run_scenario_simulation("Earthquake", 2.0)
        self.assertIn("overall_preparedness_index", sim)
        self.assertEqual(sim["scenario"], "Earthquake")

if __name__ == "__main__":
    unittest.main()
