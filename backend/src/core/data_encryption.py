from typing import Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from base64 import b64encode, b64decode
import os
import json

class DataEncryption:
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption utilities with a key.
        If no key is provided, generates a new one.
        """
        if encryption_key:
            self.key = b64decode(encryption_key)
        else:
            self.key = Fernet.generate_key()
        
        self.fernet = Fernet(self.key)
        
        # For AES encryption
        self.backend = default_backend()
        self.padder = padding.PKCS7(128)

    def get_key(self) -> str:
        """Get the base64-encoded encryption key."""
        return b64encode(self.key).decode()

    def encrypt_text(self, text: str) -> str:
        """
        Encrypt a text string using Fernet (suitable for database fields).
        """
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt_text(self, encrypted_text: str) -> str:
        """
        Decrypt a Fernet-encrypted string.
        """
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception as e:
            raise ValueError("Failed to decrypt text") from e

    def encrypt_json(self, data: Any) -> str:
        """
        Encrypt a JSON-serializable object.
        """
        json_str = json.dumps(data)
        return self.encrypt_text(json_str)

    def decrypt_json(self, encrypted_data: str) -> Any:
        """
        Decrypt and deserialize a JSON object.
        """
        try:
            json_str = self.decrypt_text(encrypted_data)
            return json.loads(json_str)
        except Exception as e:
            raise ValueError("Failed to decrypt JSON data") from e

    def encrypt_file(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        Encrypt a file using AES-256-CBC.
        Returns the path to the encrypted file.
        """
        if not output_path:
            output_path = f"{file_path}.encrypted"

        # Generate a random IV
        iv = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        padder = self.padder.padder()

        with open(file_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
            # Write the IV at the beginning of the file
            f_out.write(iv)
            
            while True:
                chunk = f_in.read(64 * 1024)  # 64KB chunks
                if not chunk:
                    break
                
                # Pad the last chunk
                if len(chunk) % 16:
                    chunk = padder.update(chunk)
                    chunk += padder.finalize()
                
                # Encrypt and write
                encrypted_chunk = encryptor.update(chunk)
                f_out.write(encrypted_chunk)
            
            # Write the final block
            f_out.write(encryptor.finalize())

        return output_path

    def decrypt_file(self, encrypted_path: str, output_path: Optional[str] = None) -> str:
        """
        Decrypt an AES-encrypted file.
        Returns the path to the decrypted file.
        """
        if not output_path:
            output_path = encrypted_path.replace('.encrypted', '.decrypted')

        with open(encrypted_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
            # Read the IV from the beginning of the file
            iv = f_in.read(16)
            
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            unpadder = self.padder.unpadder()

            # Decrypt in chunks
            while True:
                chunk = f_in.read(64 * 1024 + 16)  # 64KB chunks + block size
                if not chunk:
                    break
                
                decrypted_chunk = decryptor.update(chunk)
                
                try:
                    # Try to unpad the last chunk
                    if not f_in.peek(1):
                        decrypted_chunk = unpadder.update(decrypted_chunk)
                        decrypted_chunk += unpadder.finalize()
                except ValueError:
                    pass
                
                f_out.write(decrypted_chunk)
            
            # Write the final block
            f_out.write(decryptor.finalize())

        return output_path

def setup_encryption(encryption_key: Optional[str] = None) -> DataEncryption:
    """
    Set up the encryption utilities with an optional key.
    If no key is provided, generates a new one.
    """
    return DataEncryption(encryption_key)