"use client";

import { motion, useMotionValue, useTransform, PanInfo } from "framer-motion";
import { FinalReport } from "@/types";
import { PropertyCard } from "./PropertyCard";
import { X, Heart } from "lucide-react";

interface SwipeCardProps {
  report: FinalReport;
  onSwipe: (direction: "left" | "right") => void;
  onLike: () => void;
  onDislike: () => void;
}

export function SwipeCard({ report, onSwipe, onLike, onDislike }: SwipeCardProps) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-25, 25]);
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0, 1, 1, 1, 0]);

  const handleDragEnd = (_: any, info: PanInfo) => {
    const swipeThreshold = 100;

    if (info.offset.x > swipeThreshold) {
      // Swipe right - like
      onSwipe("right");
    } else if (info.offset.x < -swipeThreshold) {
      // Swipe left - dislike
      onSwipe("left");
    }
  };

  const handleLikeClick = () => {
    onLike();
  };

  const handleDislikeClick = () => {
    onDislike();
  };

  return (
    <div className="relative">
      <motion.div
        style={{ x, rotate, opacity }}
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        onDragEnd={handleDragEnd}
        className="cursor-grab active:cursor-grabbing"
      >
        <PropertyCard report={report} />

        {/* Swipe Indicators */}
        <motion.div
          className="absolute top-20 right-8 bg-red-500/90 text-white rounded-2xl px-6 py-3 text-2xl font-bold rotate-12 pointer-events-none border-4 border-red-500"
          style={{
            opacity: useTransform(x, [-100, 0], [1, 0]),
          }}
        >
          NOPE
        </motion.div>

        <motion.div
          className="absolute top-20 left-8 bg-green-500/90 text-white rounded-2xl px-6 py-3 text-2xl font-bold -rotate-12 pointer-events-none border-4 border-green-500"
          style={{
            opacity: useTransform(x, [0, 100], [0, 1]),
          }}
        >
          LIKE
        </motion.div>
      </motion.div>

      {/* Action Buttons */}
      <div className="flex justify-center gap-4 mt-6">
        <button
          onClick={handleDislikeClick}
          className="bg-red-500/10 hover:bg-red-500/20 border-2 border-red-500 text-red-500 rounded-full p-4 transition-all hover:scale-110 active:scale-95"
        >
          <X className="w-8 h-8" />
        </button>
        <button
          onClick={handleLikeClick}
          className="bg-green-500/10 hover:bg-green-500/20 border-2 border-green-500 text-green-500 rounded-full p-4 transition-all hover:scale-110 active:scale-95"
        >
          <Heart className="w-8 h-8" />
        </button>
      </div>
    </div>
  );
}
