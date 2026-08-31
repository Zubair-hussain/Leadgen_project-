import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Globe,
  Mail,
  MapPin,
  Rocket,
  Zap,
  Sparkles,
  Target,
  CheckCircle2,
  X
} from "lucide-react";

const GeneratorForm = ({ form, setForm, busy, handleGenerate, togglePlatform }) => {
  const platforms = [
    {
      id: "reddit",
      icon: Globe,
      label: "Reddit",
      color: "from-orange-500 to-red-500",
      description: "Community discussions"
    },
    {
      id: "x",
      icon: () => <span className="font-bold text-lg">𝕏</span>,
      label: "X (Twitter)",
      color: "from-gray-900 to-black",
      description: "Real-time conversations"
    },
    {
      id: "google-maps",
      icon: MapPin,
      label: "Google Maps",
      color: "from-blue-500 to-blue-600",
      description: "Local business data"
    },
    {
      id: "apify",
      icon: Sparkles,
      label: "Professional",
      color: "from-purple-500 to-purple-600",
      description: "Enterprise sources"
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="max-w-4xl mx-auto space-y-8"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-100 dark:bg-primary-900/30 rounded-full">
          <Target className="w-4 h-4 text-primary-600" />
          <span className="text-sm font-medium text-primary-700 dark:text-primary-300">AI-Powered Discovery</span>
        </div>
        <h2 className="text-3xl font-bold text-foreground">Find Your Perfect Leads</h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Configure your search parameters and let our AI discover high-intent prospects
          across multiple platforms simultaneously.
        </p>
      </motion.div>

      {/* Main Form Card */}
      <motion.div
        variants={itemVariants}
        className="card p-8 space-y-8"
      >
        <form onSubmit={handleGenerate} className="space-y-8">
          {/* Search Parameters */}
          <div className="grid md:grid-cols-2 gap-6">
            <motion.div variants={itemVariants} className="space-y-3">
              <label className="label">Target Niche</label>
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="text"
                  value={form.niche}
                  onChange={e => setForm({ ...form, niche: e.target.value })}
                  placeholder="e.g. Real Estate Agents, Dentists, SaaS Companies"
                  className="input pl-12 w-full"
                />
              </div>
              <p className="text-xs text-muted-foreground">Be specific for better results</p>
            </motion.div>

            <motion.div variants={itemVariants} className="space-y-3">
              <label className="label">Target Location</label>
              <div className="relative">
                <MapPin className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="text"
                  value={form.country}
                  onChange={e => setForm({ ...form, country: e.target.value })}
                  placeholder="e.g. New York, London, San Francisco"
                  className="input pl-12 w-full"
                />
              </div>
              <p className="text-xs text-muted-foreground">City, state, or country</p>
            </motion.div>
          </div>

          {/* Platform Selection */}
          <motion.div variants={itemVariants} className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="label">Search Platforms</label>
              <span className="text-xs text-muted-foreground">
                {form.platforms.length} selected
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {platforms.map((platform, index) => {
                const isSelected = form.platforms.includes(platform.id);
                return (
                  <motion.button
                    key={platform.id}
                    variants={itemVariants}
                    transition={{ delay: index * 0.05 }}
                    type="button"
                    onClick={() => togglePlatform(platform.id)}
                    className={`relative p-4 rounded-2xl border-2 transition-all duration-200 group ${
                      isSelected
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 shadow-lg shadow-primary-500/25'
                        : 'border-border hover:border-primary-300 bg-surface hover:bg-surface-hover'
                    }`}
                  >
                    <div className="flex flex-col items-center gap-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-200 ${
                        isSelected
                          ? `bg-gradient-to-br ${platform.color} shadow-lg`
                          : 'bg-surface-hover group-hover:bg-surface'
                      }`}>
                        <platform.icon className={`w-6 h-6 transition-colors ${
                          isSelected ? 'text-white' : 'text-muted-foreground group-hover:text-foreground'
                        }`} />
                      </div>

                      <div className="text-center">
                        <h3 className={`font-semibold text-sm transition-colors ${
                          isSelected ? 'text-primary-700 dark:text-primary-300' : 'text-foreground'
                        }`}>
                          {platform.label}
                        </h3>
                        <p className={`text-xs transition-colors ${
                          isSelected ? 'text-primary-600 dark:text-primary-400' : 'text-muted-foreground'
                        }`}>
                          {platform.description}
                        </p>
                      </div>
                    </div>

                    <AnimatePresence>
                      {isSelected && (
                        <motion.div
                          initial={{ scale: 0, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0, opacity: 0 }}
                          className="absolute -top-2 -right-2 w-6 h-6 bg-primary-500 rounded-full flex items-center justify-center shadow-lg"
                        >
                          <CheckCircle2 className="w-4 h-4 text-white" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>

          {/* Professional Mode Toggle */}
          <AnimatePresence>
            {form.platforms.includes("google-maps") && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="p-6 rounded-2xl bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 border border-primary-200 dark:border-primary-800"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25">
                      <Rocket className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground">Professional Deep Search</h3>
                      <p className="text-sm text-muted-foreground">Use Apify as an optional deep source; SerpAPI remains active in standard mode</p>
                    </div>
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    type="button"
                    onClick={() => setForm(p => ({ ...p, is_professional: !p.is_professional }))}
                    className={`relative w-14 h-8 rounded-full transition-all duration-300 ${
                      form.is_professional ? 'bg-primary-500' : 'bg-secondary-300 dark:bg-secondary-600'
                    }`}
                  >
                    <motion.div
                      className="w-6 h-6 bg-white rounded-full shadow-md absolute top-1 transition-all duration-300"
                      animate={{ x: form.is_professional ? 22 : 2 }}
                    />
                  </motion.button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit Button */}
          <motion.div variants={itemVariants} className="pt-4">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={busy || !form.niche || !form.country || !form.platforms.length}
              className="w-full h-16 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 disabled:from-secondary-300 disabled:to-secondary-400 text-white font-bold text-lg rounded-2xl transition-all duration-200 shadow-xl hover:shadow-2xl disabled:shadow-none disabled:cursor-not-allowed flex items-center justify-center gap-3"
            >
              <AnimatePresence mode="wait">
                {busy ? (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin"
                  />
                ) : (
                  <motion.div
                    key="zap"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-3"
                  >
                    <Zap className="w-6 h-6" fill="currentColor" />
                    <span>START AI DISCOVERY</span>
                    <Sparkles className="w-5 h-5" />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>

            <p className="text-center text-sm text-muted-foreground mt-4">
              {busy ? "AI is scanning multiple platforms..." : "Results will be added to your data warehouse"}
            </p>
          </motion.div>
        </form>
      </motion.div>

      {/* Info Cards */}
      <motion.div variants={itemVariants} className="grid md:grid-cols-3 gap-6">
        <div className="card p-6 text-center">
          <div className="w-12 h-12 bg-success-100 dark:bg-success-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-6 h-6 text-success-600" />
          </div>
          <h3 className="font-semibold text-foreground mb-2">99.8% Accuracy</h3>
          <p className="text-sm text-muted-foreground">Industry-leading email verification</p>
        </div>

        <div className="card p-6 text-center">
          <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Zap className="w-6 h-6 text-primary-600" />
          </div>
          <h3 className="font-semibold text-foreground mb-2">Lightning Fast</h3>
          <p className="text-sm text-muted-foreground">Process thousands of leads in minutes</p>
        </div>

        <div className="card p-6 text-center">
          <div className="w-12 h-12 bg-warning-100 dark:bg-warning-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Target className="w-6 h-6 text-warning-600" />
          </div>
          <h3 className="font-semibold text-foreground mb-2">AI-Powered</h3>
          <p className="text-sm text-muted-foreground">Smart filtering for high-intent prospects</p>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default GeneratorForm;
