import React, { useEffect, useRef } from 'react';

interface Meteor {
  x: number;
  y: number;
  length: number;
  speed: number;
  angle: number;
  opacity: number;
  tailOpacity: number;
  width: number;
}

interface Asteroid {
  x: number;
  y: number;
  radius: number;
  points: number[];
  rotation: number;
  rotSpeed: number;
  dx: number;
  dy: number;
  opacity: number;
}

interface Star {
  x: number;
  y: number;
  radius: number;
  opacity: number;
  twinkleSpeed: number;
}

export const BackgroundSpaceCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    // Initialize Stars
    const stars: Star[] = Array.from({ length: 160 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 1.5 + 0.5,
      opacity: Math.random() * 0.8 + 0.2,
      twinkleSpeed: (Math.random() - 0.5) * 0.015,
    }));

    // Initialize Asteroids
    const createAsteroid = (): Asteroid => {
      const radius = Math.random() * 16 + 10;
      const numVertices = Math.floor(Math.random() * 4) + 6;
      const points = Array.from({ length: numVertices }, () => 0.7 + Math.random() * 0.6);
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        radius,
        points,
        rotation: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.008,
        dx: (Math.random() - 0.5) * 0.3,
        dy: (Math.random() - 0.5) * 0.3,
        opacity: Math.random() * 0.35 + 0.15,
      };
    };
    const asteroids: Asteroid[] = Array.from({ length: 14 }, createAsteroid);

    // Initialize Meteors
    const createMeteor = (): Meteor => ({
      x: Math.random() * width * 1.5 - width * 0.25,
      y: -50,
      length: Math.random() * 120 + 80,
      speed: Math.random() * 8 + 6,
      angle: Math.PI / 4 + (Math.random() - 0.5) * 0.1,
      opacity: Math.random() * 0.8 + 0.2,
      tailOpacity: Math.random() * 0.5 + 0.3,
      width: Math.random() * 1.8 + 1,
    });
    const meteors: Meteor[] = Array.from({ length: 4 }, createMeteor);

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Render Twinkling Stars
      stars.forEach((star) => {
        star.opacity += star.twinkleSpeed;
        if (star.opacity > 0.95 || star.opacity < 0.15) {
          star.twinkleSpeed = -star.twinkleSpeed;
        }
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${star.opacity.toFixed(2)})`;
        ctx.fill();
      });

      // Render Floating Asteroids
      asteroids.forEach((ast) => {
        ast.x += ast.dx;
        ast.y += ast.dy;
        ast.rotation += ast.rotSpeed;

        if (ast.x < -40) ast.x = width + 40;
        if (ast.x > width + 40) ast.x = -40;
        if (ast.y < -40) ast.y = height + 40;
        if (ast.y > height + 40) ast.y = -40;

        ctx.save();
        ctx.translate(ast.x, ast.y);
        ctx.rotate(ast.rotation);
        ctx.beginPath();

        const numPoints = ast.points.length;
        for (let i = 0; i < numPoints; i++) {
          const angle = (i / numPoints) * Math.PI * 2;
          const r = ast.radius * ast.points[i];
          const px = Math.cos(angle) * r;
          const py = Math.sin(angle) * r;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.strokeStyle = `rgba(255, 255, 255, ${ast.opacity.toFixed(2)})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();

        ctx.fillStyle = `rgba(15, 15, 20, ${(ast.opacity * 0.6).toFixed(2)})`;
        ctx.fill();
        ctx.restore();
      });

      // Render Meteors
      meteors.forEach((m, idx) => {
        m.x += Math.cos(m.angle) * m.speed;
        m.y += Math.sin(m.angle) * m.speed;

        if (m.y > height + 100 || m.x > width + 100) {
          meteors[idx] = createMeteor();
        }

        const tailX = m.x - Math.cos(m.angle) * m.length;
        const tailY = m.y - Math.sin(m.angle) * m.length;

        const grad = ctx.createLinearGradient(m.x, m.y, tailX, tailY);
        grad.addColorStop(0, `rgba(255, 255, 255, ${m.opacity})`);
        grad.addColorStop(0.3, `rgba(220, 220, 240, ${m.tailOpacity * 0.7})`);
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

        ctx.beginPath();
        ctx.moveTo(m.x, m.y);
        ctx.lineTo(tailX, tailY);
        ctx.strokeStyle = grad;
        ctx.lineWidth = m.width;
        ctx.stroke();

        // Meteor Head Glow
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.width * 1.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${m.opacity})`;
        ctx.shadowColor = '#ffffff';
        ctx.shadowBlur = 12;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
    />
  );
};
