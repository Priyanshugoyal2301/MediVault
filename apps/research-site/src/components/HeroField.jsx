import { useEffect, useRef } from 'react';

/**
 * Full-bleed ambient canvas — abstract longitudinal signal field.
 * Reduced-motion safe: paints a single static frame.
 */
export default function HeroField() {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return undefined;

    const ctx = canvas.getContext('2d', { alpha: true });
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf = 0;
    let running = true;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const { clientWidth: w, clientHeight: h } = canvas;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    window.addEventListener('resize', resize);

    const series = Array.from({ length: 7 }, (_, i) => ({
      phase: i * 0.7,
      amp: 18 + i * 6,
      y: 0.28 + i * 0.08,
      speed: 0.00025 + i * 0.00004,
      alpha: 0.08 + i * 0.02,
    }));

    const draw = (t) => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      // Soft vertical wash
      const g = ctx.createLinearGradient(0, 0, w * 0.9, h);
      g.addColorStop(0, 'rgba(11, 46, 51, 0.03)');
      g.addColorStop(0.5, 'rgba(61, 155, 143, 0.05)');
      g.addColorStop(1, 'rgba(43, 107, 138, 0.04)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);

      // Faint grid
      ctx.strokeStyle = 'rgba(11, 46, 51, 0.045)';
      ctx.lineWidth = 1;
      const step = 48;
      for (let x = 0; x < w; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // Longitudinal curves
      series.forEach((s) => {
        ctx.beginPath();
        for (let x = 0; x <= w; x += 4) {
          const nx = x / w;
          const y =
            h * s.y +
            Math.sin(nx * Math.PI * 3 + s.phase + t * s.speed) * s.amp +
            Math.sin(nx * Math.PI * 7 + s.phase * 1.4) * (s.amp * 0.25);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = `rgba(33, 122, 113, ${s.alpha})`;
        ctx.lineWidth = 1.25;
        ctx.stroke();
      });

      // Sparse particles along a mid ridge
      for (let i = 0; i < 28; i += 1) {
        const px = ((i * 97 + t * 0.018) % (w + 40)) - 20;
        const py =
          h * 0.55 +
          Math.sin(i * 0.8 + t * 0.0008) * 40 +
          Math.cos(i * 1.3) * 16;
        const r = 1.2 + (i % 3) * 0.6;
        ctx.beginPath();
        ctx.fillStyle = `rgba(61, 155, 143, ${0.15 + (i % 5) * 0.04})`;
        ctx.arc(px, py, r, 0, Math.PI * 2);
        ctx.fill();
      }

      // Focal orb
      const ox = w * 0.72;
      const oy = h * 0.42;
      const orb = ctx.createRadialGradient(ox, oy, 0, ox, oy, 120);
      orb.addColorStop(0, 'rgba(61, 155, 143, 0.18)');
      orb.addColorStop(1, 'rgba(61, 155, 143, 0)');
      ctx.fillStyle = orb;
      ctx.beginPath();
      ctx.arc(ox, oy, 120, 0, Math.PI * 2);
      ctx.fill();
    };

    if (reduce) {
      draw(0);
    } else {
      const loop = (now) => {
        if (!running) return;
        draw(now);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return <canvas ref={ref} className="home-hero__canvas" aria-hidden="true" />;
}
