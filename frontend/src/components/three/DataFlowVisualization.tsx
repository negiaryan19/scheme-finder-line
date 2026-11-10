"use client";

import { useRef, useEffect, useMemo, useState } from "react";
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

// Particle data flow types
interface DataParticle {
  id: number;
  position: THREE.Vector3;
  targetPosition: THREE.Vector3;
  velocity: THREE.Vector3;
  color: THREE.Color;
  size: number;
  progress: number;
  stage: number; // 0: voice input, 1: STT, 2: LLM, 3: TTS, 4: audio output
}

// Stage positions for data flow visualization
const STAGE_POSITIONS = [
  new THREE.Vector3(-8, 0, 0),   // Voice Input
  new THREE.Vector3(-4, 0, 0),   // STT
  new THREE.Vector3(0, 0, 0),    // LLM/Scheme Matching
  new THREE.Vector3(4, 0, 0),    // TTS
  new THREE.Vector3(8, 0, 0),    // Audio Output
];

const STAGE_LABELS = [
  "Voice Input",
  "Prisma STT",
  "Evon LLM",
  "Timbre TTS",
  "Audio Output",
];

const STAGE_COLORS = [
  0x6366f1, // indigo
  0xf97316, // saffron
  0x14b8a6, // mint
  0xf97316, // saffron
  0x6366f1, // indigo
];

// Particle system component
function ParticleSystem() {
  const particlesRef = useRef<DataParticle[]>([]);
  const { viewport } = useThree();
  const timeRef = useRef(0);
  const spawnTimerRef = useRef(0);

  // Initialize particles
  useEffect(() => {
    const particleCount = 150;
    for (let i = 0; i < particleCount; i++) {
      const stage = Math.floor(Math.random() * 4);
      const startPos = STAGE_POSITIONS[stage].clone();
      const endPos = STAGE_POSITIONS[stage + 1].clone();
      
      // Add some vertical spread
      startPos.y += (Math.random() - 0.5) * 1.5;
      endPos.y += (Math.random() - 0.5) * 1.5;
      
      particlesRef.current.push({
        id: i,
        position: startPos.clone(),
        targetPosition: endPos.clone(),
        velocity: new THREE.Vector3(0, 0, 0),
        color: new THREE.Color(STAGE_COLORS[stage]),
        size: Math.random() * 0.08 + 0.04,
        progress: Math.random(),
        stage: stage,
      });
    }
  }, []);

  useFrame((_, delta) => {
    timeRef.current += delta;
    spawnTimerRef.current += delta;

    // Spawn new particles periodically
    if (spawnTimerRef.current > 0.3) {
      spawnTimerRef.current = 0;
      const stage = Math.floor(Math.random() * 4);
      const startPos = STAGE_POSITIONS[stage].clone();
      const endPos = STAGE_POSITIONS[stage + 1].clone();
      startPos.y += (Math.random() - 0.5) * 1.5;
      endPos.y += (Math.random() - 0.5) * 1.5;
      
      // Find a dead particle to recycle
      const deadParticle = particlesRef.current.find(p => p.progress >= 1);
      if (deadParticle) {
        deadParticle.position.copy(startPos);
        deadParticle.targetPosition.copy(endPos);
        deadParticle.color.setHex(STAGE_COLORS[stage]);
        deadParticle.stage = stage;
        deadParticle.progress = 0;
        deadParticle.velocity.set(0, 0, 0);
        deadParticle.size = Math.random() * 0.08 + 0.04;
      }
    }

    // Update particles
    particlesRef.current.forEach((particle) => {
      if (particle.progress >= 1) return;

      // Spring physics toward target
      const direction = new THREE.Vector3().subVectors(
        particle.targetPosition,
        particle.position
      );
      const distance = direction.length();
      
      if (distance > 0.01) {
        direction.normalize();
        particle.velocity.addScaledVector(direction, delta * 3);
        particle.velocity.multiplyScalar(0.92); // damping
        particle.position.addScaledVector(particle.velocity, delta);
        particle.progress = 1 - distance / STAGE_POSITIONS[0].distanceTo(STAGE_POSITIONS[1]);
      } else {
        particle.progress = 1;
      }

      // Color transition based on progress
      const nextStageColor = new THREE.Color(STAGE_COLORS[particle.stage + 1]);
      particle.color.lerp(nextStageColor, particle.progress);
    });
  });

  // Render particles as points
  const pointsRef = useRef<THREE.Points>(null);
  
  useEffect(() => {
    if (!pointsRef.current) return;
    
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particlesRef.current.length * 3);
    const colors = new Float32Array(particlesRef.current.length * 3);
    const sizes = new Float32Array(particlesRef.current.length);
    
    particlesRef.current.forEach((particle, i) => {
      positions[i * 3] = particle.position.x;
      positions[i * 3 + 1] = particle.position.y;
      positions[i * 3 + 2] = particle.position.z;
      colors[i * 3] = particle.color.r;
      colors[i * 3 + 1] = particle.color.g;
      colors[i * 3 + 2] = particle.color.b;
      sizes[i] = particle.size * (particle.progress > 0 && particle.progress < 1 ? 1 : 0.3);
    });
    
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

  // Update geometry each frame
  useFrame(() => {
    if (!pointsRef.current) return;
    
    const positions = pointsRef.current.geometry.attributes.position.array as Float32Array;
    const colors = pointsRef.current.geometry.attributes.color.array as Float32Array;
    const sizes = pointsRef.current.geometry.attributes.size.array as Float32Array;
    
    particlesRef.current.forEach((particle, i) => {
      positions[i * 3] = particle.position.x;
      positions[i * 3 + 1] = particle.position.y;
      positions[i * 3 + 2] = particle.position.z;
      colors[i * 3] = particle.color.r;
      colors[i * 3 + 1] = particle.color.g;
      colors[i * 3 + 2] = particle.color.b;
      sizes[i] = particle.size * (particle.progress > 0 && particle.progress < 1 ? 1 : 0.2);
    });
    
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
    pointsRef.current.geometry.attributes.color.needsUpdate = true;
    pointsRef.current.geometry.attributes.size.needsUpdate = true;
  });

  return <points ref={pointsRef} />;
}

// Connection lines between stages
function ConnectionLines() {
  const linesRef = useRef<THREE.Line[]>([]);
  const timeRef = useRef(0);

  useEffect(() => {
    // Create lines once
    if (linesRef.current.length === 0) {
      STAGE_POSITIONS.slice(0, -1).forEach((start, i) => {
        const end = STAGE_POSITIONS[i + 1];
        const curve = new THREE.QuadraticBezierCurve3(
          start.clone(),
          new THREE.Vector3((start.x + end.x) / 2, 0, 0),
          end.clone()
        );
        const points = curve.getPoints(20);
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineDashedMaterial({
          color: new THREE.Color().lerpColors(
            new THREE.Color(STAGE_COLORS[i]),
            new THREE.Color(STAGE_COLORS[i + 1]),
            0.5
          ),
          linewidth: 0.02,
          dashSize: 0.5,
          gapSize: 0.3,
          transparent: true,
          opacity: 0.4,
        });
        const line = new THREE.Line(geometry, material);
        line.computeLineDistances();
        linesRef.current.push(line);
      });
    }
  }, []);

  useFrame((_, delta) => {
    timeRef.current += delta;
    
    linesRef.current.forEach((line, i) => {
      // Animate dash offset for flow effect
      const material = line.material as THREE.LineDashedMaterial;
      if (material) {
        material.dashOffset = -timeRef.current * 2;
        material.needsUpdate = true;
      }
      
      // Update curve for animation
      const start = STAGE_POSITIONS[i];
      const end = STAGE_POSITIONS[i + 1];
      const midY = Math.sin(timeRef.current + i) * 0.3;
      const curve = new THREE.QuadraticBezierCurve3(
        start.clone(),
        new THREE.Vector3((start.x + end.x) / 2, midY, 0),
        end.clone()
      );
      const points = curve.getPoints(20);
      (line.geometry as THREE.BufferGeometry).setFromPoints(points);
      line.geometry.attributes.position.needsUpdate = true;
      line.computeLineDistances();
    });
  });

  return (
    <>
      {linesRef.current.map((line, i) => (
        <primitive key={i} object={line} />
      ))}
    </>
  );
}

// Stage node component
function StageNode({ index }: { index: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const { viewport } = useThree();
  const [isHovered, setIsHovered] = useState(false);
  
  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.005;
      meshRef.current.rotation.x = Math.sin(Date.now() * 0.001 + index) * 0.1;
      
      // Pulse scale
      const pulse = 1 + Math.sin(Date.now() * 0.003 + index * 2) * 0.05;
      meshRef.current.scale.setScalar(pulse);
    }
  });

  const position = STAGE_POSITIONS[index];
  const color = STAGE_COLORS[index];
  const label = STAGE_LABELS[index];

  return (
    <group
      onPointerOver={() => setIsHovered(true)}
      onPointerOut={() => setIsHovered(false)}
    >
      <RoundedBox
        ref={meshRef}
        args={[1.2, 1.2, 1.2, 0.2]}
        position={[position.x, position.y, position.z]}
        color={color}
        transparent
        opacity={isHovered ? 0.9 : 0.6}
      >
        <meshStandardMaterial
          emissive={new THREE.Color(color)}
          emissiveIntensity={isHovered ? 0.5 : 0.2}
          metalness={0.3}
          roughness={0.4}
        />
      </RoundedBox>
      
      {/* Floating label */}
      <Html
        transform
        position={[position.x, position.y - 1.8, position.z]}
        style={{
          pointerEvents: "none",
          textAlign: "center",
          whiteSpace: "nowrap",
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: isHovered ? 1 : 0.7, y: 0 }}
          transition={{ duration: 0.3 }}
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "#fff",
            textShadow: `0 0 10px #${color.toString(16).padStart(6, "0")}`,
            fontFamily: "var(--font-display)",
          }}
        >
          {label}
        </motion.div>
      </Html>
      
      {/* Glow ring */}
      <mesh
        position={[position.x, position.y, position.z]}
        scale={isHovered ? 1.5 : 1.2}
      >
        <ringGeometry args={[1.5, 2, 32]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={isHovered ? 0.3 : 0.1}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

// Central scheme card that highlights when particles arrive
function CentralSchemeCard() {
  const meshRef = useRef<THREE.Mesh>(null);
  const [activeScheme, setActiveScheme] = useState<string>("PM-KISAN");
  
  const schemes = [
    "PM-KISAN", "Ayushman Bharat", "PM Awas Yojana",
    "Jal Jeevan Mission", "Digital India", "Skill India"
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveScheme(schemes[Math.floor(Math.random() * schemes.length)]);
    }, 3000);
    return () => clearInterval(interval);
  }, [schemes]);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.2;
    }
  });

  return (
    <group position={[0, 2.5, 0]}>
      <RoundedBox
        ref={meshRef}
        args={[3, 1.5, 0.3, 0.15]}
        color={0x1a1a24}
      >
        <meshStandardMaterial
          metalness={0.1}
          roughness={0.8}
          transparent
          opacity={0.9}
        />
      </RoundedBox>
      
      <Html
        transform
        position={[0, 2.5, 0.35]}
        style={{
          pointerEvents: "none",
          textAlign: "center",
        }}
      >
        <motion.div
          key={activeScheme}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
          style={{
            padding: "0.75rem 1.5rem",
            borderRadius: "1rem",
            background: "rgba(26, 26, 36, 0.95)",
            border: "1px solid rgba(255, 159, 28, 0.3)",
            backdropFilter: "blur(20px)",
            fontFamily: "var(--font-display)",
            fontSize: "1.1rem",
            fontWeight: 700,
            color: "#ff9f1c",
            whiteSpace: "nowrap",
          }}
        >
          {activeScheme}
        </motion.div>
      </Html>
    </group>
  );
}

// Main Data Flow Visualization Component
export function DataFlowVisualization() {
  return (
    <div style={{ width: "100%", height: "100%", minHeight: "600px" }}>
      <Canvas
        camera={{ position: [0, 5, 15], fov: 45 }}
        gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
        onCreated={({ gl }) => {
          gl.setClearColor(0x0a0a0f, 1);
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.2;
        }}
      >
        <color attach="background" args={[0x0a0a0f]} />
        <fog attach="fog" args={[0x0a0a0f, 5, 35]} />
        
        {/* Lighting */}
        <ambientLight intensity={0.4} color={0xffffff} />
        <directionalLight position={[5, 10, 5]} intensity={1.5} color={0xffffff} />
        <pointLight position={[-8, 3, 0]} color={0x6366f1} intensity={2} distance={15} decay={2} />
        <pointLight position={[8, 3, 0]} color={0xf97316} intensity={2} distance={15} decay={2} />
        <pointLight position={[0, 5, 0]} color={0x14b8a6} intensity={1.5} distance={20} decay={2} />
        
        {/* Stars background */}
        <Stars radius={50} depth={100} count={3000} factor={4} saturation={0} fade />
        
        {/* Orbit controls */}
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          minDistance={8}
          maxDistance={30}
          maxPolarAngle={Math.PI / 2 - 0.1}
        />
        
        {/* Connection lines */}
        <ConnectionLines />
        
        {/* Particle system */}
        <ParticleSystem />
        
        {/* Stage nodes */}
        {STAGE_POSITIONS.map((_, i) => (
          <StageNode key={i} index={i} />
        ))}
        
        {/* Central scheme card */}
        <CentralSchemeCard />
      </Canvas>
    </div>
  );
}