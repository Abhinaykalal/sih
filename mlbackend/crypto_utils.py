import os
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519

def get_private_key() -> ed25519.Ed25519PrivateKey:
    hex_key = os.environ.get("MODEL_SIGNING_PRIVATE_KEY")
    if not hex_key:
        raise ValueError("CRITICAL: MODEL_SIGNING_PRIVATE_KEY environment variable is missing. Cannot sign artifact in CI/CD.")
    return ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hex_key))

def get_public_key(key_id: str) -> ed25519.Ed25519PublicKey:
    keys_json = os.environ.get("MODEL_VERIFICATION_PUBLIC_KEYS")
    if not keys_json:
        raise ValueError("CRITICAL: MODEL_VERIFICATION_PUBLIC_KEYS is missing. Cannot verify artifacts.")
    
    try:
        keys_map = json.loads(keys_json)
    except json.JSONDecodeError:
        raise ValueError("CRITICAL: MODEL_VERIFICATION_PUBLIC_KEYS must be a valid JSON map.")
        
    hex_pub = keys_map.get(key_id)
    if not hex_pub:
        raise ValueError(f"CRITICAL: key_id '{key_id}' is not in the pinned verification keys.")
        
    return ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_pub))

def sign_metadata(metadata: dict, key_id: str = "v1") -> dict:
    """Canonicalize JSON and sign with Ed25519 private key. Returns the signature envelope."""
    canonical_json = json.dumps(metadata, separators=(',', ':'), sort_keys=True).encode('utf-8')
    private_key = get_private_key()
    signature = private_key.sign(canonical_json)
    return {
        "key_id": key_id,
        "signature_b64": base64.b64encode(signature).decode('utf-8')
    }

def verify_metadata(metadata: dict, signature_envelope: dict) -> bool:
    """Verify the signature of the canonical JSON payload against the pinned public key."""
    try:
        canonical_json = json.dumps(metadata, separators=(',', ':'), sort_keys=True).encode('utf-8')
        signature = base64.b64decode(signature_envelope["signature_b64"])
        public_key = get_public_key(signature_envelope["key_id"])
        public_key.verify(signature, canonical_json)
        return True
    except Exception:
        return False
