# ==========================================
# CATA — Backend principal
# ==========================================

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import os
SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000")

import uuid
import shutil
import json
import base64
import time
import requests
from Crypto.Hash import SHA1
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import logging
from fastapi import HTTPException

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("cata")

from cata_pdf import generate_cata
from db import init_db, mark_paid, is_paid

PADDLE_VENDOR_ID = os.environ.get("PADDLE_VENDOR_ID")
PADDLE_VENDOR_AUTH_CODE = os.environ.get("PADDLE_VENDOR_AUTH_CODE")
PADDLE_PUBLIC_KEY = os.environ.get("PADDLE_PUBLIC_KEY")  # PEM contents or path

# ---------- CONFIG ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(BASE_DIR, "tmp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Inicializar DB (SQLite)
init_db()

# ---------- APP ----------
app = FastAPI(title="CATA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego lo cerramos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- STATIC FILES ----------
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# ---------- SERVIR FRONTEND (opcional para despliegue simple) ----------
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "Frontend"))
if os.path.exists(FRONTEND_DIR):
    # Servimos el frontend bajo /Frontend para evitar conflictos con las rutas de la API
    app.mount("/Frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

    # Ruta raíz que redirige a la SPA (index)
    @app.get("/")
    def root_redirect():
        return RedirectResponse(url="/Frontend/index.html")

# ==========================================
# ENDPOINT: GENERAR CATÁLOGO (PREVIEW)
# ==========================================

@app.post("/generate")
async def generate_catalog(
    csv: UploadFile = File(...),
    logo: UploadFile = File(...),
    whatsapp: str = Form(...)
):
    job_id = str(uuid.uuid4())

    csv_path = os.path.join(TMP_DIR, f"{job_id}.csv")
    logo_path = os.path.join(TMP_DIR, f"{job_id}_logo.png")

    pdf_watermark = os.path.join(
        OUTPUT_DIR, f"CATA_{job_id}_watermark.pdf"
    )

    # Validación básica de tipos y tamaños
    MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB
    MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB

    def _save_upload_file_limited(upload_file, dest_path, max_bytes):
        total = 0
        with open(dest_path, "wb") as out:
            chunk = upload_file.file.read(65536)
            while chunk:
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail=f"Uploaded file exceeds size limit of {max_bytes} bytes")
                out.write(chunk)
                chunk = upload_file.file.read(65536)
        # Reset pointer for future reads if necessary
        try:
            upload_file.file.seek(0)
        except Exception:
            pass

    try:
        # ---------- GUARDAR ARCHIVOS ----------
        if csv.content_type not in ("text/csv", "application/vnd.ms-excel", "text/plain"):
            logger.warning("CSV content_type unexpected: %s", csv.content_type)
        _save_upload_file_limited(csv, csv_path, MAX_CSV_BYTES)

        if logo.content_type not in ("image/png", "image/jpeg"):
            raise HTTPException(status_code=400, detail="Logo must be PNG or JPEG")
        _save_upload_file_limited(logo, logo_path, MAX_LOGO_BYTES)

        # ---------- GENERAR PDF (CON MARCA DE AGUA) ----------
        logger.info("Generating watermark PDF for job %s", job_id)
        generate_cata(
            csv_path=csv_path,
            logo_path=logo_path,
            whatsapp=whatsapp,
            output_path=pdf_watermark,
            watermark=True  # 🔥 CLAVE PARA MODELO DE NEGOCIO
        )

        # ---------- GENERAR PDF LIMPIO (SIN MARCA) ----------
        pdf_clean = os.path.join(OUTPUT_DIR, f"CATA_{job_id}.pdf")
        logger.info("Generating clean PDF for job %s", job_id)
        generate_cata(
            csv_path=csv_path,
            logo_path=logo_path,
            whatsapp=whatsapp,
            output_path=pdf_clean,
            watermark=False
        )

        # ---------- RESPUESTA (NO DESCARGA) ----------
        return JSONResponse({
            "job_id": job_id,
            "pdf_preview": f"/download/{job_id}?watermark=1",
            "pdf_clean": f"/download/{job_id}?watermark=0",
            "preview_url": f"/Frontend/preview.html?job={job_id}"
        })

    except HTTPException as he:
        logger.warning("Request rejected: %s", he.detail)
        raise
    except Exception as e:
        logger.exception("Error generating cata for job %s: %s", job_id, e)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    finally:
        # Limpieza de archivos temporales
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
            if os.path.exists(logo_path):
                os.remove(logo_path)
        except Exception:
            logger.exception("Error cleaning temp files for job %s", job_id)


@app.get("/download/{job_id}")
def download(job_id: str, watermark: int = 1):
    """Descarga el PDF correspondiente. Usa watermark=1 para la versión con marca y watermark=0 para la versión limpia.
    Esta ruta fuerza descarga mediante Content-Disposition: attachment.
    """
    fname = f"CATA_{job_id}_watermark.pdf" if int(watermark) == 1 else f"CATA_{job_id}.pdf"
    path = os.path.join(OUTPUT_DIR, fname)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "file not found"})
    return FileResponse(path, media_type="application/pdf", filename=fname)


@app.get("/preview/{job_id}")
def preview_pdf(job_id: str):
    """Devuelve el PDF de previsualización con Content-Disposition inline para que el navegador lo muestre en un iframe en lugar de descargarlo automáticamente."""
    fname = f"CATA_{job_id}_watermark.pdf"
    path = os.path.join(OUTPUT_DIR, fname)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "file not found"})
    headers = {"Content-Disposition": f"inline; filename=\"{fname}\""}
    return FileResponse(path, media_type="application/pdf", headers=headers)


@app.get("/checkout")
def checkout(job: str):
    """Genera un Pay Link de Paddle para el `job` y devuelve la URL de pago."""
    if not (PADDLE_VENDOR_ID and PADDLE_VENDOR_AUTH_CODE):
        return JSONResponse(status_code=500, content={"error": "Paddle not configured"})

    payload = {
        "vendor_id": PADDLE_VENDOR_ID,
        "vendor_auth_code": PADDLE_VENDOR_AUTH_CODE,
        "title": "CATA — Sin marca de agua",
        "prices": ["USD:15.00"],
        "return_url": f"{SITE_URL}/Frontend/paid.html?job={job}",
        "passthrough": job
    }

    try:
        r = requests.post("https://vendors.paddle.com/api/2.0/product/generate_pay_link", data=payload, timeout=10)
        r.raise_for_status()
        resp = r.json()
        if not resp.get("success"):
            return JSONResponse(status_code=500, content={"error": "paddle error", "details": resp})
        url = resp["response"]["url"]
        return JSONResponse({"url": url})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


from fastapi import Request


@app.post("/webhook/paddle")
async def paddle_webhook(request: Request):
    """Webhook endpoint para recibir eventos de Paddle y marcar `job` como pagado cuando corresponda.
    Verifica la firma p_signature usando la clave pública de Paddle.
    """
    form = await request.form()
    payload = {k: v for k, v in form.items()}

    # Verificar firma
    p_signature = payload.pop("p_signature", None)
    verified = False
    try:
        if p_signature and PADDLE_PUBLIC_KEY:
            # Preparar serialización
            items = sorted(payload.items())
            serialized = b""
            for k, v in items:
                if isinstance(v, (list, dict)):
                    s = json.dumps(v, separators=(",", ":"), sort_keys=True)
                else:
                    s = str(v)
                serialized += s.encode("utf-8")

            signature = base64.b64decode(p_signature)
            # Load public key (either PEM contents or path)
            if PADDLE_PUBLIC_KEY.strip().startswith("-----BEGIN"):
                key = RSA.import_key(PADDLE_PUBLIC_KEY)
            else:
                key = RSA.import_key(open(PADDLE_PUBLIC_KEY, "rb").read())
            verifier = PKCS1_v1_5.new(key)
            digest = SHA1.new(serialized)
            verified = verifier.verify(digest, signature)
    except Exception:
        verified = False

    # Si no se puede verificar, responder 400
    if not verified:
        return JSONResponse(status_code=400, content={"error": "invalid signature"})

    # Manejar alertas de pago
    alert = payload.get("alert_name") or payload.get("alert_type")
    passthrough = payload.get("passthrough")

    if alert and "payment" in alert and passthrough:
        # Marcar como pagado
        mark_paid(passthrough, info=payload)

    return JSONResponse({"status": "ok"})


@app.get("/status")
def payment_status(job: str):
    paid = is_paid(job)
    if paid:
        return JSONResponse({"paid": True, "download": f"/download/{job}?watermark=0"})
    return JSONResponse({"paid": False})
