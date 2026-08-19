import React, { useEffect, useRef } from 'react';

interface Meteor {
  x: number;
  y: number;
  length: number;
  speed: number;
  angle: number;
  opacity: number;
}

interface Asteroid {
  x: number;
  y: number;
  radius: number;
  rotSpeed: number;
  angle: number;
  vx: number;
  vy: number;
  points: { x: number; y: number }[];
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

    // Stars (Glowing Amber/Yellow Twinkling)
    const starCount = 180;
    const stars = Array.from({ length: starCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      size: Math.random() * 1.6 + 0.4,
      alpha: Math.random() * 0.8 + 0.2,
      delta: (Math.random() * 0.015 + 0.005) * (Math.random() > 0.5 ? 1 : -1),
    }));

    // Meteors (Amber / Dark Yellow Trails)
    const meteors: Meteor[] = Array.from({ length: 6 }, () => createMeteor(width, height));

    function createMeteor(w: number, h: number): Meteor {
      return {
        x: Math.random() * w * 1.5 - w * 0.25,
        y: Math.random() * -200,
        length: Math.random() * 90 + 50,
        speed: Math.random() * 6 + 4,
        angle: Math.PI / 4 + (Math.random() * 0.1 - 0.05),
        opacity: Math.random() * 0.8 + 0.2,
      };
    }

    // 3D Wireframe Asteroids (Golden Cybernetic Rocks)
    const asteroidCount = 7;
    const asteroids: Asteroid[] = Array.from({ length: asteroidCount }, () => {
      const radius = Math.random() * 24 + 14;
      const numPoints = Math.floor(Math.random() * 4) + 6;
      const points = [];
      for (let i = 0; i < numPoints; i++) {
        const a = (i / numPoints) * Math.PI * 2;
        const r = radius * (0.7 + Math.random() * 0.6);
        points.push({ x: Math.cos(a) * r, y: Math.sin(a) * r });
      }
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        radius,
        rotSpeed: (Math.random() - 0.5) * 0.012,
        angle: Math.random() * Math.PI * 2,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        points,
      };
    });

    const draw = () => {
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, width, height);

      // Render Stars
      stars.forEach((star) => {
        star.alpha += star.delta;
        if (star.alpha <= 0.2 || star.alpha >= 1) star.delta *= -1;

        ctx.fillStyle = `rgba(245, 158, 11, ${star.alpha})`;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Render Meteors
      meteors.forEach((m, idx) => {
        m.x += Math.cos(m.angle) * m.speed;
        m.y += Math.sin(m.angle) * m.speed;

        if (m.y > height + 200 || m.x > width + 200) {
          meteors[idx] = createMeteor(width, height);
        }

        const grad = ctx.createLinearGradient(
          m.x,
          m.y,
          m.x - Math.cos(m.angle) * m.length,
          m.y - Math.sin(m.angle) * m.length
        );
        grad.addColorStop(0, `rgba(253, 224, 71, ${m.opacity})`);
        grad.addColorStop(0.4, `rgba(245, 158, 11, ${m.opacity * 0.6})`);
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.moveTo(m.x, m.y);
        ctx.lineTo(
          m.x - Math.cos(m.angle) * m.length,
          m.y - Math.sin(m.angle) * m.length
        );
        ctx.stroke();
      });

      // Render Asteroids
      asteroids.forEach((ast) => {
        ast.x += ast.vx;
        ast.y += ast.vy;
        ast.angle += ast.rotSpeed;

        if (ast.x < -50) ast.x = width + 50;
        if (ast.x > width + 50) ast.x = -50;
        if (ast.y < -50) ast.y = height + 50;
        if (ast.y > height + 50) ast.y = -50;

        ctx.save();
        ctx.translate(ast.x, ast.y);
        ctx.rotate(ast.angle);

        ctx.strokeStyle = 'rgba(217, 119, 6, 0.45)';
        ctx.lineWidth = 1.2;
        ctx.fillStyle = 'rgba(20, 18, 10, 0.6)';

        ctx.beginPath();
        ast.points.forEach((p, i) => {
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        });
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        ctx.restore();
      });

      animId = requestAnimationFrame(draw);
    };

    draw();

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
