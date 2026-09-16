'use client';

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Download, Trash2, Mail, ExternalLink,
  MapPin, CheckCircle2, AlertCircle, RefreshCw,
  Database, TrendingUp, Users, Filter
} from "lucide-react";

const LeadsTable = ({ leads, handleVerify, handleDelete, verifying, handleExport }) => {
  const linkHost = (link) => {
    try {
      return new URL(link).hostname || 'Link';
    } catch {
      return 'Link';
    }
  };

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

  const verifiedCount = leads.filter(lead => lead.is_verified).length;
  const unverifiedCount = leads.length - verifiedCount;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="mt-8 space-y-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-100 dark:bg-primary-900/30 rounded-full">
            <Database className="w-4 h-4 text-primary-600" />
            <span className="text-sm font-medium text-primary-700 dark:text-primary-300">Lead Warehouse</span>
          </div>
          <h2 className="text-2xl font-bold text-foreground">Your Lead Database</h2>
          <p className="text-muted-foreground">
            {leads.length} contacts discovered • {verifiedCount} verified • {unverifiedCount} pending verification
          </p>
        </div>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleExport}
          className="inline-flex items-center gap-2 px-6 py-3 bg-surface hover:bg-surface-hover border border-border rounded-xl text-foreground font-semibold transition-all duration-200 shadow-sm hover:shadow-md"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </motion.button>
      </motion.div>

      {/* Stats Cards */}
      <motion.div variants={itemVariants} className="grid md:grid-cols-3 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
              <Users className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">{leads.length}</p>
              <p className="text-sm text-muted-foreground">Total Leads</p>
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success-100 dark:bg-success-900/30 rounded-xl flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-success-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">{verifiedCount}</p>
              <p className="text-sm text-muted-foreground">Verified</p>
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-warning-100 dark:bg-warning-900/30 rounded-xl flex items-center justify-center">
              <AlertCircle className="w-5 h-5 text-warning-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">{unverifiedCount}</p>
              <p className="text-sm text-muted-foreground">Pending</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Table */}
      <motion.div variants={itemVariants} className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-max md:min-w-0">
            <thead>
              <tr className="border-b border-border bg-surface-hover">
                <th className="text-left py-4 px-6 font-semibold text-foreground">Contact</th>
                <th className="text-left py-4 px-6 font-semibold text-foreground">Authenticity</th>
                <th className="text-left py-4 px-6 font-semibold text-foreground hidden sm:table-cell">Platform</th>
                <th className="text-left py-4 px-6 font-semibold text-foreground hidden md:table-cell">Location</th>
                <th className="text-left py-4 px-6 font-semibold text-foreground hidden lg:table-cell">Website</th>
                <th className="text-right py-4 px-6 font-semibold text-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence>
                {leads.length === 0 ? (
                  <motion.tr
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <td colSpan="6" className="py-16 text-center">
                      <div className="space-y-4">
                        <div className="w-16 h-16 bg-surface-hover rounded-xl flex items-center justify-center mx-auto">
                          <Database className="w-8 h-8 text-muted-foreground" />
                        </div>
                        <div>
                          <p className="font-semibold text-foreground mb-1">No leads found</p>
                          <p className="text-sm text-muted-foreground">Start an extraction to populate your warehouse</p>
                        </div>
                      </div>
                    </td>
                  </motion.tr>
                ) : (
                  leads.map((lead, index) => (
                    <motion.tr
                      key={lead.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ delay: index * 0.02 }}
                      className="border-b border-border hover:bg-surface-hover transition-colors"
                    >
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25">
                            <Mail className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <p className="font-semibold text-foreground">{lead.email}</p>
                            <p className="text-xs text-muted-foreground">
                              Added {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '—'}
                            </p>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-6">
                        {lead.is_verified ? (
                          <div className="inline-flex items-center gap-2 px-3 py-1 bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 rounded-full text-xs font-semibold">
                            <CheckCircle2 className="w-3 h-3" />
                            Verified
                          </div>
                        ) : (
                          <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => handleVerify(lead.id)}
                            disabled={verifying[lead.id]}
                            className="inline-flex items-center gap-2 px-3 py-1 bg-warning-100 dark:bg-warning-900/30 hover:bg-warning-200 dark:hover:bg-warning-900/50 text-warning-700 dark:text-warning-300 rounded-full text-xs font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {verifying[lead.id] ? (
                              <RefreshCw className="w-3 h-3 animate-spin" />
                            ) : (
                              <AlertCircle className="w-3 h-3" />
                            )}
                            {verifying[lead.id] ? 'Verifying...' : 'Verify'}
                          </motion.button>
                        )}
                      </td>

                      <td className="py-4 px-6 hidden sm:table-cell">
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-secondary-100 dark:bg-secondary-900/30 text-secondary-700 dark:text-secondary-300 rounded-full text-xs font-medium">
                          <div className="w-2 h-2 bg-current rounded-full"></div>
                          {lead.source || 'Unknown'}
                        </div>
                      </td>

                      <td className="py-4 px-6 hidden md:table-cell">
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <MapPin className="w-4 h-4" />
                          {lead.location || 'Remote'}
                        </div>
                      </td>

                      <td className="py-4 px-6 hidden lg:table-cell">
                        {lead.link && lead.link.trim() ? (
                          <motion.a
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            href={lead.link}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-2 px-3 py-1 bg-secondary-100 dark:bg-secondary-900/30 text-secondary-700 dark:text-secondary-300 rounded-full text-xs font-medium hover:bg-secondary-200 dark:hover:bg-secondary-900/50 transition-all duration-200"
                            title={lead.link}
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span className="truncate max-w-xs">{linkHost(lead.link)}</span>
                          </motion.a>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>

                      <td className="py-4 px-6">
                        <div className="flex items-center justify-end gap-2">
                          <motion.a
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            href={lead.link}
                            target="_blank"
                            rel="noreferrer"
                            className="w-8 h-8 bg-surface-hover hover:bg-surface border border-border rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground transition-all duration-200"
                            title="View source"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </motion.a>

                          <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => handleDelete(lead.id)}
                            className="w-8 h-8 bg-danger-100 dark:bg-danger-900/30 hover:bg-danger-200 dark:hover:bg-danger-900/50 border border-danger-200 dark:border-danger-800 rounded-lg flex items-center justify-center text-danger-600 hover:text-danger-700 dark:text-danger-400 dark:hover:text-danger-300 transition-all duration-200"
                            title="Delete lead"
                          >
                            <Trash2 className="w-4 h-4" />
                          </motion.button>
                        </div>
                      </td>
                    </motion.tr>
                  ))
                )}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Footer Stats */}
      {leads.length > 0 && (
        <motion.div variants={itemVariants} className="flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>Showing {leads.length} leads</span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-success-500 rounded-full"></div>
              <span>{verifiedCount} verified</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-warning-500 rounded-full"></div>
              <span>{unverifiedCount} unverified</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span>Updated in real-time</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default LeadsTable;