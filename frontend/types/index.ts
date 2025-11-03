/**
 * TypeScript types for reAItor frontend
 */

export interface UserPreferences {
  price_min?: number;
  price_max?: number;
  bedrooms_min?: number;
  bedrooms_max?: number;
  bathrooms_min?: number;
  bathrooms_max?: number;
  sqft_min?: number;
  sqft_max?: number;
  location?: string;
  property_types?: string[];
  must_have_features?: string[];
  deal_breakers?: string[];
  lifestyle_priorities?: string[];
}

export interface Listing {
  id: string;
  source: "zillow" | "redfin" | "realtor";
  url: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  price: number;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  property_type: string;
  description: string;
  images: string[];
  listing_date?: string;
  days_on_market?: number;
}

export interface EvaluationReport {
  listing_id: string;
  preference_match_score: number;
  crime_score?: number;
  school_score?: number;
  walkability_score?: number;
  affordability_score?: number;
  similar_evaluations: string[];
  strengths: string[];
  concerns: string[];
  additional_notes?: string;
}

export interface ArgumentReport {
  listing_id: string;
  pro_arguments: string[];
  con_arguments: string[];
}

export interface FinalReport {
  listing: Listing;
  evaluation: EvaluationReport;
  arguments: ArgumentReport;
  final_score: number;
  executive_summary: string;
  recommendation: "Strong Buy" | "Consider" | "Pass";
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface SearchStatus {
  status: "pending" | "scraping" | "evaluating" | "complete" | "error";
  progress: number;
  message: string;
  listings_found: number;
}
