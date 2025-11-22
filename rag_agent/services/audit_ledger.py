import hashlib
import json
import asyncio
from datetime import datetime, timezone
from google.cloud import firestore
from google.cloud import kms

class AuditLedger:
    def __init__(self, project_id, location, key_ring, key_name, version="1"):
        self.db = firestore.Client(project=project_id)
        self.kms_client = kms.KeyManagementServiceClient()
        self.key_name = self.kms_client.crypto_key_version_path(
            project_id, location, key_ring, key_name, version
        )
        self.collection_name = "secure_audit_ledger"

    def _calculate_hash(self, data_string):
        return hashlib.sha256(data_string.encode()).hexdigest()

    def _sign_data(self, data_string):
        """Cryptographically signs the hash using Cloud KMS."""
        digest = {'sha256': hashlib.sha256(data_string.encode()).digest()}
        response = self.kms_client.asymmetric_sign(
            request={'name': self.key_name, 'digest': digest}
        )
        return response.signature.hex()

    async def _write_log_async(self, action: str, payload: dict, user_id: str):
        """
        Internal async method to perform the heavy lifting (DB read/write + Signing)
        without blocking the main agent thread.
        """
        try:
            # 1. Get the Last Hash (To create the chain)
            # In a real high-throughput system, you might cache this or use a distributed counter.
            query = self.db.collection(self.collection_name)\
                        .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                        .limit(1)
            docs = list(query.stream())
            
            prev_hash = "GENESIS_HASH" # Default for first entry
            if docs:
                prev_hash = docs[0].get("current_hash")

            # 2. Prepare Data Payload
            timestamp = datetime.now(timezone.utc).isoformat()
            log_entry = {
                "previous_hash": prev_hash,
                "timestamp": timestamp,
                "user_id": user_id,
                "action": action,
                "payload": payload
            }

            # 3. Create Canonical String for Hashing (Deterministic JSON)
            canonical_str = json.dumps(log_entry, sort_keys=True)

            # 4. Calculate Hash & Sign
            current_hash = self._calculate_hash(canonical_str)
            signature = self._sign_data(canonical_str)

            # 5. Final Document
            final_doc = {
                **log_entry,
                "current_hash": current_hash,
                "signature": signature
            }

            # 6. Write to Firestore
            self.db.collection(self.collection_name).add(final_doc)
            print(f"✅ Secure Log Written: {current_hash[:8]}...")

        except Exception as e:
            print(f"❌ Audit Log Failed: {e}")

    def log_action(self, action: str, payload: dict, user_id: str):
        """
        Public non-blocking method. Fires and forgets.
        """
        asyncio.create_task(self._write_log_async(action, payload, user_id))
