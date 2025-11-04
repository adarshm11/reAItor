"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { FinalReport, SearchStatus as SearchStatusType } from "@/types";
import { getSearchStatus, getSearchResults, submitFeedback } from "@/lib/api";
import { SwipeCard } from "@/components/SwipeCard";
import { SearchProgress } from "@/components/SearchProgress";
import { EvaluationDisplay } from "@/components/EvaluationDisplay";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Info, Home } from "lucide-react";

export default function SearchResultsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [searchStatus, setSearchStatus] = useState<SearchStatusType | null>(null);
  const [reports, setReports] = useState<FinalReport[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showEvaluation, setShowEvaluation] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [swipeDirection, setSwipeDirection] = useState<"left" | "right" | null>(null);

  // Poll search status
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        const status = await getSearchStatus(sessionId);
        setSearchStatus(status);

        if (status.status === "complete") {
          // Fetch results
          const results = await getSearchResults(sessionId);
          setReports(results);
          setIsLoading(false);
          clearInterval(intervalId);
        } else if (status.status === "error") {
          setIsLoading(false);
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Error polling search status:", error);
        setIsLoading(false);
        clearInterval(intervalId);
      }
    };

    pollStatus();
    intervalId = setInterval(pollStatus, 2000);

    return () => clearInterval(intervalId);
  }, [sessionId]);

  const handleSwipe = async (direction: "left" | "right") => {
    if (currentIndex >= reports.length) return;

    const currentReport = reports[currentIndex];
    const action = direction === "right" ? "like" : "dislike";

    setSwipeDirection(direction);

    try {
      await submitFeedback(currentReport.listing.id, action, sessionId);

      // Wait for animation
      setTimeout(() => {
        setCurrentIndex((prev) => prev + 1);
        setSwipeDirection(null);
      }, 300);
    } catch (error) {
      console.error("Error submitting feedback:", error);
      setSwipeDirection(null);
    }
  };

  const handleLike = () => handleSwipe("right");
  const handleDislike = () => handleSwipe("left");

  const currentReport = reports[currentIndex];
  const hasMoreListings = currentIndex < reports.length;

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back to Chat</span>
          </button>

          {hasMoreListings && (
            <div className="flex items-center gap-4">
              <div className="text-sm text-zinc-400">
                {currentIndex + 1} / {reports.length}
              </div>
              {currentReport && (
                <button
                  onClick={() => setShowEvaluation(true)}
                  className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 px-4 py-2 rounded-lg transition-colors"
                >
                  <Info className="w-4 h-4" />
                  <span className="text-sm">Details</span>
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {isLoading || searchStatus?.status !== "complete" ? (
          // Show progress
          <SearchProgress status={searchStatus || {
            status: "pending",
            progress: 0,
            message: "Initializing search...",
            listings_found: 0,
          }} />
        ) : !hasMoreListings ? (
          // Empty state - no more listings
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center min-h-[500px] text-center"
          >
            <Home className="w-20 h-20 text-zinc-600 mb-6" />
            <h2 className="text-3xl font-bold text-white mb-2">
              You've Seen All Properties!
            </h2>
            <p className="text-zinc-400 mb-8 max-w-md">
              You've reviewed all the listings we found. Based on your feedback, we'll learn your preferences better for next time!
            </p>
            <button
              onClick={() => router.push("/")}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
            >
              Start New Search
            </button>
          </motion.div>
        ) : (
          // Show swipe cards
          <div className="flex justify-center items-start min-h-[600px] pt-8">
            <AnimatePresence mode="wait">
              {currentReport && !swipeDirection && (
                <motion.div
                  key={currentReport.listing.id}
                  initial={{ scale: 0.8, opacity: 0, y: 50 }}
                  animate={{ scale: 1, opacity: 1, y: 0 }}
                  exit={{
                    x: swipeDirection === "right" ? 500 : swipeDirection === "left" ? -500 : 0,
                    opacity: 0,
                    transition: { duration: 0.3 },
                  }}
                >
                  <SwipeCard
                    report={currentReport}
                    onSwipe={handleSwipe}
                    onLike={handleLike}
                    onDislike={handleDislike}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </main>

      {/* Evaluation Modal */}
      {currentReport && (
        <EvaluationDisplay
          report={currentReport}
          isOpen={showEvaluation}
          onClose={() => setShowEvaluation(false)}
        />
      )}
    </div>
  );
}
