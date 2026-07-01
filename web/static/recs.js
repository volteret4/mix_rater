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

// ---------------- sliders ----------------

function build() {
  const div = document.getElementById("sliders");
  div.innerHTML = "";

  dims.forEach((d) => {
    const row = document.createElement("div");

    row.innerHTML = `
          <label>${d}</label>
          <input type="range" min="-5" max="5" value="0" id="${d}">
          <span id="v_${d}">0</span>
        `;

    div.appendChild(row);

    const input = document.getElementById(d);
    const label = document.getElementById("v_" + d);

    input.oninput = () => (label.innerText = input.value);
  });
}

// ---------------- search ----------------

async function search() {
  const vector = dims.map((d) => parseInt(document.getElementById(d).value));

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
    el.className = "rec";
    el.innerText = `${t.artist} - ${t.title} (${(t.sim * 100).toFixed(1)}%)`;
    div.appendChild(el);
  });
}

build();
