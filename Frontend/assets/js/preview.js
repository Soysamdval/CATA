const params = new URLSearchParams(window.location.search);
const jobId = params.get("job");

if (!jobId) {
  alert("Catálogo no encontrado");
  location.href = "/";
}

const API_BASE =
  window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : "";

const watermarkPDF = `${API_BASE}/output/${jobId}?watermark=1`;

document.getElementById("pdfPreview").src = watermarkPDF;

document.getElementById("freeDownload").onclick = () => {
  window.open(watermarkPDF, "_blank");
};

document.getElementById("payDownload").onclick = () => {
  // Placeholder realista
  window.location.href = `/checkout?job=${jobId}`;
};
