const form = document.getElementById("cataForm");
const status = document.getElementById("status");
const button = form.querySelector("button");

const API_URL =
  window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000/generate"
    : "/generate";

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const whatsapp = form.whatsapp.value.trim();
  if (!/^\d{10,15}$/.test(whatsapp)) {
    status.textContent = "❌ Número de WhatsApp inválido";
    return;
  }

  status.textContent = "⏳ Generando tu catálogo...";
  button.disabled = true;

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      body: new FormData(form)
    });

    if (!response.ok) throw new Error();

    const data = await response.json();
    window.location.href = data.preview_url;

  } catch {
    status.textContent = "❌ Ocurrió un error. Intenta de nuevo.";
  } finally {
    button.disabled = false;
  }
});
