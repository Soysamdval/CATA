# ==========================================
# CATA — Motor de generación de catálogos PDF
# ==========================================

from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from PIL import Image
from io import BytesIO
import csv
import requests
import urllib.parse
import os

# ---------- PALETA CATA ----------
GREEN = HexColor("#22C55E")
GREEN_BORDER = HexColor("#16A34A")
CREAM = HexColor("#FFFFFF")
GRAY = HexColor("#F3F4F6")
TEXT = HexColor("#111827")

# ---------- ESTILOS ----------
title_style = ParagraphStyle(
    name="Title",
    fontName="Helvetica-Bold",
    fontSize=24,
    textColor=TEXT,
    alignment=1,
    leading=28
)

intro_style = ParagraphStyle(
    name="Intro",
    fontName="Helvetica",
    fontSize=11,
    textColor=TEXT,
    alignment=1,
    leading=16
)

# ---------- CACHE ----------
session = requests.Session()
image_cache = {}
whatsapp_cache = {}

def normalize_whatsapp(whatsapp):
    return "".join(filter(str.isdigit, str(whatsapp)))

# ==========================================
# CSV → DATA
# ==========================================

def load_products_from_csv(csv_path):
    data = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row.get("category", "").strip()
            name = row.get("name", "").strip()
            price_raw = row.get("price", "").strip()
            price = float(price_raw) if price_raw else None
            image_url = row.get("image_url", "").strip()
            if category and name:
                data.append((category, name, price, image_url))
    data.sort(key=lambda x: x[0])
    return data

# ==========================================
# UTILIDADES
# ==========================================

def truncate(text, max_len=55):
    return text if len(text) <= max_len else text[:max_len - 3] + "..."

def get_image(url):
    if not url:
        return None
    if url in image_cache:
        return image_cache[url]
    try:
        r = session.get(url, timeout=6)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.thumbnail((400, 400), Image.LANCZOS)
        reader = ImageReader(img)
        image_cache[url] = reader
        return reader
    except:
        image_cache[url] = None
        return None

def whatsapp_link(product, price, whatsapp):
    whatsapp = normalize_whatsapp(whatsapp)
    key = (product, price, whatsapp)
    if key in whatsapp_cache:
        return whatsapp_cache[key]

    lines = [
        "Hola, quiero este producto desde el catálogo:",
        "",
        f"• {product}"
    ]
    if price:
        lines.append(f"Precio: ${price:,.0f}")
    lines.append("")
    lines.append("¿Está disponible?")

    msg = "\n".join(lines)
    link = f"https://wa.me/{whatsapp}?text={urllib.parse.quote(msg)}"
    whatsapp_cache[key] = link
    return link

# ==========================================
# ELEMENTOS VISUALES
# ==========================================

def draw_background(c, w, h):
    c.setFillColor(CREAM)
    c.rect(0, 0, w, h, fill=1)

def draw_button(c, x, y, w, h, text, url):
    c.setFillColor(GREEN)
    c.setStrokeColor(GREEN_BORDER)
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, 14, fill=1, stroke=1)
    c.setFillColor(CREAM)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x + w / 2, y + h / 2 - 4, text)
    c.linkURL(url, (x, y, x + w, y + h), relative=0)

def draw_footer(c, width, whatsapp):
    w, h = 6 * cm, 1.3 * cm
    x = (width - w) / 2
    link = whatsapp_link("Pedido desde el catálogo", None, whatsapp)
    draw_button(c, x, 2 * cm, w, h, "Finalizar pedido", link)

# ---------- MARCAS DE AGUA ----------

def draw_logo_watermark(c, width, height, logo_path):
    if not os.path.exists(logo_path):
        return
    try:
        c.saveState()
        c.setFillAlpha(0.05)
        size = 12 * cm
        x = (width - size) / 2
        y = (height - size) / 2
        c.drawImage(logo_path, x, y, size, size, mask="auto")
        c.restoreState()
    except:
        pass

def draw_text_watermark(c, width, height):
    c.saveState()
    c.setFillAlpha(0.035)
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(TEXT)
    c.translate(width / 2, height / 2)
    c.rotate(30)

    text = "Creado con CATA · Catálogos para WhatsApp"
    spacing = 7 * cm

    for x in range(-int(width), int(width), int(spacing)):
        for y in range(-int(height), int(height), int(spacing)):
            c.drawCentredString(x, y, text)

    c.restoreState()

# ==========================================
# FUNCIÓN PRINCIPAL
# ==========================================

def generate_cata(
    csv_path,
    logo_path,
    whatsapp,
    output_path,
    watermark=True
):
    print("🚀 Generando CATA...")

    whatsapp = normalize_whatsapp(whatsapp)
    data = load_products_from_csv(csv_path)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    SIDE = 3 * cm
    TOP = 3 * cm
    BOTTOM = 3 * cm
    IMG = 3.2 * cm
    CARD = 4.6 * cm

    CONTENT_WIDTH = width - (SIDE * 2)
    y = height - TOP
    current_category = None

    # ---------- PORTADA ----------
    draw_background(c, width, height)
    if watermark:
        draw_logo_watermark(c, width, height, logo_path)
        draw_text_watermark(c, width, height)

    title = Paragraph("Tu catálogo está listo", title_style)
    title.wrapOn(c, width - 6 * cm, 3 * cm)
    title.drawOn(c, 3 * cm, height - 5 * cm)

    intro = Paragraph(
        "Explora productos y pide directamente por WhatsApp.<br/><br/>"
        "Haz clic en <b>Lo quiero</b> para comenzar tu compra.",
        intro_style
    )
    intro.wrapOn(c, width - 8 * cm, 6 * cm)
    intro.drawOn(c, 4 * cm, height - 9 * cm)

    draw_footer(c, width, whatsapp)
    c.showPage()

    draw_background(c, width, height)
    if watermark:
        draw_logo_watermark(c, width, height, logo_path)
        draw_text_watermark(c, width, height)
    y = height - TOP

    # ---------- PRODUCTOS ----------
    for category, name, price, image_url in data:

        if category != current_category:
            if current_category:
                draw_footer(c, width, whatsapp)
                c.showPage()
                draw_background(c, width, height)
                if watermark:
                    draw_logo_watermark(c, width, height, logo_path)
                    draw_text_watermark(c, width, height)
                y = height - TOP

            c.setFillColor(GREEN)
            c.roundRect(SIDE, y - 1.2 * cm, CONTENT_WIDTH, 1.4 * cm, 18, fill=1)
            c.setFillColor(CREAM)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(SIDE + 1 * cm, y - 0.9 * cm, category)

            y -= 2.4 * cm
            current_category = category

        if y - CARD < BOTTOM:
            draw_footer(c, width, whatsapp)
            c.showPage()
            draw_background(c, width, height)
            if watermark:
                draw_logo_watermark(c, width, height, logo_path)
                draw_text_watermark(c, width, height)
            y = height - TOP

        c.setFillColor(GRAY)
        c.roundRect(SIDE, y - CARD, CONTENT_WIDTH, CARD - 0.6 * cm, 20, fill=1)

        img = get_image(image_url)
        if img:
            c.drawImage(img, SIDE + 1 * cm, y - IMG - 0.8 * cm, IMG, IMG, mask="auto")

        c.setFillColor(TEXT)
        c.setFont("Helvetica", 10)
        c.drawString(SIDE + IMG + 2.2 * cm, y - 1.6 * cm, truncate(name))

        price_text = f"${price:,.0f}" if price else "Precio por DM"
        c.setFont("Helvetica-Bold", 12)
        c.drawString(SIDE + IMG + 2.2 * cm, y - 2.7 * cm, price_text)

        draw_button(
            c,
            SIDE + IMG + 2.2 * cm,
            y - 4.1 * cm,
            5 * cm,
            1.3 * cm,
            "Lo quiero",
            whatsapp_link(name, price, whatsapp)
        )

        y -= CARD + 0.4 * cm

    draw_footer(c, width, whatsapp)
    c.save()

    print("✅ CATA generado con éxito")
