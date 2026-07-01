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

let current = null;

// ---------------- LOAD SONG ----------------

async function load() {
  const r = await fetch("/api/random");
  current = await r.json();

  document.getElementById("title").innerText =
    current.artist + " - " + current.title;

  document.getElementById("meta").innerText =
    `${current.album || "?"} | ${current.genre || "?"} | ${current.year || "?"}`;

  buildSliders();
}

// ---------------- SLIDERS ----------------

function buildSliders() {
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

    input.oninput = () => {
      label.innerText = input.value;
    };
  });
}

// ---------------- SAVE ----------------

async function save() {
  if (!current) return;

  const vector = {};

  dims.forEach((d) => {
    vector[d] = parseInt(document.getElementById(d).value);
  });

  await fetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: current.id,
      ratings: vector,
    }),
  });

  load(); // siguiente canción
}

// init
load();
