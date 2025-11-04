"use client";

import { FinalReport } from "@/types";
import { ThumbsUp, ThumbsDown, CheckCircle, AlertCircle, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface EvaluationDisplayProps {
  report: FinalReport;
  isOpen: boolean;
  onClose: () => void;
}

export function EvaluationDisplay({ report, isOpen, onClose }: EvaluationDisplayProps) {
  const { evaluation, arguments: args } = report;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-zinc-900 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden border border-zinc-800"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-zinc-800">
              <h2 className="text-2xl font-bold text-white">Detailed Analysis</h2>
              <button
                onClick={onClose}
                className="text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Content */}
            <div className="overflow-y-auto max-h-[calc(80vh-80px)] p-6 space-y-6">
              {/* Strengths */}
              {evaluation.strengths && evaluation.strengths.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    <h3 className="text-lg font-semibold text-white">Strengths</h3>
                  </div>
                  <ul className="space-y-2">
                    {evaluation.strengths.map((strength, index) => (
                      <li
                        key={index}
                        className="text-zinc-300 text-sm flex items-start gap-2"
                      >
                        <span className="text-green-400 mt-1">•</span>
                        <span>{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Concerns */}
              {evaluation.concerns && evaluation.concerns.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <AlertCircle className="w-5 h-5 text-yellow-400" />
                    <h3 className="text-lg font-semibold text-white">Concerns</h3>
                  </div>
                  <ul className="space-y-2">
                    {evaluation.concerns.map((concern, index) => (
                      <li
                        key={index}
                        className="text-zinc-300 text-sm flex items-start gap-2"
                      >
                        <span className="text-yellow-400 mt-1">•</span>
                        <span>{concern}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Pro Arguments */}
              {args.pro_arguments && args.pro_arguments.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <ThumbsUp className="w-5 h-5 text-green-400" />
                    <h3 className="text-lg font-semibold text-white">Why You Should Buy</h3>
                  </div>
                  <div className="space-y-3">
                    {args.pro_arguments.map((arg, index) => (
                      <div
                        key={index}
                        className="bg-green-500/10 border border-green-500/30 rounded-lg p-3"
                      >
                        <p className="text-zinc-200 text-sm leading-relaxed">{arg}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Con Arguments */}
              {args.con_arguments && args.con_arguments.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <ThumbsDown className="w-5 h-5 text-red-400" />
                    <h3 className="text-lg font-semibold text-white">Why You Should Pass</h3>
                  </div>
                  <div className="space-y-3">
                    {args.con_arguments.map((arg, index) => (
                      <div
                        key={index}
                        className="bg-red-500/10 border border-red-500/30 rounded-lg p-3"
                      >
                        <p className="text-zinc-200 text-sm leading-relaxed">{arg}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Additional Notes */}
              {evaluation.additional_notes && (
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">Additional Notes</h3>
                  <p className="text-zinc-300 text-sm leading-relaxed">
                    {evaluation.additional_notes}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
