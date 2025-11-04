"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChatInterface } from "@/components/ChatInterface";
import { UserPreferences } from "@/types";
import { startSearch } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [isStartingSearch, setIsStartingSearch] = useState(false);

  const handlePreferencesComplete = async (sessionId: string, _prefs: UserPreferences) => {
    try {
      setIsStartingSearch(true);

      // Start the search
      const { search_session_id } = await startSearch(sessionId);

      // Navigate to search results page
      router.push(`/search/${search_session_id}`);
    } catch (error) {
      console.error("Failed to start search:", error);
      setIsStartingSearch(false);
      alert("Failed to start search. Please try again.");
    }
  };

  return (
    <div className="h-screen w-full">
      <ChatInterface onPreferencesComplete={handlePreferencesComplete} />
      {isStartingSearch && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg p-6 text-white text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
            <p>Starting your search...</p>
          </div>
        </div>
      )}
    </div>
  );
}
