"use client";

import { forwardRef, ButtonHTMLAttributes, ReactNode, useRef, useEffect } from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import { gsap } from "gsap";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "outline" | "magnetic";
  size?: "sm" | "md" | "lg" | "xl";
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
  magnetic?: boolean;
}

// Omit conflicting props from motion
type SafeButtonProps = Omit<HTMLMotionProps<"button">, "onDrag" | "onAnimationStart" | "onAnimationEnd" | "onAnimationIteration">;

const sizeClasses = {
  sm: "px-4 py-2 text-sm gap-1.5",
  md: "px-6 py-3 text-base gap-2",
  lg: "px-8 py-4 text-lg gap-2.5",
  xl: "px-10 py-5 text-xl gap-3",
};

const variantClasses = {
  primary: "bg-gradient-to-r from-brand-indigo-600 to-brand-saffron-500 text-text-inverse shadow-glow hover:shadow-glow-saffron",
  secondary: "bg-bg-tertiary text-text-primary border border-border-primary hover:bg-bg-card-hover hover:border-border-accent",
  ghost: "bg-transparent text-text-secondary hover:text-text-primary hover:bg-bg-tertiary",
  outline: "bg-transparent text-text-primary border border-border-secondary hover:border-brand-saffron-500 hover:bg-brand-saffron-500/10",
  magnetic: "bg-gradient-to-r from-brand-indigo-600 to-brand-saffron-500 text-text-inverse shadow-glow",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = "primary",
      size = "md",
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      magnetic = false,
      className,
      disabled,
      style,
      onDrag,
      onAnimationStart,
      onAnimationEnd,
      onAnimationIteration,
      ...props
    },
    ref
  ) => {
    const buttonRef = useRef<HTMLButtonElement | null>(null);
    const combinedRef = (node: HTMLButtonElement | null) => {
      buttonRef.current = node;
      if (typeof ref === "function") ref(node);
      else if (ref) ref.current = node;
    };

    // Magnetic effect
    useEffect(() => {
      if (!magnetic || !buttonRef.current) return;

      const btn = buttonRef.current;
      const handleMouseMove = (e: MouseEvent) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        gsap.to(btn, {
          x: x * 0.3,
          y: y * 0.3,
          duration: 0.4,
          ease: "power3.out",
        });
      };
      const handleMouseLeave = () => {
        gsap.to(btn, {
          x: 0,
          y: 0,
          scale: 1,
          duration: 0.5,
          ease: "elastic.out(1, 0.5)",
        });
      };
      const handleMouseEnter = () => {
        gsap.to(btn, { scale: 1.05, duration: 0.3, ease: "power2.out" });
      };

      btn.addEventListener("mousemove", handleMouseMove);
      btn.addEventListener("mouseleave", handleMouseLeave);
      btn.addEventListener("mouseenter", handleMouseEnter);

      return () => {
        btn.removeEventListener("mousemove", handleMouseMove);
        btn.removeEventListener("mouseleave", handleMouseLeave);
        btn.removeEventListener("mouseenter", handleMouseEnter);
      };
    }, [magnetic]);

    const motionProps: SafeButtonProps = {
      whileTap: { scale: 0.96 },
      whileHover: variant === "primary" || variant === "magnetic" ? { scale: 1.02 } : undefined,
    };

    return (
      <motion.button
        ref={combinedRef}
        className={cn(
          "btn-base",
          "inline-flex items-center justify-center",
          "font-medium transition-all duration-200",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary",
          "disabled:opacity-50 disabled:pointer-events-none",
          "relative overflow-hidden",
          sizeClasses[size],
          variantClasses[variant],
          fullWidth && "w-full",
          className
        )}
        style={style}
        disabled={disabled || loading}
        {...motionProps}
        {...props}
      >
        {loading ? (
          <>
            <motion.span
              className="w-5 h-5 border-2 border-current border-t-transparent rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
              aria-hidden="true"
            />
            <span className="sr-only">Loading...</span>
          </>
        ) : (
          <>
            {leftIcon && <span className="flex-shrink-0" aria-hidden="true">{leftIcon}</span>}
            <span>{children}</span>
            {rightIcon && <span className="flex-shrink-0" aria-hidden="true">{rightIcon}</span>}
          </>
        )}
        {/* Shimmer effect on hover */}
        {!loading && (
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full"
            initial={{ x: "-100%" }}
            whileHover={{ x: "100%" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            aria-hidden="true"
          />
        )}
      </motion.button>
    );
  }
);

Button.displayName = "Button";

// Icon exports for convenience
import { Mic, Volume2, Send, ArrowRight, Check, Loader2 } from "lucide-react";

export const ButtonIcons = {
  Mic,
  Volume2,
  Send,
  ArrowRight,
  Check,
  Loader2,
};