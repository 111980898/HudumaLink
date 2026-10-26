(function () {
  "use strict";
  var canvas = document.getElementById("vortex-canvas");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;
  var section = canvas.closest("[data-vortex-section]");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var width = 0;
  var height = 0;
  var frame = 0;
  var scrollBoost = 0;
  var scrollTarget = 0;
  var pointer = { x: 0.5, y: 0.5, active: false };
  var rings = 42;
  var particles = Array.from({ length: 1450 }, function (_, index) {
    return { angle: index * 0.043, radius: Math.random(), depth: Math.random(), seed: Math.random() * Math.PI * 2 };
  });

  function resize() {
    var rect = canvas.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    canvas.width = Math.max(1, Math.floor(width * dpr));
    canvas.height = Math.max(1, Math.floor(height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function paint(time) {
    var focusX = width * (0.51 + (pointer.active ? (pointer.x - 0.5) * 0.08 : 0));
    var focusY = height * (0.32 + (pointer.active ? (pointer.y - 0.5) * 0.04 : 0));
    scrollBoost += (scrollTarget - scrollBoost) * 0.08;
    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = "lighter";
    ctx.strokeStyle = "rgba(152,230,190,.16)";
    ctx.lineWidth = 1;
    for (var ring = 1; ring <= rings; ring += 1) {
      var scale = ring / rings;
      var wobble = Math.sin(time * 0.0003 + ring) * 0.02;
      ctx.beginPath();
      ctx.ellipse(focusX, focusY, width * (0.06 + scale * 0.7), height * (0.05 + scale * 0.65) * (1 + wobble), 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    particles.forEach(function (particle) {
      var orbit = particle.angle + time * 0.00012 + scrollBoost * 0.8 + particle.seed;
      var tunnel = Math.max(0.035, particle.radius + Math.sin(time * 0.0005 + particle.seed) * 0.045);
      var depth = 0.2 + tunnel * 1.85;
      var x = focusX + Math.cos(orbit) * width * tunnel * 0.43 * depth;
      var y = focusY + Math.sin(orbit) * height * tunnel * 0.28 * depth;
      var alpha = (0.12 + particle.depth * 0.66) * (1 - Math.min(0.7, tunnel * 0.35));
      ctx.globalAlpha = alpha;
      ctx.fillStyle = particle.depth > 0.8 ? "#F4C95D" : "#98E6BE";
      ctx.beginPath();
      ctx.arc(x, y, 0.35 + particle.depth * 1.1, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    if (!reduce) frame = requestAnimationFrame(paint);
  }

  function updateScroll() {
    if (!section) return;
    var rect = section.getBoundingClientRect();
    var progress = Math.max(0, Math.min(1, (window.innerHeight - rect.top) / (window.innerHeight + rect.height)));
    scrollTarget = progress * 2.4;
    section.style.setProperty("--vortex-progress", progress.toFixed(3));
  }

  function move(event) {
    var rect = canvas.getBoundingClientRect();
    pointer.x = (event.clientX - rect.left) / rect.width;
    pointer.y = (event.clientY - rect.top) / rect.height;
    pointer.active = true;
  }
  function leave() { pointer.active = false; }

  resize();
  updateScroll();
  paint(0);
  window.addEventListener("resize", resize);
  window.addEventListener("scroll", updateScroll, { passive: true });
  canvas.addEventListener("pointermove", move);
  canvas.addEventListener("pointerleave", leave);
})();
