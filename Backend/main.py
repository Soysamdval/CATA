# ==========================================
# CATA — Backend principal
# ==========================================

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import os
import uuid
import shutil

from cata_pdf import generate_cata

# ---------- CONFIG ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(BASE_DIR, "tmp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

    try:
        # ---------- GUARDAR ARCHIVOS ----------
        with open(csv_path, "wb") as f:
            shutil.copyfileobj(csv.file, f)

        with open(logo_path, "wb") as f:
            shutil.copyfileobj(logo.file, f)

        # ---------- GENERAR PDF (CON MARCA DE AGUA) ----------
        generate_cata(
            csv_path=csv_path,
            logo_path=logo_path,
            whatsapp=whatsapp,
            output_path=pdf_watermark,
            watermark=True  # 🔥 CLAVE PARA MODELO DE NEGOCIO
        )

        # ---------- RESPUESTA (NO DESCARGA) ----------
        return JSONResponse({
            "job_id": job_id,
            "pdf_preview": f"/output/CATA_{job_id}_watermark.pdf",
            "preview_url": f"../Frontend/preview.html?job={job_id}"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
