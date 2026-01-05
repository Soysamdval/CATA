"""Utility: send a signed Paddle-like webhook to local /webhook/paddle for testing.
Usage:
  python send_paddle_test.py --job <job_id>
It generates a temporary RSA keypair and prints the public key; you can paste that into env var PADDLE_PUBLIC_KEY for local testing.
"""
import argparse
import requests
import json
import base64
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA1


def sign_payload(payload: dict, private_key_pem: bytes) -> str:
    items = sorted(payload.items())
    serialized = b""
    for k, v in items:
        if isinstance(v, (list, dict)):
            s = json.dumps(v, separators=(",", ":"), sort_keys=True)
        else:
            s = str(v)
        serialized += s.encode('utf-8')
    key = RSA.import_key(private_key_pem)
    signer = PKCS1_v1_5.new(key)
    digest = SHA1.new(serialized)
    signature = signer.sign(digest)
    return base64.b64encode(signature).decode('ascii')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--job', required=True)
    p.add_argument('--url', default='http://127.0.0.1:8000/webhook/paddle')
    args = p.parse_args()

    key = RSA.generate(1024)
    private_pem = key.export_key()
    public_pem = key.publickey().export_key()

    print('PUBLIC KEY (set this as PADDLE_PUBLIC_KEY for testing):')
    print(public_pem.decode('utf-8'))

    payload = {
        'alert_name': 'payment_succeeded',
        'passthrough': args.job,
        'amount': '15.00',
        'currency': 'USD'
    }
    sig = sign_payload(payload, private_pem)
    payload['p_signature'] = sig

    r = requests.post(args.url, data=payload)
    print('status', r.status_code)
    print(r.text)
