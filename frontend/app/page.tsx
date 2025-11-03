"use client";

import { useState } from "react";
import { ChatInterface } from "@/components/ChatInterface";
import { UserPreferences } from "@/types";

export default function Home() {
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [searchStarted, setSearchStarted] = useState(false);

  const handlePreferencesComplete = (sessionId: string, prefs: UserPreferences) => {
    setChatSessionId(sessionId);
    setPreferences(prefs);
    setSearchStarted(true);

    // TODO: Navigate to search results page or show results UI
    console.log("Preferences complete:", { sessionId, prefs });
  };

  return (
    <div className="h-screen w-full">
      <ChatInterface onPreferencesComplete={handlePreferencesComplete} />
    </div>
  );
}
