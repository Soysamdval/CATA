"""Script de prueba: sube un CSV y un logo para generar un catálogo.
Requiere que el servidor esté corriendo en http://127.0.0.1:8000
"""
import requests
from PIL import Image, ImageDraw
import io

API = "http://127.0.0.1:8000/generate"
CSV_PATH = "./tmp/151c2598-dba1-40d8-af47-26983ddad026.csv"


def run():
    # Crear un logo temporal
    img = Image.new("RGB", (400, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50, 180), "CATA", fill=(34,197,94))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    with open(CSV_PATH, "rb") as csv_file:
        files = {
            'csv': ('sample.csv', csv_file, 'text/csv'),
            'logo': ('logo.png', buf, 'image/png')
        }
        data = {'whatsapp': '573001234567'}
        r = requests.post(API, files=files, data=data)
        print(r.status_code)
        print(r.text)


if __name__ == '__main__':
    run()