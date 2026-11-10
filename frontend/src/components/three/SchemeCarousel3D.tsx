"use client";

import { useRef, useEffect, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  Html,
  OrbitControls,
  Stars,
  RoundedBox,
  Text,
  useGLTF,
} from "@react-three/drei";
import * as THREE from "three";
import { motion } from "framer-motion";
import gsap from "gsap";

// Scheme data
interface Scheme {
  id: string;
  name: string;
  nameHi: string;
  description: string;
  category: string;
  color: number;
  icon: string;
  beneficiaries: string;
  launchYear: number;
}

const SCHEMES: Scheme[] = [
  {
    id: "pm-kisan",
    name: "PM-KISAN",
    nameHi: "पीएम-किसान",
    description: "Income support of ₹6,000/year for small & marginal farmers",
    category: "Agriculture",
    color: 0x14b8a6,
    icon: "🌾",
    beneficiaries: "11+ Cr farmers",
    launchYear: 2019,
  },
  {
    id: "ayushman-bharat",
    name: "Ayushman Bharat",
    nameHi: "आयुष्मान भारत",
    description: "Health insurance cover of ₹5 lakh per family per year",
    category: "Healthcare",
    color: 0xf97316,
    icon: "🏥",
    beneficiaries: "50+ Cr citizens",
    launchYear: 2018,
  },
  {
    id: "pm-awas-yojana",
    name: "PM Awas Yojana",
    nameHi: "पीएम आवास योजना",
    description: "Affordable housing for urban & rural poor",
    category: "Housing",
    color: 0x6366f1,
    icon: "🏠",
    beneficiaries: "3+ Cr houses",
    launchYear: 2015,
  },
  {
    id: "jal-jeevan-mission",
    name: "Jal Jeevan Mission",
    nameHi: "जल जीवन मिशन",
    description: "Safe drinking water to every rural household by 2024",
    category: "Water",
    color: 0x3b82f6,
    icon: "💧",
    beneficiaries: "19+ Cr households",
    launchYear: 2019,
  },
  {
    id: "digital-india",
    name: "Digital India",
    nameHi: "डिजिटल इंडिया",
    description: "Transform India into digitally empowered society",
    category: "Technology",
    color: 0x8b5cf6,
    icon: "💻",
    beneficiaries: "130+ Cr citizens",
    launchYear: 2015,
  },
  {
    id: "skill-india",
    name: "Skill India",
    nameHi: "स्किल इंडिया",
    description: "Skill development & vocational training for youth",
    category: "Education",
    color: 0xec4899,
    icon: "🎓",
    beneficiaries: "5+ Cr trained",
    launchYear: 2015,
  },
  {
    id: "swachh-bharat",
    name: "Swachh Bharat Mission",
    nameHi: "स्वच्छ भारत मिशन",
    description: "Clean India - sanitation & waste management",
    category: "Sanitation",
    color: 0x22c55e,
    icon: "🗑️",
    beneficiaries: "100+ Cr citizens",
    launchYear: 2014,
  },
  {
    id: "udyam-registration",
    name: "Udyam Registration",
    nameHi: "उद्यम पंजीकरण",
    description: "Simplified registration for MSMEs with benefits",
    category: "Business",
    color: 0xf59e0b,
    icon: "🏭",
    beneficiaries: "3+ Cr MSMEs",
    launchYear: 2020,
  },
];

// Carousel item component
function CarouselItem({ 
  scheme, 
  index, 
  isActive, 
  onSelect,
  rotation,
  radius 
}: { 
  scheme: Scheme; 
  index: number; 
  isActive: boolean; 
  onSelect: (id: string) => void;
  rotation: number;
  radius: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [isHovered, setIsHovered] = useState(false);
  const { viewport } = useThree();

  // Calculate position on circle
  const angle = rotation + (index / SCHEMES.length) * Math.PI * 2;
  const x = Math.cos(angle) * radius;
  const z = Math.sin(angle) * radius;
  const y = isActive ? 1.5 : 0;

  useFrame((_, delta) => {
    if (meshRef.current) {
      // Gentle floating animation
      meshRef.current.position.y = y + Math.sin(Date.now() * 0.001 + index) * 0.1;
      
      // Rotate slowly when active
      if (isActive) {
        meshRef.current.rotation.y += delta * 0.3;
      }
      
      // Scale pulse when active
      const targetScale = isActive ? 1.15 : 1;
      meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), delta * 5);
    }
  });

  return (
    <group
      position={[x, y, z]}
      rotation={[0, -angle + Math.PI / 2, 0]}
      onClick={() => onSelect(scheme.id)}
      onPointerOver={() => setIsHovered(true)}
      onPointerOut={() => setIsHovered(false)}
    >
      {/* Main card box */}
      <RoundedBox
        ref={meshRef}
        args={[2.8, 3.5, 0.4, 0.2]}
        color={scheme.color}
        position={[0, 0, 0]}
      >
        <meshStandardMaterial
          metalness={0.1}
          roughness={0.7}
          transparent
          opacity={isActive || isHovered ? 0.95 : 0.8}
          emissive={new THREE.Color(scheme.color)}
          emissiveIntensity={isActive ? 0.3 : isHovered ? 0.15 : 0}
        />
      </RoundedBox>

      {/* Card content - front face */}
      <Html
        transform
        position={[0, 0, 0.45]}
        style={{
          pointerEvents: "none",
          width: "260px",
          textAlign: "center",
          padding: "1.5rem",
        }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ 
            opacity: isActive ? 1 : 0.85, 
            scale: isActive ? 1 : 0.95 
          }}
          transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
          style={{
            background: `rgba(26, 26, 36, ${isActive ? 0.95 : 0.85})`,
            borderRadius: "1rem",
            border: `1px solid ${isActive ? `rgba(${scheme.color.toString(16).padStart(6, '0')}, 0.5)` : "rgba(255,255,255,0.1)"}`,
            backdropFilter: "blur(20px)",
            padding: "1.5rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.75rem",
            minHeight: "300px",
            justifyContent: "space-between",
          }}
        >
          {/* Icon */}
          <div style={{ fontSize: "3rem", lineHeight: 1 }}>{scheme.icon}</div>
          
          {/* Names */}
          <div>
            <motion.h3
              key={scheme.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "1.25rem",
                fontWeight: 700,
                color: "#fff",
                margin: 0,
              }}
            >
              {scheme.name}
            </motion.h3>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              style={{
                fontFamily: "var(--font-body)",
                fontSize: "0.9rem",
                color: "#a1a1aa",
                margin: "0.25rem 0 0",
              }}
            >
              {scheme.nameHi}
            </motion.p>
          </div>
          
          {/* Category badge */}
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.15 }}
            style={{
              display: "inline-block",
              padding: "0.25rem 0.75rem",
              borderRadius: "9999px",
              fontSize: "0.7rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              background: `rgba(${scheme.color.toString(16).padStart(6, '0')}, 0.2)`,
              color: `#${scheme.color.toString(16).padStart(6, '0')}`,
              border: `1px solid rgba(${scheme.color.toString(16).padStart(6, '0')}, 0.4)`,
            }}
          >
            {scheme.category}
          </motion.span>
          
          {/* Description */}
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            style={{
              fontSize: "0.85rem",
              lineHeight: 1.5,
              color: "#d4d4d8",
              margin: 0,
              fontFamily: "var(--font-body)",
            }}
          >
            {scheme.description}
          </motion.p>
          
          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            style={{
              display: "flex",
              justifyContent: "space-between",
              paddingTop: "0.5rem",
              borderTop: "1px solid rgba(255,255,255,0.1)",
              fontSize: "0.75rem",
              color: "#71717a",
              fontFamily: "var(--font-mono)",
            }}
          >
            <span>👥 {scheme.beneficiaries}</span>
            <span>📅 {scheme.launchYear}</span>
          </motion.div>
          
          {/* Active indicator */}
          {isActive && (
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{
                marginTop: "1rem",
                padding: "0.5rem 1rem",
                borderRadius: "9999px",
                fontSize: "0.75rem",
                fontWeight: 600,
                color: "#fff",
                background: `linear-gradient(135deg, #${scheme.color.toString(16).padStart(6, '0')} 0%, #${(scheme.color + 0x222222).toString(16).padStart(6, '0')} 100%)`,
                boxShadow: `0 0 20px -5px #${scheme.color.toString(16).padStart(6, '0')}`,
              }}
            >
              ✨ Tap to explore
            </motion.div>
          )}
        </motion.div>
      </Html>

      {/* Glow ring behind active card */}
      {isActive && (
        <mesh position={[0, 0, -0.1]} scale={1.3}>
          <ringGeometry args={[3, 4.5, 64]} />
          <meshBasicMaterial
            color={scheme.color}
            transparent
            opacity={0.15}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      )}

      {/* Floating particles around active card */}
      {isActive && <ActiveParticles color={scheme.color} />}
    </group>
  );
}

// Particle effect for active card
function ActiveParticles({ color }: { color: number }) {
  const pointsRef = useRef<THREE.Points>(null);
  const particlesRef = useRef<Array<{
    position: THREE.Vector3;
    velocity: THREE.Vector3;
    life: number;
    maxLife: number;
    size: number;
  }>>([]);

  useEffect(() => {
    // Initialize particles
    for (let i = 0; i < 30; i++) {
      particlesRef.current.push({
        position: new THREE.Vector3(
          (Math.random() - 0.5) * 4,
          (Math.random() - 0.5) * 5,
          (Math.random() - 0.5) * 2
        ),
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * 0.5,
          Math.random() * 0.5 + 0.2,
          (Math.random() - 0.5) * 0.5
        ),
        life: Math.random(),
        maxLife: 1,
        size: Math.random() * 0.08 + 0.04,
      });
    }
  }, []);

  useFrame((_, delta) => {
    if (!pointsRef.current) return;

    const positions = new Float32Array(particlesRef.current.length * 3);
    const colors = new Float32Array(particlesRef.current.length * 3);
    const sizes = new Float32Array(particlesRef.current.length);

    particlesRef.current.forEach((particle, i) => {
      // Update position
      particle.position.addScaledVector(particle.velocity, delta);
      particle.life += delta / 3;
      
      // Reset if dead
      if (particle.life >= particle.maxLife) {
        particle.position.set(
          (Math.random() - 0.5) * 4,
          -2.5 + Math.random() * 1,
          (Math.random() - 0.5) * 2
        );
        particle.velocity.set(
          (Math.random() - 0.5) * 0.5,
          Math.random() * 0.5 + 0.2,
          (Math.random() - 0.5) * 0.5
        );
        particle.life = 0;
        particle.size = Math.random() * 0.08 + 0.04;
      }

      positions[i * 3] = particle.position.x;
      positions[i * 3 + 1] = particle.position.y;
      positions[i * 3 + 2] = particle.position.z;
      
      const particleColor = new THREE.Color(color);
      const alpha = 1 - particle.life / particle.maxLife;
      colors[i * 3] = particleColor.r;
      colors[i * 3 + 1] = particleColor.g;
      colors[i * 3 + 2] = particleColor.b;
      
      sizes[i] = particle.size * alpha;
    });

    pointsRef.current.geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    pointsRef.current.geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    pointsRef.current.geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
    pointsRef.current.geometry.attributes.color.needsUpdate = true;
    pointsRef.current.geometry.attributes.size.needsUpdate = true;
  });

  useEffect(() => {
    if (!pointsRef.current) return;
    
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particlesRef.current.length * 3);
    const colors = new Float32Array(particlesRef.current.length * 3);
    const sizes = new Float32Array(particlesRef.current.length);
    
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));
    
    const material = new THREE.PointsMaterial({
      size: 0.1,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
      sizeAttenuation: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    
    pointsRef.current.geometry = geometry;
    pointsRef.current.material = material;
  }, []);

  return <points ref={pointsRef} />;
}

// Main carousel component
function SchemeCarousel3DInner() {
  const [activeIndex, setActiveIndex] = useState(0);
  const rotationRef = useRef(0);
  const targetRotationRef = useRef(0);
  const radius = 10;
  const [autoRotate, setAutoRotate] = useState(true);

  // Auto-rotate
  useFrame((_, delta) => {
    if (autoRotate) {
      targetRotationRef.current -= delta * 0.15;
    }
    
    // Smooth rotation interpolation
    rotationRef.current += (targetRotationRef.current - rotationRef.current) * delta * 3;
  });

  const handleSelect = (id: string) => {
    const index = SCHEMES.findIndex(s => s.id === id);
    if (index !== -1) {
      setActiveIndex(index);
      setAutoRotate(false);
      
      // Calculate target rotation to bring selected item to front
      const targetAngle = -((index / SCHEMES.length) * Math.PI * 2) + Math.PI / 2;
      targetRotationRef.current = targetAngle;
      
      // Resume auto-rotate after 5 seconds
      setTimeout(() => setAutoRotate(true), 5000);
    }
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        const newIndex = (activeIndex - 1 + SCHEMES.length) % SCHEMES.length;
        handleSelect(SCHEMES[newIndex].id);
      } else if (e.key === "ArrowRight") {
        const newIndex = (activeIndex + 1) % SCHEMES.length;
        handleSelect(SCHEMES[newIndex].id);
      }
    };
    
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeIndex]);

  return (
    <group rotation={[0, rotationRef.current, 0]}>
      {SCHEMES.map((scheme, index) => (
        <CarouselItem
          key={scheme.id}
          scheme={scheme}
          index={index}
          isActive={index === activeIndex}
          onSelect={handleSelect}
          rotation={rotationRef.current}
          radius={radius}
        />
      ))}
      
      {/* Center indicator */}
      <Html
        transform
        position={[0, -3.5, 0]}
        style={{ pointerEvents: "none", textAlign: "center" }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 0.6, y: 0 }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.5rem 1rem",
            borderRadius: "9999px",
            background: "rgba(26, 26, 36, 0.9)",
            border: "1px solid rgba(255,255,255,0.1)",
            backdropFilter: "blur(20px)",
            fontSize: "0.85rem",
            color: "#a1a1aa",
            fontFamily: "var(--font-body)",
          }}
        >
          <kbd style={{
            padding: "0.15rem 0.5rem",
            borderRadius: "0.25rem",
            background: "rgba(255,255,255,0.1)",
            border: "1px solid rgba(255,255,255,0.1)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.7rem",
          }}>←</kbd>
          <span>Navigate schemes</span>
          <kbd style={{
            padding: "0.15rem 0.5rem",
            borderRadius: "0.25rem",
            background: "rgba(255,255,255,0.1)",
            border: "1px solid rgba(255,255,255,0.1)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.7rem",
          }}>→</kbd>
        </motion.div>
      </Html>
    </group>
  );
}

// Export the main component
export function SchemeCarousel3D() {
  return (
    <div style={{ width: "100%", height: "100%", minHeight: "600px" }}>
      <Canvas
        camera={{ position: [0, 2, 18], fov: 35 }}
        gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
        onCreated={({ gl }) => {
          gl.setClearColor(0x0a0a0f, 1);
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.3;
        }}
      >
        <color attach="background" args={[0x0a0a0f]} />
        <fog attach="fog" args={[0x0a0a0f, 10, 50]} />
        
        {/* Lighting */}
        <ambientLight intensity={0.5} color={0xffffff} />
        <directionalLight position={[0, 10, 10]} intensity={1.2} color={0xffffff} />
        <pointLight position={[-12, 5, 0]} color={0x6366f1} intensity={2} distance={30} decay={2} />
        <pointLight position={[12, 5, 0]} color={0xf97316} intensity={2} distance={30} decay={2} />
        <pointLight position={[0, 8, 0]} color={0x14b8a6} intensity={1.5} distance={30} decay={2} />
        
        {/* Stars */}
        <Stars radius={80} depth={100} count={5000} factor={4} saturation={0} fade />
        
        {/* Controls */}
        <OrbitControls
          enablePan={false}
          enableZoom={true}
          enableRotate={true}
          minDistance={12}
          maxDistance={30}
          maxPolarAngle={Math.PI / 2 - 0.05}
          autoRotate={false}
        />
        
        {/* Carousel */}
        <SchemeCarousel3DInner />
      </Canvas>
    </div>
  );
}