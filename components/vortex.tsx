import * as React from "react";

export type VortexProps = React.HTMLAttributes<HTMLDivElement> & {
  discCount?: number;
  particleCount?: number;
  particleColor?: string;
  discColor?: string;
  discLineWidth?: number;
  particleSize?: number;
  depth?: number;
  spread?: number;
  speed?: number;
  rotationDirection?: number;
  centerX?: number;
  centerY?: number;
  opacity?: number;
  enableCursorInteraction?: boolean;
  cursorInfluence?: number;
  children?: React.ReactNode;
};

/**
 * Flask-safe adapter for the React Bits Pro Vortex API.
 * The live Flask surface uses static/js/vortex.js so the portal stays dependency-light.
 */
export function Vortex({
  discCount = 50,
  particleCount = 10000,
  particleColor = "#98E6BE",
  discColor = "rgba(152,230,190,.22)",
  discLineWidth = 1,
  particleSize = 0.5,
  depth = 1.7,
  spread = 1,
  speed = 0.05,
  rotationDirection = 1,
  centerX = 0.5,
  centerY = 0,
  opacity = 1,
  enableCursorInteraction = true,
  cursorInfluence = 0.1,
  children,
  className,
  style,
  ...props
}: VortexProps) {
  const ref = React.useRef<HTMLCanvasElement>(null);

  React.useEffect(() => {
    const canvas = ref.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const pointer = { x: 0.5, y: 0.5, active: false };
    let width = 0;
    let height = 0;
    let frame = 0;
    const rings = Math.max(12, discCount);
    const particles = Array.from({ length: Math.min(16000, Math.max(500, particleCount / 6)) }, (_, index) => ({
      angle: (index / particleCount) * Math.PI * 2,
      radius: Math.random(),
      depth: Math.random(),
      seed: Math.random() * Math.PI * 2,
    }));

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (time: number) => {
      const focalX = width * (centerX + (pointer.active && enableCursorInteraction ? (pointer.x - 0.5) * cursorInfluence : 0));
      const focalY = height * (centerY + (pointer.active && enableCursorInteraction ? (pointer.y - 0.5) * cursorInfluence * 0.45 : 0));
      context.clearRect(0, 0, width, height);
      context.globalAlpha = opacity;
      context.strokeStyle = discColor;
      context.lineWidth = discLineWidth;
      for (let ring = 1; ring <= rings; ring += 1) {
        const scale = ring / rings;
        const w = width * scale * spread * 0.95;
        const h = height * scale * depth * 0.6;
        context.beginPath();
        context.ellipse(focalX, focalY, w, h, 0, 0, Math.PI * 2);
        context.stroke();
      }
      context.fillStyle = particleColor;
      particles.forEach((particle) => {
        const orbit = particle.angle + time * speed * rotationDirection * 0.001 + particle.seed;
        const tunnel = Math.max(0.03, particle.radius + Math.sin(time * 0.0004 + particle.seed) * 0.04);
        const scale = 0.3 + tunnel * 1.8;
        const x = focalX + Math.cos(orbit) * width * tunnel * spread * 0.52;
        const y = focalY + Math.sin(orbit) * height * tunnel * depth * 0.32;
        context.globalAlpha = opacity * (0.12 + particle.depth * 0.72) * Math.max(0.2, 1 - tunnel * 0.55);
        context.beginPath();
        context.arc(x, y, Math.max(0.35, particleSize * scale), 0, Math.PI * 2);
        context.fill();
      });
      context.globalAlpha = 1;
      if (!motion.matches) frame = requestAnimationFrame(draw);
    };

    const move = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = (event.clientX - rect.left) / rect.width;
      pointer.y = (event.clientY - rect.top) / rect.height;
      pointer.active = true;
    };
    const leave = () => { pointer.active = false; };

    resize();
    draw(0);
    window.addEventListener("resize", resize);
    canvas.addEventListener("pointermove", move);
    canvas.addEventListener("pointerleave", leave);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("pointermove", move);
      canvas.removeEventListener("pointerleave", leave);
    };
  }, [centerX, centerY, cursorInfluence, depth, discColor, discCount, discLineWidth, enableCursorInteraction, opacity, particleColor, particleCount, particleSize, rotationDirection, spread, speed]);

  return <div className={className} style={{ position: "relative", overflow: "hidden", ...style }} {...props}>
    <canvas ref={ref} aria-hidden="true" style={{ display: "block", width: "100%", height: "100%" }} />
    {children ? <div style={{ position: "absolute", inset: 0 }}>{children}</div> : null}
  </div>;
}

export default Vortex;
