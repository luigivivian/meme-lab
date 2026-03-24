import type { Variants, Transition } from "framer-motion";

// ── Page route transitions (used by shell.tsx AnimatePresence) ────────────────

export const pageVariants: Variants = {
  initial: { opacity: 0, y: 8, filter: "blur(4px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -4, filter: "blur(2px)" },
};

export const pageTransition: Transition = {
  duration: 0.35,
  ease: [0.16, 1, 0.3, 1], // expo out
};

// ── Stagger container/item (used by grids and lists) ─────────────────────────

export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
};

export const staggerItem: Variants = {
  initial: { opacity: 0, y: 20, scale: 0.97 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
  },
};

// ── Fast stagger (for small items like status rows) ──────────────────────────

export const fastStaggerContainer: Variants = {
  initial: {},
  animate: {
    transition: { staggerChildren: 0.03 },
  },
};

export const fastStaggerItem: Variants = {
  initial: { opacity: 0, x: -8 },
  animate: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.25, ease: "easeOut" },
  },
};

// ── Fade in (for conditional inline elements) ────────────────────────────────

export const fadeIn: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.3, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

// ── Fade in up (for banners, alerts) ─────────────────────────────────────────

export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.2 } },
};

// ── Scale in (for modals/popovers) ───────────────────────────────────────────

export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.95, filter: "blur(4px)" },
  animate: {
    opacity: 1,
    scale: 1,
    filter: "blur(0px)",
    transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] },
  },
  exit: { opacity: 0, scale: 0.97, filter: "blur(2px)", transition: { duration: 0.15 } },
};

// ── Slide in from left (for sidebar mobile) ──────────────────────────────────

export const slideInLeft: Variants = {
  initial: { x: -280, opacity: 0 },
  animate: { x: 0, opacity: 1 },
  exit: { x: -280, opacity: 0 },
};

// ── Number counter spring ────────────────────────────────────────────────────

export const numberSpring: Transition = {
  type: "spring",
  stiffness: 100,
  damping: 20,
  mass: 0.8,
};

// ── Card hover (for interactive cards) ───────────────────────────────────────

export const cardHover: Variants = {
  rest: { y: 0, scale: 1 },
  hover: {
    y: -2,
    scale: 1.01,
    transition: { duration: 0.2, ease: "easeOut" },
  },
};
