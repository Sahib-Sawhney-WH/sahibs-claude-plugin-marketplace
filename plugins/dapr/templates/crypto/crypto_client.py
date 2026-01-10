"""
DAPR Cryptography Client Template
Building Block: Cryptography

Features:
- Encrypt/decrypt data without exposing keys
- Support for Azure Key Vault and local storage
- Stream encryption for large files
- Key wrapping algorithms
"""
import asyncio
import base64
import logging
from typing import Optional, Union

from dapr.clients import DaprClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crypto store name (from component YAML)
CRYPTO_STORE_NAME = "{{CRYPTO_STORE_NAME}}"


class CryptoClient:
    """
    Client for DAPR Cryptography building block.

    Provides encryption/decryption without exposing keys to the application.
    """

    def __init__(
        self,
        store_name: str = CRYPTO_STORE_NAME,
        key_name: Optional[str] = None
    ):
        """
        Initialize crypto client.

        Args:
            store_name: DAPR crypto store component name
            key_name: Default key name for operations
        """
        self.store_name = store_name
        self.key_name = key_name

    async def encrypt(
        self,
        plaintext: Union[str, bytes],
        key_name: Optional[str] = None,
        algorithm: str = "RSA-OAEP-256"
    ) -> bytes:
        """
        Encrypt data using the specified key.

        Args:
            plaintext: Data to encrypt (string or bytes)
            key_name: Key to use (defaults to client's key_name)
            algorithm: Key wrap algorithm (RSA-OAEP-256, A256KW, etc.)

        Returns:
            Encrypted bytes

        Example:
            encrypted = await client.encrypt("sensitive data")
        """
        key = key_name or self.key_name
        if not key:
            raise ValueError("Key name required for encryption")

        # Convert string to bytes
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        async with DaprClient() as client:
            result = await client.encrypt(
                data=plaintext,
                options={
                    "component_name": self.store_name,
                    "key_name": key,
                    "key_wrap_algorithm": algorithm,
                }
            )

            logger.debug(f"Encrypted {len(plaintext)} bytes with key: {key}")
            return result.payload

    async def decrypt(
        self,
        ciphertext: bytes,
        key_name: Optional[str] = None
    ) -> bytes:
        """
        Decrypt data.

        Args:
            ciphertext: Encrypted data
            key_name: Key to use for decryption

        Returns:
            Decrypted bytes

        Example:
            decrypted = await client.decrypt(encrypted_data)
            text = decrypted.decode("utf-8")
        """
        key = key_name or self.key_name

        async with DaprClient() as client:
            result = await client.decrypt(
                data=ciphertext,
                options={
                    "component_name": self.store_name,
                    "key_name": key if key else None,
                }
            )

            logger.debug(f"Decrypted {len(result.payload)} bytes")
            return result.payload

    async def encrypt_string(
        self,
        text: str,
        key_name: Optional[str] = None
    ) -> str:
        """
        Encrypt a string and return base64-encoded result.

        Args:
            text: String to encrypt
            key_name: Key to use

        Returns:
            Base64-encoded encrypted string

        Example:
            encrypted = await client.encrypt_string("my secret")
        """
        encrypted = await self.encrypt(text, key_name)
        return base64.b64encode(encrypted).decode("utf-8")

    async def decrypt_string(
        self,
        encrypted_base64: str,
        key_name: Optional[str] = None
    ) -> str:
        """
        Decrypt a base64-encoded encrypted string.

        Args:
            encrypted_base64: Base64-encoded encrypted data
            key_name: Key to use

        Returns:
            Decrypted string

        Example:
            text = await client.decrypt_string(encrypted)
        """
        ciphertext = base64.b64decode(encrypted_base64)
        decrypted = await self.decrypt(ciphertext, key_name)
        return decrypted.decode("utf-8")

    async def encrypt_file(
        self,
        input_path: str,
        output_path: str,
        key_name: Optional[str] = None,
        chunk_size: int = 64 * 1024  # 64KB chunks
    ) -> None:
        """
        Encrypt a file using streaming.

        Args:
            input_path: Path to plaintext file
            output_path: Path for encrypted output
            key_name: Key to use
            chunk_size: Size of chunks to process
        """
        key = key_name or self.key_name
        if not key:
            raise ValueError("Key name required for encryption")

        async with DaprClient() as client:
            with open(input_path, "rb") as infile:
                with open(output_path, "wb") as outfile:
                    while True:
                        chunk = infile.read(chunk_size)
                        if not chunk:
                            break

                        result = await client.encrypt(
                            data=chunk,
                            options={
                                "component_name": self.store_name,
                                "key_name": key,
                                "key_wrap_algorithm": "RSA-OAEP-256",
                            }
                        )
                        outfile.write(result.payload)

        logger.info(f"Encrypted file: {input_path} -> {output_path}")


# =============================================================================
# Helper Functions
# =============================================================================

async def encrypt_sensitive_field(
    data: dict,
    field: str,
    key_name: str,
    store_name: str = CRYPTO_STORE_NAME
) -> dict:
    """
    Encrypt a specific field in a dictionary.

    Args:
        data: Dictionary containing the field
        field: Field name to encrypt
        key_name: Encryption key name
        store_name: Crypto store name

    Returns:
        Dictionary with encrypted field

    Example:
        user = {"name": "John", "ssn": "123-45-6789"}
        encrypted_user = await encrypt_sensitive_field(user, "ssn", "pii-key")
    """
    if field not in data:
        return data

    client = CryptoClient(store_name=store_name, key_name=key_name)
    encrypted_value = await client.encrypt_string(str(data[field]))

    result = data.copy()
    result[field] = encrypted_value
    result[f"{field}_encrypted"] = True

    return result


# =============================================================================
# FastAPI Integration Example
# =============================================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Cryptography Service")
crypto = CryptoClient(key_name="app-encryption-key")


class EncryptRequest(BaseModel):
    plaintext: str


class DecryptRequest(BaseModel):
    ciphertext: str  # Base64 encoded


@app.post("/encrypt")
async def encrypt_data(request: EncryptRequest):
    """Encrypt sensitive data."""
    try:
        encrypted = await crypto.encrypt_string(request.plaintext)
        return {"encrypted": encrypted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decrypt")
async def decrypt_data(request: DecryptRequest):
    """Decrypt encrypted data."""
    try:
        decrypted = await crypto.decrypt_string(request.ciphertext)
        return {"decrypted": decrypted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UserData(BaseModel):
    name: str
    email: str
    ssn: str  # Sensitive field


@app.post("/users")
async def create_user(user: UserData):
    """Create user with encrypted SSN."""
    user_dict = user.model_dump()

    # Encrypt sensitive field before storing
    encrypted_user = await encrypt_sensitive_field(
        user_dict,
        field="ssn",
        key_name="pii-encryption-key"
    )

    # Store encrypted_user in database
    logger.info(f"Stored user with encrypted SSN: {encrypted_user['name']}")

    return {"status": "created", "ssn_encrypted": True}


# =============================================================================
# CLI Usage Example
# =============================================================================

if __name__ == "__main__":
    async def main():
        client = CryptoClient(key_name="my-encryption-key")

        # Encrypt and decrypt string
        original = "This is sensitive data!"
        encrypted = await client.encrypt_string(original)
        print(f"Encrypted: {encrypted[:50]}...")

        decrypted = await client.decrypt_string(encrypted)
        print(f"Decrypted: {decrypted}")

        assert original == decrypted
        print("Encryption/decryption successful!")

    asyncio.run(main())
