import * as React from "react";

export type SpectralDrapeProps = React.CanvasHTMLAttributes<HTMLCanvasElement> & {
  colors?: [string, string];
  backgroundColor?: string;
  density?: number;
  dotSize?: number;
  strands?: number;
  amplitude?: number;
  frequency?: number;
  depth?: number;
  speed?: number;
  interactive?: boolean;
  brush?: number;
  brushRadius?: number;
  children?: React.ReactNode;
};

/**
 * Flask-safe adapter surface for the React Bits Pro Spectral Drape API.
 * The live Flask hero uses static/js/spectral-drape.js; this component keeps
 * the same control vocabulary available if a React surface is introduced.
 */
export function SpectralDrape({
  colors = ["#98E6BE", "#F4C95D"],
  backgroundColor = "transparent",
  density = 1,
  dotSize = 1,
  strands = 8,
  amplitude = 1,
  frequency = 1,
  depth = 1,
  speed = 1,
  interactive = true,
  brush = 1,
  brushRadius = 0.2,
  children,
  className,
  style,
  ...canvasProps
}: SpectralDrapeProps) {
  const ref = React.useRef<HTMLCanvasElement>(null);
  React.useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let frame = 0;
    let width = 0;
    let height = 0;
    const pointer = { x: 0.5, y: 0.5, active: false };
    const dots = Array.from({ length: Math.max(500, Math.floor(1300 * density)) }, () => ({
      x: Math.random(), y: Math.random(), phase: Math.random() * Math.PI * 2, depth: Math.random(),
    }));
    const resize = () => {
      const rect = canvas.getBoundingClientRect(); width = rect.width; height = rect.height;
      canvas.width = width * dpr; canvas.height = height * dpr; context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const paint = (time: number) => {
      context.fillStyle = backgroundColor; context.fillRect(0, 0, width, height);
      dots.forEach((dot) => {
        const wave = Math.sin(dot.x * strands * frequency + dot.phase + time * 0.001 * speed) * 0.06 * amplitude;
        let x = (dot.x + wave) * width;
        let y = (dot.y + Math.sin(dot.x * 6 + dot.phase + time * 0.0005 * speed) * 0.04 * depth) * height;
        if (interactive && pointer.active) {
          const dx = pointer.x * width - x; const dy = pointer.y * height - y;
          const distance = Math.hypot(dx, dy); const radius = height * brushRadius;
          if (distance < radius) { const force = (1 - distance / radius) * brush; x += dx * force; y += dy * force; }
        }
        const alpha = 0.2 + dot.depth * 0.5;
        context.fillStyle = colors[dot.depth > 0.72 ? 1 : 0]; context.globalAlpha = alpha;
        context.beginPath(); context.arc(x, y, (0.6 + dot.depth) * dotSize, 0, Math.PI * 2); context.fill();
      });
      context.globalAlpha = 1; if (!motion.matches) frame = requestAnimationFrame(paint);
    };
    const move = (event: PointerEvent) => { const rect = canvas.getBoundingClientRect(); pointer.x = (event.clientX - rect.left) / rect.width; pointer.y = (event.clientY - rect.top) / rect.height; pointer.active = true; };
    resize(); paint(0); window.addEventListener("resize", resize); canvas.addEventListener("pointermove", move); canvas.addEventListener("pointerleave", () => { pointer.active = false; });
    return () => { cancelAnimationFrame(frame); window.removeEventListener("resize", resize); canvas.removeEventListener("pointermove", move); };
  }, [colors, backgroundColor, density, dotSize, strands, amplitude, frequency, depth, speed, interactive, brush, brushRadius]);
  return <div className={className} style={{ position: "relative", overflow: "hidden", ...style }}><canvas ref={ref} {...canvasProps} style={{ display: "block", width: "100%", height: "100%" }} />{children ? <div style={{ position: "absolute", inset: 0 }}>{children}</div> : null}</div>;
}

export default SpectralDrape;
