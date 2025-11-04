"use client";

import { FinalReport } from "@/types";
import { useState } from "react";
import { ChevronLeft, ChevronRight, MapPin, Home, Bed, Bath, Ruler } from "lucide-react";

interface PropertyCardProps {
  report: FinalReport;
}

export function PropertyCard({ report }: PropertyCardProps) {
  const { listing, evaluation, final_score, recommendation, executive_summary } = report;
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  const nextImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev + 1) % listing.images.length);
  };

  const prevImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev - 1 + listing.images.length) % listing.images.length);
  };

  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case "Strong Buy":
        return "bg-green-500/20 text-green-400 border-green-500/30";
      case "Consider":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
      case "Pass":
        return "bg-red-500/20 text-red-400 border-red-500/30";
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/30";
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 8) return "text-green-400";
    if (score >= 6) return "text-yellow-400";
    return "text-red-400";
  };

  return (
    <div className="w-full max-w-md h-[600px] bg-zinc-900 rounded-2xl overflow-hidden shadow-2xl border border-zinc-800">
      {/* Image Carousel */}
      <div className="relative h-64 bg-zinc-800">
        {listing.images.length > 0 ? (
          <>
            <img
              src={listing.images[currentImageIndex]}
              alt={listing.address}
              className="w-full h-full object-cover"
            />
            {listing.images.length > 1 && (
              <>
                <button
                  onClick={prevImage}
                  className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 rounded-full p-2 transition-all"
                >
                  <ChevronLeft className="w-5 h-5 text-white" />
                </button>
                <button
                  onClick={nextImage}
                  className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 rounded-full p-2 transition-all"
                >
                  <ChevronRight className="w-5 h-5 text-white" />
                </button>
                <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
                  {listing.images.map((_, index) => (
                    <div
                      key={index}
                      className={`h-1.5 rounded-full transition-all ${
                        index === currentImageIndex
                          ? "w-6 bg-white"
                          : "w-1.5 bg-white/50"
                      }`}
                    />
                  ))}
                </div>
              </>
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Home className="w-16 h-16 text-zinc-600" />
          </div>
        )}

        {/* Score Badge */}
        <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-sm rounded-full px-4 py-2">
          <span className={`text-2xl font-bold ${getScoreColor(final_score)}`}>
            {final_score.toFixed(1)}
          </span>
          <span className="text-zinc-400 text-sm">/10</span>
        </div>

        {/* Recommendation Badge */}
        <div className={`absolute top-3 left-3 ${getRecommendationColor(recommendation)} backdrop-blur-sm rounded-full px-3 py-1 border text-xs font-semibold`}>
          {recommendation}
        </div>
      </div>

      {/* Content */}
      <div className="p-5 space-y-4 overflow-y-auto h-[336px]">
        {/* Price and Address */}
        <div>
          <h2 className="text-3xl font-bold text-white">
            ${listing.price.toLocaleString()}
          </h2>
          <div className="flex items-start gap-1 mt-1 text-zinc-400">
            <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <p className="text-sm">
              {listing.address}, {listing.city}, {listing.state} {listing.zip_code}
            </p>
          </div>
        </div>

        {/* Property Details */}
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <Bed className="w-4 h-4 text-zinc-400" />
            <span className="text-white font-medium">{listing.bedrooms}</span>
            <span className="text-zinc-400">beds</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Bath className="w-4 h-4 text-zinc-400" />
            <span className="text-white font-medium">{listing.bathrooms}</span>
            <span className="text-zinc-400">baths</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Ruler className="w-4 h-4 text-zinc-400" />
            <span className="text-white font-medium">{listing.sqft.toLocaleString()}</span>
            <span className="text-zinc-400">sqft</span>
          </div>
        </div>

        {/* Executive Summary */}
        <div>
          <h3 className="text-sm font-semibold text-zinc-300 mb-1">Summary</h3>
          <p className="text-sm text-zinc-400 leading-relaxed">{executive_summary}</p>
        </div>

        {/* Scores Grid */}
        <div className="grid grid-cols-2 gap-2">
          {evaluation.preference_match_score !== undefined && (
            <div className="bg-zinc-800/50 rounded-lg p-2">
              <p className="text-xs text-zinc-500">Match</p>
              <p className="text-lg font-bold text-white">{(evaluation.preference_match_score * 100).toFixed(0)}%</p>
            </div>
          )}
          {evaluation.walkability_score !== undefined && (
            <div className="bg-zinc-800/50 rounded-lg p-2">
              <p className="text-xs text-zinc-500">Walkability</p>
              <p className="text-lg font-bold text-white">{evaluation.walkability_score}/100</p>
            </div>
          )}
          {evaluation.school_score !== undefined && (
            <div className="bg-zinc-800/50 rounded-lg p-2">
              <p className="text-xs text-zinc-500">Schools</p>
              <p className="text-lg font-bold text-white">{evaluation.school_score}/10</p>
            </div>
          )}
          {evaluation.crime_score !== undefined && (
            <div className="bg-zinc-800/50 rounded-lg p-2">
              <p className="text-xs text-zinc-500">Safety</p>
              <p className="text-lg font-bold text-white">{evaluation.crime_score}/10</p>
            </div>
          )}
        </div>

        {/* Property Type and Days on Market */}
        <div className="flex gap-2 text-xs">
          <span className="bg-zinc-800 rounded-full px-3 py-1 text-zinc-300">
            {listing.property_type}
          </span>
          {listing.days_on_market !== undefined && (
            <span className="bg-zinc-800 rounded-full px-3 py-1 text-zinc-300">
              {listing.days_on_market} days on market
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
