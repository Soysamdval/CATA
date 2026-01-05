"""
CATA - Generador de Catálogos PDF
Backend optimizado con FastAPI
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import os
import uuid
import json
import base64
import logging
import asyncio
from functools import lru_cache

# ==========================================
# CONFIGURACIÓN Y LOGGING
# ==========================================

class Config:
    """Configuración centralizada de la aplicación"""
    
    # Entorno
    SITE_URL: str = os.getenv("SITE_URL", "http://127.0.0.1:8000")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Paddle
    PADDLE_VENDOR_ID: Optional[str] = os.getenv("PADDLE_VENDOR_ID")
    PADDLE_VENDOR_AUTH_CODE: Optional[str] = os.getenv("PADDLE_VENDOR_AUTH_CODE")
    PADDLE_PUBLIC_KEY: Optional[str] = os.getenv("PADDLE_PUBLIC_KEY")
    PADDLE_WEBHOOK_TIMEOUT: int = 10
    
    # Archivos
    BASE_DIR: Path = Path(__file__).parent.absolute()
    TMP_DIR: Path = BASE_DIR / "tmp"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    FRONTEND_DIR: Path = BASE_DIR.parent / "Frontend"
    
    # Límites de archivos
    MAX_CSV_SIZE: int = 5 * 1024 * 1024  # 5 MB
    MAX_LOGO_SIZE: int = 2 * 1024 * 1024  # 2 MB
    CHUNK_SIZE: int = 65536  # 64 KB
    
    # Precio del producto
    PRODUCT_PRICE: str = "USD:15.00"
    PRODUCT_TITLE: str = "CATA — Catálogo sin marca de agua"
    
    # Tipos de archivos permitidos
    ALLOWED_CSV_TYPES: set = {"text/csv", "application/vnd.ms-excel", "text/plain"}
    ALLOWED_LOGO_TYPES: set = {"image/png", "image/jpeg"}
    
    # Limpieza automática
    CLEANUP_ENABLED: bool = os.getenv("CLEANUP_ENABLED", "true").lower() == "true"
    FILE_RETENTION_HOURS: int = int(os.getenv("FILE_RETENTION_HOURS", "24"))

    @classmethod
    def validate(cls) -> None:
        """Valida la configuración al inicio"""
        cls.TMP_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        if not cls.PADDLE_VENDOR_ID or not cls.PADDLE_VENDOR_AUTH_CODE:
            logging.warning("Paddle credentials not configured. Payment features will be disabled.")

@lru_cache()
def get_config() -> Config:
    """Dependencia para obtener configuración (singleton)"""
    return Config()


# Configurar logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("cata")

# ==========================================
# IMPORTACIONES OPCIONALES Y MÓDULOS
# ==========================================

# Crypto (opcional)
HAS_CRYPTO = False
try:
    from Crypto.Hash import SHA1
    from Crypto.PublicKey import RSA
    from Crypto.Signature import PKCS1_v1_5
    HAS_CRYPTO = True
    logger.info("Crypto library loaded successfully")
except ImportError:
    logger.warning(
        "pycryptodome not installed. Paddle webhook verification disabled. "
        "Install with: pip install pycryptodome"
    )

# Requests para API de Paddle
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.error("requests library not installed. Payment features disabled.")

# Módulos internos
try:
    from cata_pdf import generate_cata
    from db import init_db, mark_paid, is_paid, cleanup_old_files
    HAS_INTERNAL_MODULES = True
except ImportError as e:
    HAS_INTERNAL_MODULES = False
    logger.error(f"Internal modules not found: {e}")


# ==========================================
# UTILIDADES
# ==========================================

class FileHandler:
    """Manejo seguro de archivos"""
    
    @staticmethod
    async def save_upload_limited(
        upload_file: UploadFile,
        dest_path: Path,
        max_bytes: int,
        allowed_types: set
    ) -> None:
        """Guarda un archivo con límites de tamaño y validación de tipo"""
        
        # Validar tipo de contenido
        if upload_file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )
        
        total_bytes = 0
        try:
            with open(dest_path, "wb") as out:
                while chunk := await upload_file.read(Config.CHUNK_SIZE):
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        out.close()
                        dest_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail=f"File exceeds maximum size of {max_bytes / (1024*1024):.1f} MB"
                        )
                    out.write(chunk)
        except HTTPException:
            raise
        except Exception as e:
            dest_path.unlink(missing_ok=True)
            logger.error(f"Error saving file {dest_path}: {e}")
            raise HTTPException(status_code=500, detail="Error saving file")
        finally:
            await upload_file.close()
        
        logger.info(f"Saved file {dest_path.name} ({total_bytes / 1024:.1f} KB)")
    
    @staticmethod
    def cleanup_temp_files(*paths: Path) -> None:
        """Limpia archivos temporales de forma segura"""
        for path in paths:
            try:
                if path and path.exists():
                    path.unlink()
                    logger.debug(f"Cleaned up temp file: {path.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {path}: {e}")


class PaddleWebhookVerifier:
    """Verificador de firmas de webhooks de Paddle"""
    
    def __init__(self, public_key: Optional[str]):
        self.public_key = public_key
        self.enabled = HAS_CRYPTO and public_key
        
        if not self.enabled:
            logger.warning("Paddle webhook verification disabled")
    
    def verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verifica la firma de un webhook de Paddle"""
        if not self.enabled:
            return False
        
        try:
            # Preparar datos para verificación
            sorted_items = sorted(payload.items())
            serialized = b""
            
            for key, value in sorted_items:
                if isinstance(value, (list, dict)):
                    string_val = json.dumps(value, separators=(",", ":"), sort_keys=True)
                else:
                    string_val = str(value)
                serialized += string_val.encode("utf-8")
            
            # Decodificar firma
            signature_bytes = base64.b64decode(signature)
            
            # Cargar clave pública
            if self.public_key.strip().startswith("-----BEGIN"):
                key = RSA.import_key(self.public_key)
            else:
                with open(self.public_key, "rb") as f:
                    key = RSA.import_key(f.read())
            
            # Verificar
            verifier = PKCS1_v1_5.new(key)
            digest = SHA1.new(serialized)
            
            return verifier.verify(digest, signature_bytes)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False


# ==========================================
# CICLO DE VIDA DE LA APLICACIÓN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación"""
    # Startup
    logger.info("Starting CATA API...")
    Config.validate()
    
    if HAS_INTERNAL_MODULES:
        init_db()
        logger.info("Database initialized")
    
    # Tarea de limpieza periódica (si está habilitada)
    cleanup_task = None
    if Config.CLEANUP_ENABLED and HAS_INTERNAL_MODULES:
        async def periodic_cleanup():
            while True:
                await asyncio.sleep(3600)  # Cada hora
                try:
                    cleanup_old_files(Config.FILE_RETENTION_HOURS)
                    logger.info("Periodic cleanup completed")
                except Exception as e:
                    logger.error(f"Periodic cleanup failed: {e}")
        
        cleanup_task = asyncio.create_task(periodic_cleanup())
        logger.info(f"Periodic cleanup enabled (retention: {Config.FILE_RETENTION_HOURS}h)")
    
    logger.info("CATA API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CATA API...")
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("CATA API stopped")


# ==========================================
# APLICACIÓN FASTAPI
# ==========================================

app = FastAPI(
    title="CATA API",
    description="API para generación de catálogos PDF personalizados",
    version="2.0.0",
    lifespan=lifespan
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos
app.mount("/output", StaticFiles(directory=str(Config.OUTPUT_DIR)), name="output")

# Montar frontend si existe
if Config.FRONTEND_DIR.exists():
    app.mount("/Frontend", StaticFiles(directory=str(Config.FRONTEND_DIR)), name="frontend")
    
    @app.get("/", include_in_schema=False)
    async def root_redirect():
        """Redirige a la página principal del frontend"""
        return RedirectResponse(url="/Frontend/index.html")


# ==========================================
# ENDPOINTS PRINCIPALES
# ==========================================

@app.post("/generate", response_class=JSONResponse)
async def generate_catalog(
    csv: UploadFile = File(..., description="Archivo CSV con productos"),
    logo: UploadFile = File(..., description="Logo de la empresa (PNG/JPEG)"),
    whatsapp: str = Form(..., description="Número de WhatsApp para contacto"),
    config: Config = Depends(get_config)
) -> Dict[str, str]:
    """
    Genera un catálogo PDF con marca de agua (preview) y sin marca (versión completa).
    
    Returns:
        - job_id: Identificador único del trabajo
        - pdf_preview: URL del PDF con marca de agua
        - pdf_clean: URL del PDF sin marca de agua (requiere pago)
        - preview_url: URL de la página de previsualización
    """
    
    if not HAS_INTERNAL_MODULES:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Internal modules not loaded."
        )
    
    job_id = str(uuid.uuid4())
    logger.info(f"Starting job {job_id}")
    
    # Rutas de archivos
    csv_path = config.TMP_DIR / f"{job_id}.csv"
    logo_path = config.TMP_DIR / f"{job_id}_logo{Path(logo.filename).suffix}"
    pdf_watermark = config.OUTPUT_DIR / f"CATA_{job_id}_watermark.pdf"
    pdf_clean = config.OUTPUT_DIR / f"CATA_{job_id}.pdf"
    
    try:
        # Validar número de WhatsApp
        if not whatsapp.strip():
            raise HTTPException(status_code=400, detail="WhatsApp number is required")
        
        # Guardar archivos
        logger.info(f"Job {job_id}: Saving uploaded files")
        await FileHandler.save_upload_limited(
            csv, csv_path, config.MAX_CSV_SIZE, config.ALLOWED_CSV_TYPES
        )
        await FileHandler.save_upload_limited(
            logo, logo_path, config.MAX_LOGO_SIZE, config.ALLOWED_LOGO_TYPES
        )
        
        # Generar PDF con marca de agua
        logger.info(f"Job {job_id}: Generating watermarked PDF")
        await asyncio.to_thread(
            generate_cata,
            csv_path=str(csv_path),
            logo_path=str(logo_path),
            whatsapp=whatsapp.strip(),
            output_path=str(pdf_watermark),
            watermark=True
        )
        
        # Generar PDF limpio
        logger.info(f"Job {job_id}: Generating clean PDF")
        await asyncio.to_thread(
            generate_cata,
            csv_path=str(csv_path),
            logo_path=str(logo_path),
            whatsapp=whatsapp.strip(),
            output_path=str(pdf_clean),
            watermark=False
        )
        
        logger.info(f"Job {job_id}: Completed successfully")
        
        return {
            "job_id": job_id,
            "pdf_preview": f"/download/{job_id}?watermark=1",
            "pdf_clean": f"/download/{job_id}?watermark=0",
            "preview_url": f"/Frontend/preview.html?job={job_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Job {job_id}: Generation failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    finally:
        # Limpieza de archivos temporales
        FileHandler.cleanup_temp_files(csv_path, logo_path)


@app.get("/download/{job_id}")
async def download_pdf(
    job_id: str,
    watermark: int = 1,
    config: Config = Depends(get_config)
) -> FileResponse:
    """
    Descarga el PDF generado.
    
    Args:
        job_id: ID del trabajo
        watermark: 1 para versión con marca, 0 para versión limpia
    """
    
    filename = f"CATA_{job_id}_watermark.pdf" if watermark == 1 else f"CATA_{job_id}.pdf"
    file_path = config.OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
    )


@app.get("/preview/{job_id}")
async def preview_pdf(
    job_id: str,
    config: Config = Depends(get_config)
) -> FileResponse:
    """
    Muestra el PDF con marca de agua en el navegador (inline).
    """
    
    filename = f"CATA_{job_id}_watermark.pdf"
    file_path = config.OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{filename}\""}
    )


# ==========================================
# ENDPOINTS DE PAGO (PADDLE)
# ==========================================

@app.get("/checkout")
async def create_checkout(
    job: str,
    config: Config = Depends(get_config)
) -> Dict[str, str]:
    """
    Crea un link de pago de Paddle para desbloquear el PDF sin marca de agua.
    """
    
    if not HAS_REQUESTS:
        raise HTTPException(status_code=503, detail="Payment service unavailable")
    
    if not config.PADDLE_VENDOR_ID or not config.PADDLE_VENDOR_AUTH_CODE:
        raise HTTPException(
            status_code=503,
            detail="Payment gateway not configured"
        )
    
    payload = {
        "vendor_id": config.PADDLE_VENDOR_ID,
        "vendor_auth_code": config.PADDLE_VENDOR_AUTH_CODE,
        "title": config.PRODUCT_TITLE,
        "prices": [config.PRODUCT_PRICE],
        "return_url": f"{config.SITE_URL}/Frontend/paid.html?job={job}",
        "passthrough": job
    }
    
    try:
        response = requests.post(
            "https://vendors.paddle.com/api/2.0/product/generate_pay_link",
            data=payload,
            timeout=config.PADDLE_WEBHOOK_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success"):
            logger.error(f"Paddle API error: {data}")
            raise HTTPException(
                status_code=502,
                detail="Payment gateway error"
            )
        
        checkout_url = data["response"]["url"]
        logger.info(f"Created checkout for job {job}")
        
        return {"url": checkout_url}
        
    except requests.RequestException as e:
        logger.error(f"Paddle API request failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to connect to payment gateway"
        )


@app.post("/webhook/paddle")
async def paddle_webhook(
    request: Request,
    config: Config = Depends(get_config)
) -> Dict[str, str]:
    """
    Procesa webhooks de Paddle para confirmar pagos.
    """
    
    if not HAS_INTERNAL_MODULES:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    # Obtener datos del formulario
    form = await request.form()
    payload = {k: v for k, v in form.items()}
    
    signature = payload.pop("p_signature", None)
    
    # Verificar firma
    verifier = PaddleWebhookVerifier(config.PADDLE_PUBLIC_KEY)
    
    if not verifier.verify_signature(payload, signature):
        logger.warning(f"Invalid webhook signature from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Procesar eventos de pago
    alert_name = payload.get("alert_name") or payload.get("alert_type")
    passthrough = payload.get("passthrough")
    
    if alert_name and "payment" in alert_name.lower() and passthrough:
        mark_paid(passthrough, info=payload)
        logger.info(f"Marked job {passthrough} as paid (alert: {alert_name})")
    
    return {"status": "ok"}


@app.get("/status")
async def payment_status(
    job: str,
    config: Config = Depends(get_config)
) -> Dict[str, Any]:
    """
    Verifica si un trabajo ha sido pagado.
    """
    
    if not HAS_INTERNAL_MODULES:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    paid = is_paid(job)
    
    response = {"paid": paid}
    if paid:
        response["download"] = f"/download/{job}?watermark=0"
    
    return response


# ==========================================
# ENDPOINTS DE SALUD Y MONITOREO
# ==========================================

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Verifica el estado de salud del servicio"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "modules": {
            "crypto": HAS_CRYPTO,
            "requests": HAS_REQUESTS,
            "internal": HAS_INTERNAL_MODULES
        },
        "config": {
            "paddle_configured": bool(Config.PADDLE_VENDOR_ID and Config.PADDLE_VENDOR_AUTH_CODE),
            "cleanup_enabled": Config.CLEANUP_ENABLED
        }
    }


@app.get("/metrics")
async def metrics(config: Config = Depends(get_config)) -> Dict[str, Any]:
    """Métricas básicas del servicio"""
    
    output_files = list(config.OUTPUT_DIR.glob("*.pdf"))
    temp_files = list(config.TMP_DIR.glob("*"))
    
    return {
        "files": {
            "output_count": len(output_files),
            "temp_count": len(temp_files),
            "output_size_mb": sum(f.stat().st_size for f in output_files) / (1024 * 1024),
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ==========================================
# MANEJADORES DE ERRORES
# ==========================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "path": str(request.url)}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.exception("Internal server error")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=Config.LOG_LEVEL.lower()
    )