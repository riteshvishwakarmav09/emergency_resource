import os
import base64
import json
import hashlib
import hmac
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

class CryptoEngine:
    def __init__(self, key_dir="data"):
        os.makedirs(key_dir, exist_ok=True)
        self.key_file = os.path.join(key_dir, ".master_key.key")
        self.salt_file = os.path.join(key_dir, ".master_salt.salt")
        
        self.salt = self._get_or_create_salt()
        self.fernet = self._get_or_create_fernet()

    def _get_or_create_salt(self):
        if os.path.exists(self.salt_file):
            with open(self.salt_file, "rb") as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, "wb") as f:
                f.write(salt)
            return salt

    def _get_or_create_fernet(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            # Derive Fernet key using PBKDF2
            passphrase = b"EmergencyResourceAllocatorKeySecret2026!#"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000
            )
            key = base64.urlsafe_b64encode(kdf.derive(passphrase))
            with open(self.key_file, "wb") as f:
                f.write(key)
        return Fernet(key)

    def encrypt_str(self, text: str) -> str:
        """Encrypts a string and returns base64 encoded ciphertext string."""
        if text is None:
            return ""
        if isinstance(text, (dict, list)):
            text = json.dumps(text)
        encrypted_bytes = self.fernet.encrypt(text.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt_str(self, cipher_text: str) -> str:
        """Decrypts a base64 string back to plaintext."""
        if not cipher_text:
            return ""
        try:
            decrypted_bytes = self.fernet.decrypt(cipher_text.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            return f"[Decryption Failed: {str(e)}]"

    def encrypt_data_dict(self, data_dict: dict, sensitive_keys: list) -> dict:
        """Encrypts specific sensitive keys within a dictionary."""
        encrypted_dict = data_dict.copy()
        for key in sensitive_keys:
            if key in encrypted_dict and encrypted_dict[key] is not None:
                val = encrypted_dict[key]
                if not isinstance(val, str):
                    val = json.dumps(val)
                encrypted_dict[key] = self.encrypt_str(val)
        return encrypted_dict

    def decrypt_data_dict(self, encrypted_dict: dict, sensitive_keys: list) -> dict:
        """Decrypts specific sensitive keys within a dictionary."""
        decrypted_dict = encrypted_dict.copy()
        for key in sensitive_keys:
            if key in decrypted_dict and decrypted_dict[key] is not None:
                cipher = decrypted_dict[key]
                decrypted_dict[key] = self.decrypt_str(cipher)
        return decrypted_dict

    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple[str, str]:
        """Hashes a password with SHA256 and salt."""
        if salt is None:
            salt = os.urandom(16).hex()
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return pwd_hash, salt

    @staticmethod
    def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
        """Verifies password against stored hash."""
        pwd_hash, _ = CryptoEngine.hash_password(password, stored_salt)
        return hmac.compare_digest(pwd_hash, stored_hash)

    def generate_backup_signature(self, raw_bytes: bytes) -> str:
        """Generates HMAC-SHA256 signature for backup integrity check."""
        return hmac.new(self.salt, raw_bytes, hashlib.sha256).hexdigest()

    def verify_backup_signature(self, raw_bytes: bytes, signature: str) -> bool:
        """Verifies backup payload HMAC signature."""
        expected_sig = self.generate_backup_signature(raw_bytes)
        return hmac.compare_digest(expected_sig, signature)
