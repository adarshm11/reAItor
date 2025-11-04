"use client";

import { SearchStatus } from "@/types";
import { motion } from "framer-motion";
import { Search, Home, FileCheck, CheckCircle, AlertCircle } from "lucide-react";

interface SearchProgressProps {
  status: SearchStatus;
}

export function SearchProgress({ status }: SearchProgressProps) {
  const getIcon = () => {
    switch (status.status) {
      case "scraping":
        return <Search className="w-12 h-12 text-blue-400 animate-pulse" />;
      case "evaluating":
        return <FileCheck className="w-12 h-12 text-purple-400 animate-pulse" />;
      case "complete":
        return <CheckCircle className="w-12 h-12 text-green-400" />;
      case "error":
        return <AlertCircle className="w-12 h-12 text-red-400" />;
      default:
        return <Home className="w-12 h-12 text-zinc-400 animate-pulse" />;
    }
  };

  const getStatusText = () => {
    switch (status.status) {
      case "pending":
        return "Preparing search...";
      case "scraping":
        return "Finding properties...";
      case "evaluating":
        return "Analyzing properties...";
      case "complete":
        return "Search complete!";
      case "error":
        return "Search error";
      default:
        return "Processing...";
    }
  };

  const getStatusColor = () => {
    switch (status.status) {
      case "scraping":
        return "text-blue-400";
      case "evaluating":
        return "text-purple-400";
      case "complete":
        return "text-green-400";
      case "error":
        return "text-red-400";
      default:
        return "text-zinc-400";
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="flex flex-col items-center gap-6"
      >
        {/* Icon */}
        <div className="relative">
          {getIcon()}
          {status.status !== "complete" && status.status !== "error" && (
            <motion.div
              className="absolute inset-0 rounded-full border-4 border-transparent border-t-blue-400"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            />
          )}
        </div>

        {/* Status Text */}
        <div className="text-center space-y-2">
          <h2 className={`text-2xl font-bold ${getStatusColor()}`}>
            {getStatusText()}
          </h2>
          <p className="text-zinc-400 text-sm">{status.message}</p>
        </div>

        {/* Progress Bar */}
        {status.status !== "complete" && status.status !== "error" && (
          <div className="w-64 bg-zinc-800 rounded-full h-2 overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
              initial={{ width: 0 }}
              animate={{ width: `${status.progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        )}

        {/* Stats */}
        {status.listings_found > 0 && (
          <div className="bg-zinc-800/50 rounded-lg px-6 py-3 border border-zinc-700">
            <p className="text-zinc-300 text-sm">
              <span className="font-bold text-white">{status.listings_found}</span> properties found
            </p>
          </div>
        )}

        {/* Loading Animation */}
        {status.status !== "complete" && status.status !== "error" && (
          <div className="flex gap-2">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-2 h-2 bg-blue-400 rounded-full"
                animate={{
                  scale: [1, 1.5, 1],
                  opacity: [0.5, 1, 0.5],
                }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  delay: i * 0.2,
                }}
              />
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
