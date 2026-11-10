"use client";

import { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { motion } from "framer-motion";

interface AnimatedLogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  className?: string;
  onComplete?: () => void;
}

const DEVANAGARI_S = "स";
const PARTICLE_COUNT = 60;

export function AnimatedLogo({
  size = "md",
  showText = true,
  className = "",
  onComplete,
}: AnimatedLogoProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const particlesRef = useRef<Array<{
    x: number;
    y: number;
    vx: number;
    vy: number;
    radius: number;
    color: string;
    phase: number;
    baseRadius: number;
  }>>([]);
  const animationId = useRef<number | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);

  const sizeMap = {
    sm: { width: 48, height: 48, fontSize: 24, particleScale: 0.5 },
    md: { width: 80, height: 80, fontSize: 40, particleScale: 1 },
    lg: { width: 120, height: 120, fontSize: 60, particleScale: 1.5 },
    xl: { width: 180, height: 180, fontSize: 90, particleScale: 2 },
  };

  const { width, height, fontSize, particleScale } = sizeMap[size];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
    if (!ctx) return;

    // Set canvas size (account for device pixel ratio)
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Initialize particles
    const centerX = width / 2;
    const centerY = height / 2;

    particlesRef.current = Array.from({ length: PARTICLE_COUNT }, (_, i) => {
      const angle = (i / PARTICLE_COUNT) * Math.PI * 2;
      const radius = (width / 2) * 0.3 * particleScale;
      return {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        radius: Math.random() * 2 + 1,
        color: i % 3 === 0 ? "#6366f1" : i % 3 === 1 ? "#f97316" : "#14b8a6",
        phase: Math.random() * Math.PI * 2,
        baseRadius: radius,
      };
    });

    let frame = 0;

    const animate = () => {
      if (!ctx) return;

      ctx.clearRect(0, 0, width, height);

      // Get audio data if available
      let audioLevel = 0;
      if (analyserRef.current && dataArrayRef.current) {
        // Create a new Uint8Array for the data
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);
        audioLevel = dataArray.reduce((a, b) => a + b, 0) / dataArray.length / 255;
      }

      frame += 0.016;

      // Draw particles forming the Devanagari character shape
      particlesRef.current.forEach((particle, i) => {
        // Wave animation
        const waveOffset = Math.sin(frame * 3 + particle.phase) * 8 * particleScale;
        const audioBoost = audioLevel * 30 * particleScale;

        // Target position on the character shape
        const targetAngle = (i / PARTICLE_COUNT) * Math.PI * 2;
        const targetRadius = particle.baseRadius + waveOffset + audioBoost;
        const targetX = centerX + Math.cos(targetAngle) * targetRadius;
        const targetY = centerY + Math.sin(targetAngle) * targetRadius;

        // Spring physics
        particle.vx += (targetX - particle.x) * 0.08;
        particle.vy += (targetY - particle.y) * 0.08;
        particle.vx *= 0.85;
        particle.vy *= 0.85;
        particle.x += particle.vx;
        particle.y += particle.vy;

        // Draw particle
        const alpha = Math.max(0.3, 1 - Math.hypot(particle.x - centerX, particle.y - centerY) / (width / 2));
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.radius * (0.5 + audioLevel), 0, Math.PI * 2);
        ctx.fillStyle = `${particle.color}${Math.floor(alpha * 255).toString(16).padStart(2, "0")}`;
        ctx.fill();

        // Draw connections to nearby particles
        if (i % 3 === 0) {
          const nextIdx = (i + 1) % PARTICLE_COUNT;
          const next = particlesRef.current[nextIdx];
          ctx.beginPath();
          ctx.moveTo(particle.x, particle.y);
          ctx.lineTo(next.x, next.y);
          ctx.strokeStyle = `${particle.color}${Math.floor(alpha * 100).toString(16).padStart(2, "0")}`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      });

      // Draw central pulse
      const pulseRadius = 10 + Math.sin(frame * 4) * 5 + audioLevel * 20;
      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, pulseRadius);
      gradient.addColorStop(0, "rgba(99, 102, 241, 0.3)");
      gradient.addColorStop(0.5, "rgba(249, 115, 22, 0.1)");
      gradient.addColorStop(1, "rgba(20, 184, 166, 0)");
      ctx.beginPath();
      ctx.arc(centerX, centerY, pulseRadius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();

      animationId.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationId.current) cancelAnimationFrame(animationId.current);
    };
  }, [width, height, particleScale]);

  // Audio activation
  const activateAudio = async () => {
    if (audioContextRef.current) return;

    try {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      analyserRef.current.smoothingTimeConstant = 0.8;
      dataArrayRef.current = new Uint8Array(analyserRef.current.frequencyBinCount);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
    } catch (err) {
      console.warn("Audio access denied:", err);
    }
  };

  // Intersection observer for visibility
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          setTimeout(() => setIsAnimating(true), 100);
          if (onComplete) onComplete();
        }
      },
      { threshold: 0.5 }
    );

    if (wrapperRef.current) observer.observe(wrapperRef.current);
    return () => observer.disconnect();
  }, [onComplete]);

  return (
    <motion.div
      ref={wrapperRef}
      className={`inline-flex items-center gap-3 ${className}`}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
    >
      <div className="relative" onClick={activateAudio}>
        <canvas
          ref={canvasRef}
          className="block"
          aria-hidden="true"
        />
        {!isAnimating && (
          <motion.div
            className="absolute inset-0 flex items-center justify-center text-text-muted transition-opacity duration-300"
            animate={{ opacity: isAnimating ? 0 : 1 }}
          >
            <span
              className="font-display text-text-primary"
              style={{ fontSize: `${fontSize}px`, fontWeight: 700 }}
            >
              {DEVANAGARI_S}
            </span>
          </motion.div>
        )}
      </div>

      {showText && (
        <motion.div
          className="flex flex-col leading-tight"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
        >
          <span className="font-display font-extrabold text-text-primary bg-gradient-to-r from-brand-indigo-400 via-brand-saffron-400 to-brand-mint-400 bg-clip-text text-transparent">
            {size === "sm" ? "SCHEME" : "SCHEME FINDER"}
          </span>
          <span className="font-body text-xs text-text-secondary tracking-widest uppercase">
            Voice of India
          </span>
        </motion.div>
      )}
    </motion.div>
  );
}

// Simplified logo for navigation
export function NavLogo({ className = "" }: { className?: string }) {
  return (
    <AnimatedLogo size="sm" showText={false} className={className} />
  );
}