/* HudumaLink front-end behaviour. Plain JavaScript, no frameworks, no build step. */
(function () {
  "use strict";

  /* --- Dark / light theme: remembered in localStorage (wrapped: it can throw) --- */
  var root = document.documentElement;
  function savedTheme() { try { return localStorage.getItem("hl-theme"); } catch (e) { return null; } }
  function setTheme(t) {
    root.setAttribute("data-theme", t);
    try { localStorage.setItem("hl-theme", t); } catch (e) {}
    var btn = document.getElementById("theme-toggle");
    if (btn) btn.textContent = t === "dark" ? "☀️" : "🌙";
  }
  setTheme(savedTheme() || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  var toggle = document.getElementById("theme-toggle");
  if (toggle) toggle.addEventListener("click", function () {
    setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
  });

  /* --- Mobile navigation --- */
  var navBtn = document.getElementById("nav-toggle"), nav = document.getElementById("main-nav");
  if (navBtn && nav) navBtn.addEventListener("click", function () {
    var open = nav.classList.toggle("open");
    navBtn.setAttribute("aria-expanded", open);
  });

  /* --- Live character counter on any textarea[data-max] --- */
  document.querySelectorAll("textarea[data-max]").forEach(function (area) {
    var out = document.getElementById(area.id + "-count");
    function update() { if (out) out.textContent = area.value.length + " / " + area.dataset.max; }
    area.addEventListener("input", update); update();
  });

  /* --- Image preview + client-side size check on the upload field --- */
  var file = document.getElementById("image");
  var preview = document.getElementById("image-preview");
  if (file && preview) file.addEventListener("change", function () {
    var f = file.files[0];
    preview.innerHTML = "";
    if (!f) return;
    if (f.size > 5 * 1024 * 1024) { alert("That photo is larger than 5 MB. Please pick a smaller one."); file.value = ""; return; }
    var img = document.createElement("img");
    img.alt = "Preview of the selected photo";
    img.src = URL.createObjectURL(f);
    preview.appendChild(img);
  });

  /* --- Use the phone's GPS to fill the location box (needs the user's permission) --- */
  var gps = document.getElementById("use-gps");
  if (gps) gps.addEventListener("click", function () {
    var box = document.getElementById("location");
    if (!navigator.geolocation) { alert("Your browser does not support location."); return; }
    gps.disabled = true; gps.textContent = "Locating…";
    navigator.geolocation.getCurrentPosition(function (p) {
      box.value = (box.value ? box.value + " " : "") + "(GPS " + p.coords.latitude.toFixed(5) + ", " + p.coords.longitude.toFixed(5) + ")";
      gps.disabled = false; gps.textContent = "📍 Use my location";
    }, function () { gps.disabled = false; gps.textContent = "📍 Use my location"; alert("We could not get your location. Please type it instead."); });
  });

  /* --- Stop double submissions: disable the submit button after the first click --- */
  document.querySelectorAll("form[data-once]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var b = form.querySelector("button[type=submit]");
      if (b) { b.disabled = true; b.textContent = "Please wait…"; }
    });
  });

  /* --- Copy-to-clipboard buttons (tracking numbers) --- */
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (navigator.clipboard) navigator.clipboard.writeText(b.dataset.copy).then(function () {
        var old = b.textContent; b.textContent = "Copied ✓"; setTimeout(function () { b.textContent = old; }, 1500);
      });
    });
  });
})();
