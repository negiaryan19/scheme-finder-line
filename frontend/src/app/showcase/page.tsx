"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ClientOnly } from "@/components/ClientOnly";
import { DataFlowVisualization } from "@/components/three/DataFlowVisualization";
import { SchemeCarousel3D } from "@/components/three/SchemeCarousel3D";
import { AnimatedLogo, NavLogo } from "@/components/ui/AnimatedLogo";
import { Button, ButtonIcons } from "@/components/ui/Button";
import { CursorFollower } from "@/components/ui/CursorFollower";

gsap.registerPlugin(ScrollTrigger);

export default function ShowcasePage() {
  const [showCursor, setShowCursor] = useState(false);
  const [sectionRefs, setSectionRefs] = useState<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    setShowCursor(true);
    
    // Initialize scroll animations
    const ctx = gsap.context(() => {
      // Text reveal animations
      gsap.utils.toArray(".text-reveal").forEach((el: any) => {
        gsap.fromTo(el.querySelectorAll("span"), 
          { y: "100%", opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.8,
            stagger: 0.04,
            ease: "custom",
            scrollTrigger: {
              trigger: el,
              start: "top 80%",
              toggleActions: "play none none reverse",
            },
          }
        );
      });

      // Stagger children
      gsap.utils.toArray(".stagger-children").forEach((el: any) => {
        gsap.fromTo(el.children, 
          { y: 30, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.6,
            stagger: 0.08,
            ease: "custom",
            scrollTrigger: {
              trigger: el,
              start: "top 80%",
              toggleActions: "play none none reverse",
            },
          }
        );
      });

      // Counter animations
      gsap.utils.toArray(".counter").forEach((el: any) => {
        const target = parseInt(el.dataset.target || "0");
        gsap.fromTo({ val: 0 }, { val: target }, {
          duration: 2,
          ease: "power2.out",
          scrollTrigger: {
            trigger: el,
            start: "top 80%",
          },
          onUpdate: function() {
            el.textContent = Math.round(this.targets()[0].val).toLocaleString();
          },
        });
      });
    });

    return () => {
      ctx.revert();
      ScrollTrigger.getAll().forEach(t => t.kill());
    };
  }, []);

  const stats = [
    { label: "Schemes Indexed", value: 180, suffix: "+" },
    { label: "Languages Supported", value: 11 },
    { label: "API Latency (p95)", value: 180, suffix: "ms" },
    { label: "Uptime SLA", value: 99.9, suffix: "%" },
  ];

  const features = [
    {
      icon: "🎤",
      title: "Voice-First Interface",
      description: "Natural conversation in 11 Indian languages + English. No menus, no typing — just speak naturally.",
      color: "brand-indigo",
    },
    {
      icon: "🧠",
      title: "Intelligent Scheme Matching",
      description: "Evon LLM understands context, eligibility, and intent to find the right scheme instantly.",
      color: "brand-saffron",
    },
    {
      icon: "🔊",
      title: "Real-time Voice Response",
      description: "Timbre TTS streams natural-sounding audio back in <200ms with Indian numeral formatting.",
      color: "brand-mint",
    },
    {
      icon: "📞",
      title: "Twilio Media Streams",
      description: "Bidirectional μ-law 8kHz audio streaming for telephony integration with STT/TTS pipeline.",
      color: "brand-indigo",
    },
    {
      icon: "⚡",
      title: "Production-Ready Architecture",
      description: "Exponential backoff, circuit breakers, structured logging, and comprehensive test coverage.",
      color: "brand-saffron",
    },
    {
      icon: "🛡️",
      title: "Privacy & Security",
      description: "No audio storage, encrypted transit, PII masking, and compliant with Indian data regulations.",
      color: "brand-mint",
    },
  ];

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary overflow-x-hidden">
      {/* Cursor Follower */}
      {showCursor && <CursorFollower />}

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass-strong border-b border-border-primary">
        <div className="section-container">
          <div className="flex h-16 items-center justify-between">
            <NavLogo className="cursor-pointer" />
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-text-secondary hover:text-text-primary transition-colors text-sm font-medium">
                Features
              </a>
              <a href="#architecture" className="text-text-secondary hover:text-text-primary transition-colors text-sm font-medium">
                Architecture
              </a>
              <a href="#demo" className="text-text-secondary hover:text-text-primary transition-colors text-sm font-medium">
                Live Demo
              </a>
              <a href="#docs" className="text-text-secondary hover:text-text-primary transition-colors text-sm font-medium">
                Docs
              </a>
            </div>

            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm" className="hidden sm:inline-flex">
                <ButtonIcons.Mic className="w-4 h-4" />
                Voice Demo
              </Button>
              <Button size="sm" className="hidden sm:inline-flex">
                <ButtonIcons.ArrowRight className="w-4 h-4" />
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-16">
        <div className="absolute inset-0 overflow-hidden">
          {/* Background gradient orbs */}
          <div className="absolute -top-1/2 -right-1/4 w-[600px] h-[600px] rounded-full bg-brand-indigo-500/10 blur-3xl animate-float" />
          <div className="absolute -bottom-1/4 -left-1/2 w-[500px] h-[500px] rounded-full bg-brand-saffron-500/10 blur-3xl animate-float" style={{ animationDelay: "-3s" }} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full bg-brand-mint-500/10 blur-3xl animate-float" style={{ animationDelay: "-1.5s" }} />
        </div>

        <div className="section-container relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            {/* Left: Content */}
            <div className="text-center lg:text-left">
              <motion.div
                className="stagger-children"
                initial="hidden"
                animate="visible"
                variants={{
                  hidden: { opacity: 0 },
                  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
                }}
              >
                <motion.span
                  className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-indigo-500/10 border border-brand-indigo-500/20 text-brand-indigo-400 text-sm font-medium"
                  variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                >
                  <span className="w-2 h-2 rounded-full bg-brand-saffron-500 animate-pulse" />
                  Gnani AI Internship Challenge
                </motion.span>

                <motion.h1
                  className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-extrabold leading-[1.1] tracking-tight mt-6"
                  variants={{ hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0 } }}
                >
                  <span className="text-text-primary">Government Scheme</span>
                  <br />
                  <span className="gradient-text">Voice Assistant</span>
                </motion.h1>

                <motion.p
                  className="text-lg sm:text-xl text-text-secondary max-w-xl mt-6 leading-relaxed"
                  variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0, transition: { delay: 0.2 } } }}
                >
                  A production-ready voice-enabled assistant that helps citizens discover and understand
                  government schemes through natural conversation in their preferred language.
                </motion.p>

                <motion.div
                  className="flex flex-col sm:flex-row items-center sm:items-center justify-center lg:justify-start gap-4 mt-10"
                  variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0, transition: { delay: 0.3, staggerChildren: 0.1 } } }}
                >
                  <motion.button
                    className="group btn-primary px-8 py-4 text-lg"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <ButtonIcons.Mic className="w-5 h-5 mr-2" />
                    Try Voice Demo
                    <motion.span
                      className="ml-2 inline-block"
                      animate={{ x: [0, 4, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    >
                      →
                    </motion.span>
                  </motion.button>
                  <motion.button className="btn-secondary px-8 py-4 text-lg" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    View Architecture
                  </motion.button>
                </motion.div>

                {/* Stats bar */}
                <motion.div
                  className="grid grid-cols-2 gap-6 mt-16 pt-8 border-t border-border-primary"
                  variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0, transition: { delay: 0.4, staggerChildren: 0.08 } } }}
                >
                  {stats.map((stat, i) => (
                    <motion.div
                      key={stat.label}
                      className="text-center"
                      variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                    >
                      <div className="font-display text-3xl sm:text-4xl font-extrabold gradient-text counter" data-target={stat.value}>
                        {stat.value}{stat.suffix}
                      </div>
                      <div className="text-sm text-text-muted mt-1">{stat.label}</div>
                    </motion.div>
                  ))}
                </motion.div>
              </motion.div>
            </div>

            {/* Right: 3D Data Flow Visualization */}
            <div className="relative">
              <ClientOnly fallback={<div className="aspect-[4/3] bg-bg-tertiary rounded-2xl flex items-center justify-center"><div className="text-text-muted">Loading 3D visualization...</div></div>}>
                <DataFlowVisualization />
              </ClientOnly>
              
              {/* Tech badges */}
              <motion.div
                className="absolute bottom-4 left-4 right-4 flex flex-wrap justify-center gap-2"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
              >
                {["Prisma STT", "Evon LLM", "Timbre TTS", "Twilio Media Streams", "FastAPI", "React Three Fiber"].map((tech, i) => (
                  <motion.span
                    key={tech}
                    className="px-3 py-1.5 text-xs font-medium rounded-full glass border-border-primary"
                    style={{ animationDelay: `${i * 0.05}s` }}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.6 + i * 0.05 }}
                  >
                    {tech}
                  </motion.span>
                ))}
              </motion.div>
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-text-muted"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 1 }}
        >
          <span className="text-xs uppercase tracking-widest">Scroll to explore</span>
          <motion.div
            className="w-6 h-10 border-2 border-border-primary rounded-full flex justify-center pt-2"
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <motion.div className="w-1.5 h-1.5 rounded-full bg-brand-saffron-500" animate={{ y: [0, 6, 0], opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
          </motion.div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 lg:py-32 relative">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-gradient-to-b from-brand-indigo-500/5 via-transparent to-transparent" />
        </div>

        <div className="section-container relative z-10">
          <motion.div className="text-center max-w-3xl mx-auto mb-16 stagger-children">
            <motion.span className="text-brand-saffron-400 font-medium uppercase tracking-widest text-sm">Core Capabilities</motion.span>
            <motion.h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold mt-4 gradient-text">
              Built for <span className="text-text-primary">Production Scale</span>
            </motion.h2>
            <motion.p className="text-lg text-text-secondary mt-4">
              Every component designed for reliability, observability, and seamless integration
            </motion.p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <motion.article
                key={feature.title}
                className="card-base group p-6 relative overflow-visible"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ delay: i * 0.08 }}
              >
                <div className="absolute -top-3 -right-3 w-16 h-16 rounded-2xl opacity-10 group-hover:opacity-20 transition-opacity" 
                     style={{ background: `var(--color-${feature.color}-500)` }} />
                
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-bold text-text-primary mb-2">{feature.title}</h3>
                <p className="text-text-secondary leading-relaxed">{feature.description}</p>
                
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-brand-saffron-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section id="architecture" className="py-24 lg:py-32 bg-bg-secondary relative">
        <div className="section-container">
          <motion.div className="text-center max-w-3xl mx-auto mb-16 stagger-children">
            <motion.span className="text-brand-mint-400 font-medium uppercase tracking-widest text-sm">System Architecture</motion.span>
            <motion.h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold mt-4 gradient-text">
              End-to-End <span className="text-text-primary">Voice Pipeline</span>
            </motion.h2>
            <motion.p className="text-lg text-text-secondary mt-4">
              From microphone to scheme answer — every hop optimized for latency and reliability
            </motion.p>
          </motion.div>

          <div className="relative">
            <ClientOnly fallback={<div className="aspect-[16/9] bg-bg-tertiary rounded-2xl flex items-center justify-center"><div className="text-text-muted">Loading architecture diagram...</div></div>}>
              <DataFlowVisualization />
            </ClientOnly>
            
            {/* Architecture explanation */}
            <motion.div className="mt-12 grid md:grid-cols-5 gap-4 stagger-children">
              {[
                { stage: "1", label: "Voice Input", tech: "Twilio Media Streams", detail: "μ-law 8kHz WebSocket" },
                { stage: "2", label: "Speech-to-Text", tech: "Gnani Prisma STT", detail: "prisma-v3.0, 11 languages" },
                { stage: "3", label: "Scheme Matching", tech: "Gnani Evon LLM", detail: "RAG + vector search" },
                { stage: "4", label: "Text-to-Speech", tech: "Gnani Timbre TTS", detail: "timbre-v3.0, 42 voices" },
                { stage: "5", label: "Audio Output", tech: "Twilio → Phone", detail: "μ-law 8kHz streaming" },
              ].map((item, i) => (
                <motion.div
                  key={item.stage}
                  className="card-base p-5 text-center relative overflow-hidden"
                  variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                >
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3 font-bold text-text-inverse"
                       style={{ background: `linear-gradient(135deg, var(--color-brand-indigo-500), var(--color-brand-saffron-500))` }}>
                    {item.stage}
                  </div>
                  <h4 className="font-semibold text-text-primary mb-1">{item.label}</h4>
                  <p className="text-sm font-medium text-brand-saffron-400 mb-1">{item.tech}</p>
                  <p className="text-xs text-text-muted">{item.detail}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* 3D Scheme Carousel Section */}
      <section id="demo" className="py-24 lg:py-32 relative">
        <div className="section-container">
          <motion.div className="text-center max-w-3xl mx-auto mb-12 stagger-children">
            <motion.span className="text-brand-saffron-400 font-medium uppercase tracking-widest text-sm">Interactive Demo</motion.span>
            <motion.h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold mt-4 gradient-text">
              Explore <span className="text-text-primary">Government Schemes</span> in 3D
            </motion.h2>
            <motion.p className="text-lg text-text-secondary mt-4">
              Navigate the carousel with arrow keys or click — each card represents a real scheme
            </motion.p>
          </motion.div>

          <div className="relative">
            <ClientOnly fallback={<div className="aspect-[16/9] bg-bg-tertiary rounded-2xl flex items-center justify-center"><div className="text-text-muted">Loading scheme carousel...</div></div>}>
              <SchemeCarousel3D />
            </ClientOnly>
          </div>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section id="docs" className="py-24 lg:py-32 bg-bg-secondary">
        <div className="section-container">
          <motion.div className="text-center max-w-3xl mx-auto mb-16 stagger-children">
            <motion.span className="text-brand-mint-400 font-medium uppercase tracking-widest text-sm">Technology Stack</motion.span>
            <motion.h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold mt-4 gradient-text">
              Modern, <span className="text-text-primary">Type-Safe</span> Engineering
            </motion.h2>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { category: "Backend", items: ["FastAPI 0.115", "Python 3.11+", "Pydantic v2", "httpx + WebSockets", "structlog", "pytest-asyncio"] },
              { category: "AI/ML APIs", items: ["Gnani Prisma STT", "Gnani Evon LLM", "Gnani Timbre TTS", "11 Indian languages", "μ-law 8kHz audio"] },
              { category: "Telephony", items: ["Twilio Media Streams", "WebSocket streaming", "Real-time μ-law ↔ PCM", "DTMF & mark events", "TwiML generation"] },
              { category: "Frontend", items: ["Next.js 16 (App Router)", "React 19", "Three.js / R3F", "Framer Motion", "GSAP", "Tailwind CSS v4"] },
            ].map((cat, i) => (
              <motion.article
                key={cat.category}
                className="card-base p-6 stagger-children"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ delay: i * 0.1 }}
              >
                <h3 className="font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <span className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-text-inverse"
                        style={{ background: `linear-gradient(135deg, var(--color-brand-indigo-500), var(--color-brand-saffron-500))` }}>
                    {i + 1}
                  </span>
                  {cat.category}
                </h3>
                <ul className="space-y-2">
                  {cat.items.map((item, j) => (
                    <motion.li
                      key={item}
                      className="text-sm text-text-secondary flex items-center gap-2"
                      variants={{ hidden: { opacity: 0, x: -10 }, visible: { opacity: 1, x: 0 } }}
                    >
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: `var(--color-brand-${["indigo","saffron","mint","indigo"][i]}-500)` }} />
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 lg:py-32 relative overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-br from-brand-indigo-500/10 via-transparent to-brand-saffron-500/10" />
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-brand-indigo-500/5 blur-3xl" />
        </div>

        <div className="section-container relative z-10 text-center">
          <motion.div className="max-w-3xl mx-auto stagger-children">
            <motion.h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold gradient-text">
              Ready to <span className="text-text-primary">Build Voice Apps</span>?
            </motion.h2>
            <motion.p className="text-lg text-text-secondary mt-4 mb-10">
              Clone the repo, add your Gnani API keys, and deploy. Production-ready in minutes.
            </motion.p>
            
            <motion.div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <motion.a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary px-8 py-4 text-lg group"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
                View on GitHub
              </motion.a>
              <motion.a
                href="#"
                className="btn-secondary px-8 py-4 text-lg"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Read Documentation
              </motion.a>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border-primary bg-bg-secondary">
        <div className="section-container">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <NavLogo />
            <p className="text-sm text-text-muted">
              Built for Gnani AI Internship Challenge • Government Scheme Finder Line
            </p>
            <div className="flex items-center gap-6">
              <a href="#" className="text-text-muted hover:text-text-primary transition-colors text-sm">Privacy</a>
              <a href="#" className="text-text-muted hover:text-text-primary transition-colors text-sm">Terms</a>
              <a href="#" className="text-text-muted hover:text-text-primary transition-colors text-sm">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}