fetch("../partials/nav.html")
  .then(res => res.text())
  .then(data => {
    document.getElementById("nav").innerHTML = data;
  })
  .catch(err => console.error("Nav load error:", err));