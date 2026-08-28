import { useEffect, useRef } from 'react';

/** Abstract medical signal panel for hero visual column */
export default function SignalPanel() {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf = 0;
    let running = true;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    const points = [0.42, 0.45, 0.44, 0.48, 0.52, 0.55, 0.61, 0.68, 0.72];

    const paint = (t) => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      // Panel wash
      const bg = ctx.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, 'rgba(255,255,255,0.25)');
      bg.addColorStop(1, 'rgba(212,232,228,0.15)');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      // Axes
      const pad = 36;
      ctx.strokeStyle = 'rgba(11,46,51,0.12)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad, pad);
      ctx.lineTo(pad, h - pad);
      ctx.lineTo(w - pad, h - pad);
      ctx.stroke();

      // Series polyline
      const n = points.length;
      ctx.beginPath();
      points.forEach((p, i) => {
        const x = pad + ((w - pad * 2) * i) / (n - 1);
        const breathe = reduce ? 0 : Math.sin(t * 0.0012 + i * 0.4) * 0.012;
        const y = h - pad - (h - pad * 2) * (p + breathe);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = 'rgba(33,122,113,0.85)';
      ctx.lineWidth = 2.25;
      ctx.stroke();

      // Area fill
      ctx.lineTo(w - pad, h - pad);
      ctx.lineTo(pad, h - pad);
      ctx.closePath();
      const fill = ctx.createLinearGradient(0, pad, 0, h - pad);
      fill.addColorStop(0, 'rgba(61,155,143,0.22)');
      fill.addColorStop(1, 'rgba(61,155,143,0)');
      ctx.fillStyle = fill;
      ctx.fill();

      // Points
      points.forEach((p, i) => {
        const x = pad + ((w - pad * 2) * i) / (n - 1);
        const breathe = reduce ? 0 : Math.sin(t * 0.0012 + i * 0.4) * 0.012;
        const y = h - pad - (h - pad * 2) * (p + breathe);
        ctx.beginPath();
        ctx.fillStyle = i === n - 1 ? '#0B2E33' : '#3D9B8F';
        ctx.arc(x, y, i === n - 1 ? 4.5 : 3, 0, Math.PI * 2);
        ctx.fill();
      });

      // Labels
      ctx.fillStyle = 'rgba(11,46,51,0.45)';
      ctx.font = '500 11px "Space Grotesk", sans-serif';
      ctx.fillText('PERSONAL SERIES  ·  LDL  ·  LEAVE-LAST-OUT z', pad, 22);
      ctx.fillText('causal monitor  ·  demo synthetic trend', pad, h - 14);
    };

    if (reduce) {
      paint(0);
    } else {
      const loop = (now) => {
        if (!running) return;
        paint(now);
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

  return (
    <canvas
      ref={ref}
      className="tile-art"
      style={{ width: '100%', height: '100%' }}
      aria-hidden="true"
    />
  );
}
