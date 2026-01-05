fetch("../partials/nav.html")
  .then(res => res.text())
  .then(data => {
    try {
      // Parse and insert safely
      const parser = new DOMParser();
      const doc = parser.parseFromString(data, 'text/html');
      const fragment = document.importNode(doc.body, true);
      const nav = document.getElementById('nav');
      nav.appendChild(fragment);
    } catch (e) {
      console.error('Nav parse error', e);
      document.getElementById("nav").innerHTML = data;
    }
  })
  .catch(err => console.error("Nav load error:", err));