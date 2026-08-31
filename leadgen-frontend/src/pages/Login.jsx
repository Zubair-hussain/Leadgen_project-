import { useState } from "react";
import { signInWithPopup } from "firebase/auth";
import { auth, googleProvider } from "../firebase";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Globe
} from "lucide-react";
import { toast } from "react-toastify";

const Login = () => {
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    setIsLoading(true);
    try {
      await signInWithPopup(auth, googleProvider);
      toast.success("Welcome to LeadGen AI!");
    } catch (error) {
      console.error("Login failed", error);
      toast.error("Login failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const features = [
    {
      icon: Target,
      title: "Precision Targeting",
      description: "AI-powered lead discovery across 50+ platforms"
    },
    {
      icon: ShieldCheck,
      title: "Verified Quality",
      description: "99.8% email verification accuracy"
    },
    {
      icon: TrendingUp,
      title: "Scale Instantly",
      description: "Process thousands of leads in minutes"
    },
    {
      icon: Users,
      title: "B2B Focused",
      description: "Specialized for business-to-business sales"
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50 dark:from-secondary-900 dark:via-secondary-800 dark:to-secondary-900 flex items-center justify-center overflow-hidden relative">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            rotate: [0, 180, 360]
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-gradient-to-r from-primary-200/30 to-primary-300/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            rotate: [360, 180, 0]
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute -bottom-40 -right-40 w-[700px] h-[700px] bg-gradient-to-r from-secondary-200/20 to-primary-200/30 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1, 0.8, 1],
            x: [0, 50, 0]
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute top-1/2 left-1/2 w-[400px] h-[400px] bg-gradient-to-r from-success-200/20 to-primary-200/20 rounded-full blur-2xl"
        />
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            animate={{
              y: [0, -20, 0],
              opacity: [0.3, 0.8, 0.3]
            }}
            transition={{
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              delay: Math.random() * 2
            }}
            className="absolute w-1 h-1 bg-primary-400/40 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`
            }}
          />
        ))}
      </div>

      <div className="relative z-10 w-full max-w-7xl px-6 py-12">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left side - Hero content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            className="space-y-8"
          >
            {/* Logo and badge */}
            <div className="flex items-center gap-4">
              <motion.div
                whileHover={{ scale: 1.05 }}
                className="w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-primary-500/25"
              >
                <Zap className="w-8 h-8 text-white" fill="currentColor" />
              </motion.div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">LeadGen AI</h1>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Sparkles className="w-4 h-4 text-primary-500" />
                  <span>Enterprise Lead Generation</span>
                </div>
              </div>
            </div>

            {/* Main headline */}
            <div className="space-y-4">
              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="text-5xl lg:text-6xl font-black leading-tight"
              >
                Find Your Next
                <span className="block gradient-text">Big Client</span>
              </motion.h2>
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.4 }}
                className="text-xl text-muted-foreground max-w-lg leading-relaxed"
              >
                Transform your sales pipeline with AI-powered lead discovery.
                Find, verify, and connect with high-intent B2B prospects instantly.
              </motion.p>
            </div>

            {/* Feature grid */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
              className="grid grid-cols-2 gap-4"
            >
              {features.map((feature, index) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.8 + index * 0.1 }}
                  className="flex items-start gap-3 p-4 rounded-xl bg-surface/50 backdrop-blur-sm border border-border/50 hover:bg-surface/80 transition-all duration-200"
                >
                  <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900/50 rounded-lg flex items-center justify-center flex-shrink-0">
                    <feature.icon className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm text-foreground">{feature.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1">{feature.description}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 1.2 }}
              className="flex items-center gap-8 pt-4"
            >
              <div className="text-center">
                <div className="text-2xl font-bold text-primary-600">50M+</div>
                <div className="text-sm text-muted-foreground">Leads Generated</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-success-600">99.8%</div>
                <div className="text-sm text-muted-foreground">Verification Rate</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-warning-600">24/7</div>
                <div className="text-sm text-muted-foreground">AI Processing</div>
              </div>
            </motion.div>
          </motion.div>

          {/* Right side - Login card */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="flex justify-center lg:justify-end"
          >
            <div className="w-full max-w-md">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.5 }}
                className="bg-surface border border-border rounded-3xl p-8 shadow-2xl shadow-black/5 backdrop-blur-sm"
              >
                {/* Mobile logo */}
                <div className="lg:hidden flex justify-center mb-8">
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    className="w-14 h-14 bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl flex items-center justify-center shadow-xl shadow-primary-500/25"
                  >
                    <Zap className="w-7 h-7 text-white" fill="currentColor" />
                  </motion.div>
                </div>

                <div className="space-y-6">
                  <div className="text-center space-y-2">
                    <h1 className="text-2xl font-bold text-foreground">Welcome Back</h1>
                    <p className="text-muted-foreground">Sign in to access your premium lead engine</p>
                  </div>

                  {/* Google Sign In Button */}
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleLogin}
                    disabled={isLoading}
                    className="w-full h-14 flex items-center justify-center gap-4 bg-foreground hover:bg-foreground/90 text-background font-semibold rounded-2xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <AnimatePresence mode="wait">
                      {isLoading ? (
                        <motion.div
                          key="loading"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="w-5 h-5 border-2 border-background/30 border-t-background rounded-full animate-spin"
                        />
                      ) : (
                        <motion.img
                          key="google"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
                          alt="Google"
                          className="w-5 h-5"
                        />
                      )}
                    </AnimatePresence>
                    <span>{isLoading ? "Signing in..." : "Continue with Google"}</span>
                    {!isLoading && <ArrowRight className="w-4 h-4" />}
                  </motion.button>

                  {/* Trust indicators */}
                  <div className="flex justify-center items-center gap-6 pt-4 border-t border-border">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <ShieldCheck className="w-4 h-4 text-success-500" />
                      <span>Enterprise Security</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Globe className="w-4 h-4 text-primary-500" />
                      <span>SOC 2 Compliant</span>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Additional info */}
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 1.0 }}
                className="text-center text-sm text-muted-foreground mt-6 max-w-sm mx-auto"
              >
                By signing in, you agree to our Terms of Service and Privacy Policy.
                Your data is encrypted and never shared with third parties.
              </motion.p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Login;