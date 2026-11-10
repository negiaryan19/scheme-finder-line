"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";

interface CursorFollowerProps {
  enabled?: boolean;
}

export function CursorFollower({ enabled = true }: CursorFollowerProps) {
  const cursorRef = useRef<HTMLDivElement | null>(null);
  const trailRefs = useRef<HTMLDivElement[]>([]);
  const mousePos = { x: 0, y: 0 };
  const cursorPos = { x: 0, y: 0 };
  const trailPositions = Array(8).fill({ x: 0, y: 0 });
  const animationId = useRef<number | null>(null);
  const isActive = useRef(false);
  const magneticTargets = useRef<HTMLElement[]>([]);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    // Create cursor elements
    const cursor = document.createElement("div");
    cursor.className = "cursor-follower";
    cursor.style.cssText = `
      position: fixed;
      pointer-events: none;
      z-index: 9999;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: radial-gradient(circle at center, #f97316 0%, transparent 70%);
      opacity: 0;
      mix-blend-mode: screen;
      transition: opacity 0.2s ease;
      will-change: transform;
    `;
    document.body.appendChild(cursor);
    cursorRef.current = cursor;

    // Create trail elements
    for (let i = 0; i < 8; i++) {
      const trail = document.createElement("div");
      trail.className = "cursor-trail";
      trail.style.cssText = `
        position: fixed;
        pointer-events: none;
        z-index: 9998;
        width: ${24 - i * 2}px;
        height: ${24 - i * 2}px;
        border-radius: 50%;
        background: radial-gradient(circle at center, #6366f1 0%, transparent 70%);
        opacity: 0;
        mix-blend-mode: screen;
        will-change: transform;
      `;
      document.body.appendChild(trail);
      trailRefs.current.push(trail);
    }

    // Find magnetic targets
    const findMagneticTargets = () => {
      magneticTargets.current = Array.from(document.querySelectorAll<HTMLElement>(
        '[data-magnetic], .btn-magnetic, .card-magnetic, a, button, [role="button"]'
      ));
    };
    findMagneticTargets();

    // Mouse move handler
    const handleMouseMove = (e: MouseEvent) => {
      mousePos.x = e.clientX;
      mousePos.y = e.clientY;
      if (!isActive.current) {
        isActive.current = true;
        if (cursorRef.current) cursorRef.current.style.opacity = "1";
        trailRefs.current.forEach((trail, i) => {
          trail.style.opacity = String(0.6 - i * 0.07);
        });
      }
    };

    // Mouse leave handler
    const handleMouseLeave = () => {
      isActive.current = false;
      if (cursorRef.current) cursorRef.current.style.opacity = "0";
      trailRefs.current.forEach((trail) => {
        trail.style.opacity = "0";
      });
    };

    // Magnetic effect
    const handleMagneticMove = (e: MouseEvent) => {
      const target = e.currentTarget as HTMLElement;
      const rect = target.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const deltaX = (e.clientX - centerX) * 0.3;
      const deltaY = (e.clientY - centerY) * 0.3;

      gsap.to(target, {
        x: deltaX,
        y: deltaY,
        duration: 0.4,
        ease: "power3.out",
      });

      // Scale up slightly
      gsap.to(target, {
        scale: 1.05,
        duration: 0.3,
        ease: "power2.out",
      });
    };

    const handleMagneticLeave = (e: MouseEvent) => {
      const target = e.currentTarget as HTMLElement;
      gsap.to(target, {
        x: 0,
        y: 0,
        scale: 1,
        duration: 0.5,
        ease: "elastic.out(1, 0.5)",
      });
    };

    // Attach magnetic listeners
    magneticTargets.current.forEach((target) => {
      target.addEventListener("mousemove", handleMagneticMove);
      target.addEventListener("mouseleave", handleMagneticLeave);
    });

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseleave", handleMouseLeave);

    // Animation loop for smooth cursor following
    const animate = () => {
      // Smooth cursor follow
      cursorPos.x += (mousePos.x - cursorPos.x) * 0.3;
      cursorPos.y += (mousePos.y - cursorPos.y) * 0.3;

      if (cursorRef.current) {
        cursorRef.current.style.transform = `translate(${cursorPos.x - 16}px, ${cursorPos.y - 16}px)`;
      }

      // Trail follows with delay
      trailPositions.forEach((pos, i) => {
        const target = i === 0 ? cursorPos : trailPositions[i - 1];
        pos.x += (target.x - pos.x) * 0.25;
        pos.y += (target.y - pos.y) * 0.25;

        const trail = trailRefs.current[i];
        if (trail) {
          const size = 24 - i * 2;
          trail.style.transform = `translate(${pos.x - size / 2}px, ${pos.y - size / 2}px)`;
        }
      });

      animationId.current = requestAnimationFrame(animate);
    };

    animate();

    // MutationObserver to catch new magnetic elements
    const observer = new MutationObserver(() => {
      findMagneticTargets();
      magneticTargets.current.forEach((target) => {
        if (!target.dataset.magneticAttached) {
          target.dataset.magneticAttached = "true";
          target.addEventListener("mousemove", handleMagneticMove);
          target.addEventListener("mouseleave", handleMagneticLeave);
        }
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      if (animationId.current) cancelAnimationFrame(animationId.current);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
      magneticTargets.current.forEach((target) => {
        target.removeEventListener("mousemove", handleMagneticMove);
        target.removeEventListener("mouseleave", handleMagneticLeave);
      });
      observer.disconnect();
      cursorRef.current?.remove();
      trailRefs.current.forEach((trail) => trail.remove());
      cursorRef.current = null;
      trailRefs.current = [];
    };
  }, [enabled]);

  return null;
}