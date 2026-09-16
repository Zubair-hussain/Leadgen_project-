'use client';

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck, Upload, FileText, Send,
  CheckCircle2, XCircle, RefreshCw, Layers,
  Mail, Database, FileSpreadsheet, Zap,
  AlertTriangle, TrendingUp, Users
} from "lucide-react";

const VerifierTab = ({
  singleEmail, setSingleEmail, handleSingleVerify, singleResult,
  multiEmails, setMultiEmails, handleMultiVerify,
  handleFileVerify, verifierResults, handleBulkVerify, busy
}) => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.6,
        staggerChildren: 0.1
      }
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      {/* Header */}
      <motion.div variants={cardVariants} className="text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-success-100 dark:bg-success-900/30 rounded-full">
          <ShieldCheck className="w-4 h-4 text-success-600" />
          <span className="text-sm font-medium text-success-700 dark:text-success-300">Email Verification Suite</span>
        </div>
        <h2 className="text-3xl font-bold text-foreground">Verify Your Leads</h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Ensure your leads are authentic with our comprehensive verification tools.
          Multiple methods available for different use cases.
        </p>
      </motion.div>

      {/* Verification Methods Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Quick Check */}
        <motion.div variants={cardVariants} className="card p-6 space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
              <Mail className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Quick Identity Check</h3>
              <p className="text-sm text-muted-foreground">Verify a single email address instantly</p>
            </div>
          </div>

          <form onSubmit={handleSingleVerify} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                type="email"
                placeholder="target@example.com"
                value={singleEmail}
                onChange={e => setSingleEmail(e.target.value)}
                className="input pl-12 w-full"
              />
            </div>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={busy}
              className="w-full h-12 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:from-secondary-300 disabled:to-secondary-400 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <AnimatePresence mode="wait">
                {busy ? (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"
                  />
                ) : (
                  <motion.div
                    key="send"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-2"
                  >
                    <Send className="w-5 h-5" />
                    <span>Verify Email</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          </form>

          <AnimatePresence>
            {singleResult && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                className={`p-4 rounded-xl border ${
                  singleResult.is_verified
                    ? 'bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800'
                    : 'bg-danger-50 dark:bg-danger-900/20 border-danger-200 dark:border-danger-800'
                }`}
              >
                <div className="flex items-center gap-3">
                  {singleResult.is_verified ? (
                    <CheckCircle2 className="w-5 h-5 text-success-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-danger-600" />
                  )}
                  <div>
                    <p className={`font-semibold text-sm ${
                      singleResult.is_verified ? 'text-success-700 dark:text-success-300' : 'text-danger-700 dark:text-danger-300'
                    }`}>
                      {singleResult.is_verified ? 'Email Verified' : 'Verification Failed'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">{singleResult.message}</p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Bulk Database Verification */}
        <motion.div variants={cardVariants} className="card p-6 space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/25">
              <Database className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Database Audit</h3>
              <p className="text-sm text-muted-foreground">Comprehensive check on all unverified leads</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="p-4 bg-surface-hover rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-foreground">Unverified Leads</span>
                <span className="text-xs text-muted-foreground">Ready for audit</span>
              </div>
              <div className="w-full bg-secondary-200 dark:bg-secondary-700 rounded-full h-2">
                <div className="bg-purple-500 h-2 rounded-full w-3/4"></div>
              </div>
            </div>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleBulkVerify}
              disabled={busy}
              className="w-full h-12 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 disabled:from-secondary-300 disabled:to-secondary-400 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <AnimatePresence mode="wait">
                {busy ? (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"
                  />
                ) : (
                  <motion.div
                    key="audit"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-2"
                  >
                    <ShieldCheck className="w-5 h-5" />
                    <span>Begin Bulk Audit</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          </div>
        </motion.div>

        {/* Paste & Verify */}
        <motion.div variants={cardVariants} className="card p-6 space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center shadow-lg shadow-green-500/25">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Paste & Verify</h3>
              <p className="text-sm text-muted-foreground">Batch verify multiple emails at once</p>
            </div>
          </div>

          <div className="space-y-4">
            <textarea
              placeholder="Paste emails separated by commas or lines...&#10;&#10;Example:&#10;john@example.com&#10;jane@example.com&#10;bob@example.com"
              value={multiEmails}
              onChange={e => setMultiEmails(e.target.value)}
              className="input w-full h-32 resize-none"
              rows={6}
            />

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleMultiVerify}
              disabled={busy}
              className="w-full h-12 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 disabled:from-secondary-300 disabled:to-secondary-400 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <AnimatePresence mode="wait">
                {busy ? (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"
                  />
                ) : (
                  <motion.div
                    key="verify"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-2"
                  >
                    <Layers className="w-5 h-5" />
                    <span>Verify Batch</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          </div>
        </motion.div>

        {/* Import & Extract */}
        <motion.div variants={cardVariants} className="card p-6 space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center shadow-lg shadow-orange-500/25">
              <FileSpreadsheet className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Document Extraction</h3>
              <p className="text-sm text-muted-foreground">Extract and verify emails from files</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="relative">
              <div className="border-2 border-dashed border-border hover:border-primary-300 rounded-xl p-8 text-center transition-colors cursor-pointer group">
                <div className="space-y-4">
                  <div className="w-16 h-16 bg-surface-hover group-hover:bg-primary-50 dark:group-hover:bg-primary-900/20 rounded-xl flex items-center justify-center mx-auto transition-colors">
                    <Upload className="w-8 h-8 text-muted-foreground group-hover:text-primary-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground mb-1">Click to Upload File</p>
                    <p className="text-sm text-muted-foreground">CSV, TXT files supported</p>
                  </div>
                </div>
                <input
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleFileVerify}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
              </div>
            </div>

            <p className="text-xs text-muted-foreground text-center">
              All emails found in the document will be extracted and verified automatically.
            </p>
          </div>
        </motion.div>
      </div>

      {/* Results Table */}
      <AnimatePresence>
        {verifierResults.length > 0 && (
          <motion.div
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            exit={{ opacity: 0, y: -20 }}
            className="card p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-success-500 to-success-600 rounded-xl flex items-center justify-center shadow-lg shadow-success-500/25">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">Verification Results</h3>
                  <p className="text-sm text-muted-foreground">
                    {verifierResults.filter(r => r.is_verified).length} of {verifierResults.length} emails verified
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-success-600" />
                  <span className="text-success-700 dark:text-success-300 font-medium">
                    {verifierResults.filter(r => r.is_verified).length} Valid
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-danger-600" />
                  <span className="text-danger-700 dark:text-danger-300 font-medium">
                    {verifierResults.filter(r => !r.is_verified).length} Invalid
                  </span>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 font-semibold text-foreground">Email Address</th>
                    <th className="text-left py-3 px-4 font-semibold text-foreground">Status</th>
                    <th className="text-left py-3 px-4 font-semibold text-foreground">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {verifierResults.map((result, index) => (
                    <motion.tr
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="border-b border-border hover:bg-surface-hover transition-colors"
                    >
                      <td className="py-4 px-4 font-medium text-foreground">{result.email}</td>
                      <td className="py-4 px-4">
                        <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${
                          result.is_verified
                            ? 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300'
                            : 'bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-300'
                        }`}>
                          {result.is_verified ? (
                            <CheckCircle2 className="w-3 h-3" />
                          ) : (
                            <XCircle className="w-3 h-3" />
                          )}
                          {result.is_verified ? 'Verified' : 'Failed'}
                        </div>
                      </td>
                      <td className="py-4 px-4 text-sm text-muted-foreground">{result.message}</td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats Cards */}
      <motion.div variants={cardVariants} className="grid md:grid-cols-3 gap-6">
        <div className="card p-6 text-center">
          <div className="w-12 h-12 bg-success-100 dark:bg-success-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-6 h-6 text-success-600" />
          </div>
          <h3 className="font-semibold text-foreground mb-2">Verification Checks</h3>
          <p className="text-sm text-muted-foreground">Syntax and domain validation</p>
        </div>

        <div className="card p-6 text-center">
          <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Zap className="w-6 h-6 text-primary-600" />
          </div>
          <h3 className="font-semibold text-foreground mb-2">Instant Results</h3>
          <p className="text-sm text-muted-foreground">Real-time email validation</p>
        </div>

        <div className="card p-6 text-center">
          <div className="w-12 h-12 bg-warning-100 dark:bg-warning-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Users className="w-6 h-6 text-warning-600" />
          </div>
          <h3 className="font-semibold text-foreground mb-2">Bulk Processing</h3>
          <p className="text-sm text-muted-foreground">Handle thousands at once</p>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default VerifierTab;