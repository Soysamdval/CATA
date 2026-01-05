const params = new URLSearchParams(window.location.search);
const jobId = params.get("job");

if (!jobId) {
  document.getElementById('status').textContent = "Catálogo no encontrado";
  setTimeout(()=> location.href = '/', 2000);
}

const API_BASE =
  window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : "";

// Para previsualización usamos un endpoint que devuelve el PDF con Content-Disposition inline
const watermarkPreview = `${API_BASE}/preview/${jobId}`;
const watermarkDownload = `${API_BASE}/download/${jobId}?watermark=1`;
const cleanDownload = `${API_BASE}/download/${jobId}?watermark=0`;

// Cargar el PDF en el iframe (no descarga automática)
document.getElementById("pdfPreview").src = watermarkPreview;

// Descarga solo cuando el usuario haga clic
document.getElementById("freeDownload").onclick = () => {
  // abrir en nueva pestaña para que el navegador gestione la descarga
  window.open(watermarkDownload, "_blank");
};

// Pago / descarga limpia
document.getElementById("payDownload").onclick = async () => {
  try {
    const res = await fetch(`${API_BASE}/checkout?job=${jobId}`);
    const data = await res.json();
    if (data.url) {
      // Redirigimos al Pay Link de Paddle
      document.getElementById('status').textContent = 'Redirigiendo a la pasarela de pago...';
      window.location.href = data.url;
    } else {
      document.getElementById('status').textContent = 'No se pudo iniciar el pago. Intenta de nuevo.';
    }
  } catch (e) {
    document.getElementById('status').textContent = 'Error al iniciar pago. Intenta más tarde.';
  }
};
