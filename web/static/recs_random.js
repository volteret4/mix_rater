let current = null;

async function load() {
  const r = await fetch("/api/random");
  current = await r.json();

  document.getElementById("track").innerText =
    current.artist + " - " + current.title;

  const recs = await fetch("/api/similar/" + current.id);
  const data = await recs.json();

  const div = document.getElementById("recs");
  div.innerHTML = "";

  data.forEach((t) => {
    const el = document.createElement("div");
    el.innerText = `${t.artist} - ${t.title}`;
    div.appendChild(el);
  });
}

load();
