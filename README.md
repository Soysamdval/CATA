# CATA

**CATA** es un motor automatizado para la generación de catálogos en PDF optimizados para **WhatsApp y ventas por DM**, pensado como un **producto SaaS** enfocado en velocidad, simplicidad y escalabilidad.

El objetivo de CATA es permitir que cualquier negocio (emprendedores, marcas, tiendas, mayoristas) pueda **convertir una base de datos o archivo de productos en un catálogo profesional en minutos**, sin conocimientos técnicos ni de diseño.

---

## 🚀 Visión del proyecto

Convertir a **CATA** en una plataforma global para la creación, previsualización y descarga de catálogos comerciales, con un modelo **freemium + pago por descarga**, orientado principalmente a:

* Ventas por WhatsApp
* Catálogos rápidos para redes sociales
* Equipos comerciales
* Emprendedores sin infraestructura ecommerce

---

## 🎯 Objetivos principales

### Objetivo general

Crear un sistema que genere catálogos PDF profesionales de forma **automática**, **rápida** y **personalizable**, a partir de datos estructurados.

### Objetivos específicos

* Automatizar la generación de catálogos PDF desde:

  * Bases de datos
  * CSV
  * APIs
* Optimizar los catálogos para envío por WhatsApp
* Reducir el tiempo de creación de catálogos de horas a minutos
* Implementar un sistema de monetización por descarga
* Escalar el proyecto como SaaS

---

## 🧠 ¿Qué problema resuelve CATA?

Actualmente muchos negocios:

* Diseñan catálogos manualmente
* Dependen de diseñadores
* Actualizan precios de forma lenta
* Usan imágenes desordenadas
* No tienen control sobre versiones

**CATA elimina todo eso**, generando catálogos:

* Automáticos
* Consistentes
* Repetibles
* Escalables

---

## 🧩 Funcionalidades actuales (MVP)

### ✅ Generación de PDF

* Catálogos en tamaño **A4**
* Diseño limpio y comercial
* Imágenes optimizadas
* Precios visibles
* Descripciones automáticas

### ✅ Integración de datos

* Conexión a bases de datos (MySQL)
* Lectura de archivos CSV
* Consumo de imágenes vía URL

### ✅ Motor gráfico

* Generación con **ReportLab**
* Manejo dinámico de márgenes
* Distribución automática de productos por página
* Control de tipografías y colores

### ✅ Branding

* Soporte para:

  * Marca del cliente
  * Marca de agua de CATA
* Preparado para modo **con / sin marca de agua**

---

## 💰 Modelo de negocio

CATA se plantea como un **modelo freemium**:

### Gratis

* Previsualización del catálogo
* Descarga con marca de agua de CATA

### Pago

* Descarga sin marca de agua
* Mayor calidad de imagen
* Catálogo listo para clientes finales

> El pago se realizará **por catálogo generado**, no por suscripción (en fase inicial).

---

## 🧪 Flujo del usuario (UX)

1. El usuario carga su base de datos / archivo
2. CATA procesa la información
3. Se genera una **previsualización** del catálogo
4. El usuario elige:

   * Descargar gratis (con marca de agua)
   * Descargar versión premium (pago)

---

## 🛠️ Tecnologías utilizadas

### Backend

* Python
* ReportLab
* PIL / Pillow
* MySQL
* Requests

### Frontend

* HTML
* CSS
* JavaScript

### Infraestructura (planeada)

* Backend API
* Procesamiento en servidor
* Pasarela de pago global (Paddle / alternativa a Stripe)

---

## 📦 Estructura del proyecto (simplificada)

```
CATA/
├── backend/
│   ├── generator/
│   │   ├── pdf_generator.py
│   │   └── styles.py
│   ├── data/
│   │   ├── db_connector.py
│   │   └── csv_reader.py
│   └── utils/
├── frontend/
│   ├── index.html
│   ├── preview.html
│   └── assets/
├── README.md
```

---

## 🧪 Estado actual del proyecto

* ✅ Motor de generación funcional
* ✅ Pruebas con catálogos reales
* ✅ Optimización de tiempos de carga
* 🚧 UX en proceso de pulido
* 🚧 Sistema de pagos en integración

---

## 🗺️ Roadmap

### Corto plazo

* Finalizar `preview.html`
* Integrar sistema de pago
* Control de descargas
* Manejo de errores

### Mediano plazo

* Panel de usuario
* Historial de catálogos
* Plantillas visuales
* Personalización avanzada

### Largo plazo

* SaaS completo
* API pública
* Multi-idioma
* Integraciones con ecommerce

---

## 🧑‍💻 Filosofía del proyecto

CATA se construye bajo los principios de:

* **Trabajar poco y producir mucho**
* Automatización extrema
* Simplicidad para el usuario
* Escalabilidad técnica

---

## � Despliegue y configuración rápida

1. Crear un virtualenv e instalar dependencias:

   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r Backend/requirements.txt

2. Variables de entorno recomendadas:

   - PADDLE_VENDOR_ID : tu `vendor_id` de Paddle (producción o test)
   - PADDLE_VENDOR_AUTH_CODE : el `vendor_auth_code` para la API de Paddle
   - PADDLE_PUBLIC_KEY : clave pública de Paddle (PEM) para verificar webhooks
   - SITE_URL : URL pública donde se sirve la app (ej. https://tu-dominio.com)

> Nota: eliminamos Stripe y usamos Paddle (pay links + webhooks). Asegúrate de usar credenciales de *test* de Paddle para pruebas.

3. Ejecutar en desarrollo:

   cd Backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000

4. Prueba rápida (opcional):

   - Con el servidor en marcha, ejecutar `python test_generate.py` para probar la generación automática desde un CSV de ejemplo y un logo generado dinámicamente.
   - El script te devolverá el `job_id` y las URLs de previsualización/descarga.

---

## 🧪 Webhooks (Paddle) — pruebas locales con ngrok

Para probar webhooks de Paddle en desarrollo (recomendado):

1. Arranca el servidor localmente con el venv activado:

   ```powershell
   cd Backend
   .\.venv\Scripts\Activate.ps1
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Abre un túnel público con ngrok (o similar):

   ngrok http 8000

   Copia la URL pública que te da ngrok, por ejemplo `https://abcd1234.ngrok.io`.

3. En el dashboard de Paddle (o usando la API de pay links), configura el webhook a:

   `https://abcd1234.ngrok.io/webhook/paddle`

4. Asegúrate de setear `PADDLE_PUBLIC_KEY` en tu entorno con la clave pública PEM que Paddle provee.

5. Para probar sin usar Paddle, usa la utilidad de prueba local que firma el payload y lo envía a tu servidor:

   ```powershell
   cd Backend
   .\.venv\Scripts\Activate.ps1
   python tools\send_paddle_test.py --job <job_id> --url https://abcd1234.ngrok.io/webhook/paddle
   ```

   La utilidad imprimirá una clave pública de prueba para que la pongas en `PADDLE_PUBLIC_KEY` si prefieres validar firmando/firmas locales.

6. La ruta `/status?job=<job_id>` te dirá si el pago fue confirmado y te devolverá el enlace para descargar la versión limpia del PDF.

---

4. Producción (recomendado): desplegar en un servicio con soporte WSGI/ASGI (e.g. Gunicorn+Uvicorn, Docker, Railway, Fly.io) y configurar HTTPS y variables de entorno.

5. Configurar Stripe:

   - Crear un producto "CATA — Sin marca de agua" y utilizar Checkout Sessions (se utiliza en `/checkout`).
   - Configurar `STRIPE_SECRET_KEY` y `SITE_URL` para que los redirect URLs funcionen correctamente.

> Nota: se sugiere integrar webhooks de Stripe para mayor seguridad en producción (marcar catálogos como pagados sólo tras un evento `checkout.session.completed`).

---
## ✅ Auditoría técnica (resumen)

He realizado una auditoría y aplicado mejoras críticas para preparar el proyecto para pruebas y despliegue:

- Migración de pagos a SQLite + pruebas unitarias del webhook (firma Paddle).
- Integración de Paddle (Pay Links) y webhook con verificación RSA.
- Validación de uploads (CSV y logo) con límites (5MB CSV, 2MB logo) y manejo de errores 413/400.
- Limpieza segura de ficheros temporales y logging estructurado (`LOG_LEVEL` env var).
- Mejora de UX y accesibilidad (labels `for`, `aria-live`, mensajes en página, evitar alert()).
- Mejoras SEO: meta tags, canonical, structured data JSON-LD en `index.html`.
- Tests: añadidos y ejecutados (`pytest` — 1 test que valida webhook), utilidades para firmar y enviar webhooks de prueba.

---

## 📌 Próximos pasos (prioridad para mañana)

1. Probar webhooks en entorno público usando `ngrok` y validar la firma con `PADDLE_PUBLIC_KEY`.
2. Preparar entorno asíncrono (Worker + Redis) para mover la generación de PDF a background jobs.
3. Mover almacenamiento de PDFs a S3 (o MinIO para dev) y servir con signed URLs.
4. Añadir CI (GitHub Actions): lint, tests, build Docker image y checks de seguridad.

---
## �📄 Licencia

Este proyecto se encuentra en desarrollo activo.

---

## ✨ Autor

**Samuel Sánchez**
Proyecto desarrollado como base para una **startup de automatización comercial**.

---

> CATA no es solo un generador de PDFs. Es una herramienta para vender más, más rápido.