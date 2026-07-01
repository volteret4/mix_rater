const dims = [
  "alegre_melancolica",
  "relajada_energetica",
  "instrumental_cantada",
  "lenta_rapida",
  "bailable_nobailable",
  "comercial_experimental",
  "luminosa_oscura",
  "fondo_atencion",
  "fluida_percusiva",
  "estatica_dinamica",
  "reflexiva_fisica",
  "intima_epica",
];

let activeDims = new Set(dims);

// ---------------- checkbox selector ----------------

function buildSelector() {
  const div = document.getElementById("dim_select");

  dims.forEach((d) => {
    const el = document.createElement("label");

    el.innerHTML = `
          <input type="checkbox" checked id="c_${d}">
          ${d}
        `;

    div.appendChild(el);
  });
}

// ---------------- sliders ----------------

function buildSliders() {
  const div = document.getElementById("sliders");
  div.innerHTML = "";

  dims.forEach((d) => {
    const row = document.createElement("div");

    row.innerHTML = `
          <label>${d}</label>
          <input type="range" min="-5" max="5" value="0" id="${d}">
        `;

    div.appendChild(row);
  });
}

// ---------------- search ----------------

async function search() {
  const vector = dims.map((d) => {
    const cb = document.getElementById("c_" + d);
    return cb.checked ? parseInt(document.getElementById(d).value) : 0;
  });

  const r = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vector }),
  });

  const data = await r.json();

  const div = document.getElementById("results");
  div.innerHTML = "";

  data.forEach((t) => {
    const el = document.createElement("div");
    el.innerText = `${t.artist} - ${t.title} (${(t.sim * 100).toFixed(1)}%)`;
    div.appendChild(el);
  });
}

buildSelector();
buildSliders();
