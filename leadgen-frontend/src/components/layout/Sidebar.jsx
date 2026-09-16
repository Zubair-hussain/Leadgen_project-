'use client';

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Database,
  ShieldCheck,
  LogOut,
  Menu,
  X,
  Moon,
  Sun,
  Sparkles,
  ChevronRight
} from "lucide-react";

const Sidebar = ({ tab, setTab, mobileOpen, setMobileOpen, darkMode, setDarkMode, handleLogout }) => {
  const menuItems = [
    {
      id: "generator",
      label: "Lead Generator",
      icon: Zap,
      description: "AI-powered discovery",
      color: "from-primary-500 to-primary-600"
    },
    {
      id: "leads",
      label: "Data Warehouse",
      icon: Database,
      description: "Verified contacts",
      color: "from-success-500 to-success-600"
    },
    {
      id: "verifier",
      label: "Bulk Verifier",
      icon: ShieldCheck,
      description: "Email validation",
      color: "from-warning-500 to-warning-600"
    },
  ];

  const sidebarVariants = {
    closed: {
      x: "-100%",
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 40
      }
    },
    open: {
      x: 0,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 40
      }
    }
  };

  const itemVariants = {
    closed: { x: -20, opacity: 0 },
    open: { x: 0, opacity: 1 }
  };

  return (
    <>
      {/* Mobile Header */}
      <motion.div
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="fixed top-0 left-0 right-0 h-16 bg-surface/80 backdrop-blur-xl border-b border-border flex items-center justify-between px-4 z-50 lg:hidden"
      >
        <div className="flex items-center gap-3">
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25"
          >
            <Zap className="w-4 h-4 text-white" fill="currentColor" />
          </motion.div>
          <div>
            <h1 className="text-lg font-bold text-foreground">LeadGen AI</h1>
            <p className="text-xs text-muted-foreground">Enterprise Suite</p>
          </div>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-lg bg-surface-hover hover:bg-border transition-colors"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </motion.button>
      </motion.div>

      {/* Sidebar */}
      <AnimatePresence>
        {(mobileOpen || window.innerWidth >= 1024) && (
          <motion.aside
            initial="closed"
            animate="open"
            exit="closed"
            variants={sidebarVariants}
            className="fixed top-0 left-0 h-full w-80 bg-surface/95 backdrop-blur-xl border-r border-border flex flex-col z-40 shadow-2xl"
          >
            {/* Logo Section with Close Button */}
            <motion.div
              variants={itemVariants}
              className="p-6 border-b border-border flex items-center justify-between"
            >
              <div className="flex items-center gap-4">
                <motion.div
                  whileHover={{ scale: 1.05, rotate: 5 }}
                  className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl flex items-center justify-center shadow-xl shadow-primary-500/25"
                >
                  <Zap className="w-6 h-6 text-white" fill="currentColor" />
                </motion.div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">LeadGen AI</h1>
                  <p className="text-sm text-muted-foreground flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    Enterprise Suite
                  </p>
                </div>
              </div>
              {/* Close button on mobile */}
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setMobileOpen(false)}
                className="lg:hidden p-2 rounded-lg bg-surface-hover hover:bg-border transition-colors text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </motion.button>
            </motion.div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
              {menuItems.map((item, index) => {
                const isActive = tab === item.id;
                return (
                  <motion.button
                    key={item.id}
                    variants={itemVariants}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => {
                      setTab(item.id);
                      if (window.innerWidth < 1024) {
                        setMobileOpen(false);
                      }
                    }}
                    className={`w-full p-4 rounded-2xl transition-all duration-200 group relative overflow-hidden ${
                      isActive
                        ? 'bg-gradient-to-r from-primary-500/10 to-primary-600/10 border border-primary-500/20'
                        : 'hover:bg-surface-hover border border-transparent'
                    }`}
                  >
                    {/* Background gradient for active state */}
                    {isActive && (
                      <motion.div
                        layoutId="activeBackground"
                        className="absolute inset-0 bg-gradient-to-r from-primary-500/5 to-primary-600/5 rounded-2xl"
                        initial={false}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      />
                    )}

                    <div className="relative flex items-center gap-4">
                      <motion.div
                        className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-200 ${
                          isActive
                            ? `bg-gradient-to-br ${item.color} shadow-lg shadow-primary-500/25`
                            : 'bg-surface-hover group-hover:bg-surface'
                        }`}
                      >
                        <item.icon
                          className={`w-5 h-5 transition-colors ${
                            isActive ? 'text-white' : 'text-muted-foreground group-hover:text-foreground'
                          }`}
                        />
                      </motion.div>

                      <div className="flex-1 text-left min-w-0">
                        <h3 className={`font-semibold transition-colors truncate ${
                          isActive ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground'
                        }`}>
                          {item.label}
                        </h3>
                        <p className={`text-sm transition-colors truncate ${
                          isActive ? 'text-primary-600' : 'text-muted-foreground/70 group-hover:text-muted-foreground'
                        }`}>
                          {item.description}
                        </p>
                      </div>

                      {isActive ? (
                        <motion.div
                          layoutId="activeIndicator"
                          className="w-2 h-8 bg-gradient-to-b from-primary-500 to-primary-600 rounded-full flex-shrink-0"
                          initial={false}
                          transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors flex-shrink-0" />
                      )}
                    </div>
                  </motion.button>
                );
              })}
            </nav>

            {/* Footer Actions */}
            <motion.div
              variants={itemVariants}
              className="p-4 border-t border-border space-y-3 flex-shrink-0"
            >
              {/* Theme Toggle */}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setDarkMode(!darkMode)}
                className="w-full p-3 rounded-xl bg-surface-hover hover:bg-surface border border-border transition-all duration-200 flex items-center gap-3"
              >
                <div className="w-8 h-8 rounded-lg bg-surface flex items-center justify-center flex-shrink-0">
                  {darkMode ? (
                    <Sun className="w-4 h-4 text-warning-500" />
                  ) : (
                    <Moon className="w-4 h-4 text-secondary-500" />
                  )}
                </div>
                <span className="font-medium text-sm truncate">
                  {darkMode ? 'Light Mode' : 'Dark Mode'}
                </span>
              </motion.button>

              {/* Sign Out */}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleLogout}
                className="w-full p-3 rounded-xl bg-accent-50 hover:bg-accent-100 border border-accent-200 text-accent-700 transition-all duration-200 flex items-center gap-3 dark:bg-accent-950 dark:hover:bg-accent-900 dark:border-accent-800 dark:text-accent-300"
              >
                <div className="w-8 h-8 rounded-lg bg-accent-100 dark:bg-accent-900 flex items-center justify-center flex-shrink-0">
                  <LogOut className="w-4 h-4" />
                </div>
                <span className="font-medium text-sm truncate">Sign Out</span>
              </motion.button>
            </motion.div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Mobile Overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileOpen(false)}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 lg:hidden"
          />
        )}
      </AnimatePresence>
    </>
  );
};

export default Sidebar;