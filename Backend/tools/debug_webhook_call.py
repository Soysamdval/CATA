from fastapi.testclient import TestClient
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA1
import base64
import json
import main

client = TestClient(main.app)

key = RSA.generate(1024)
private_pem = key.export_key()
public_pem = key.publickey().export_key()
main.PADDLE_PUBLIC_KEY = public_pem.decode('utf-8')

job_id = 'debug-job-1'
payload = {'alert_name': 'payment_succeeded', 'passthrough': job_id, 'amount': '15.00', 'currency': 'USD'}

# sign
items = sorted(payload.items())
serialized = b''
for k, v in items:
    s = str(v)
    serialized += s.encode('utf-8')
key_obj = RSA.import_key(private_pem)
signer = PKCS1_v1_5.new(key_obj)
digest = SHA1.new(serialized)
sig = signer.sign(digest)
p_signature = base64.b64encode(sig).decode('ascii')
payload['p_signature'] = p_signature

resp = client.post('/webhook/paddle', data=payload)
print('status', resp.status_code)
print('body', resp.text)

# Check status endpoint
resp2 = client.get(f'/status?job={job_id}')
print('status endpoint', resp2.status_code, resp2.text)
