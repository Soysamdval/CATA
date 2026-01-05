import base64
import json
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA1
from fastapi.testclient import TestClient
import tempfile
import os

import db as db_module
from main import app

client = TestClient(app)


def sign_payload(payload: dict, private_key_pem: bytes) -> str:
    # Prepare serialization as main.py does: sorted items -> concatenate string values
    items = sorted(payload.items())
    serialized = b""
    for k, v in items:
        if isinstance(v, (list, dict)):
            s = json.dumps(v, separators=(",", ":"), sort_keys=True)
        else:
            s = str(v)
        serialized += s.encode("utf-8")

    key = RSA.import_key(private_key_pem)
    signer = PKCS1_v1_5.new(key)
    digest = SHA1.new(serialized)
    signature = signer.sign(digest)
    return base64.b64encode(signature).decode("ascii")


def test_paddle_webhook_marks_paid(tmp_path):
    # Prepare a temporary DB
    tmp_db = tmp_path / "test_cata.db"
    db_module.DB_PATH = str(tmp_db)
    db_module.init_db()

    # Generate RSA keypair
    key = RSA.generate(1024)
    private_pem = key.export_key()
    public_pem = key.publickey().export_key()

    # Monkeypatch PADDLE_PUBLIC_KEY in main module
    import main as main_module
    main_module.PADDLE_PUBLIC_KEY = public_pem.decode("utf-8")

    job_id = "test-job-123"

    payload = {
        "alert_name": "payment_succeeded",
        "passthrough": job_id,
        "amount": "15.00",
        "currency": "USD"
    }

    p_signature = sign_payload(payload, private_pem)
    payload["p_signature"] = p_signature

    # Send webhook
    r = client.post("/webhook/paddle", data=payload)
    # Debug if failing
    assert r.status_code == 200, f"Unexpected status {r.status_code}, body: {r.text}"
    # Check DB
    assert db_module.is_paid(job_id) is True


if __name__ == "__main__":
    test_paddle_webhook_marks_paid(tempfile.gettempdir())
