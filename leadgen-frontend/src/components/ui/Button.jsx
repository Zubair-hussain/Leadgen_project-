'use client';

import { motion } from "framer-motion";

export const Button = ({ children, onClick, variant = "primary", className = "", disabled }) => {
  const baseStyle =
    "px-6 py-3 rounded-xl font-semibold transition-all duration-300 flex items-center justify-center gap-2";

  const variants = {
    primary:
      "bg-premium-text text-white shadow-xl shadow-gray-200 hover:bg-black hover:shadow-2xl",
    secondary:
      "bg-white border border-gray-100 text-premium-text shadow-premium hover:shadow-premium-hover hover:bg-premium-bg",
    accent:
      "bg-premium-accent text-white shadow-lg shadow-indigo-100 hover:bg-indigo-700",
  };

  return (
    <motion.button
      whileHover={!disabled ? { scale: 1.02 } : {}}
      whileTap={!disabled ? { scale: 0.95 } : {}}
      onClick={!disabled ? onClick : undefined}
      disabled={disabled}
      type="button"
      style={{ position: "relative", zIndex: 1, pointerEvents: disabled ? "none" : "auto" }}
      className={`${baseStyle} ${variants[variant]} ${className} ${
        disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
      }`}
    >
      {children}
    </motion.button>
  );
};