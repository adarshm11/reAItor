"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatMessage as ChatMessageType, UserPreferences } from "@/types";
import { startChatSession, sendChatMessage } from "@/lib/api";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";

interface ChatInterfaceProps {
  onPreferencesComplete?: (sessionId: string, preferences: UserPreferences) => void;
}

export function ChatInterface({ onPreferencesComplete }: ChatInterfaceProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [preferencesComplete, setPreferencesComplete] = useState(false);
  const [currentPreferences, setCurrentPreferences] = useState<UserPreferences | null>(null);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Initialize chat session on mount
  useEffect(() => {
    const initChat = async () => {
      try {
        setIsLoading(true);
        const { session_id, message } = await startChatSession();
        setSessionId(session_id);

        // Add initial assistant message
        setMessages([
          {
            role: "assistant",
            content: message,
            timestamp: new Date().toISOString(),
          },
        ]);
      } catch (err) {
        console.error("Failed to start chat session:", err);
        setError("Failed to connect to the server. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    initChat();
  }, []);

  const handleSendMessage = async (content: string) => {
    if (!sessionId || isLoading) return;

    // Add user message to UI
    const userMessage: ChatMessageType = {
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      setIsLoading(true);
      setIsTyping(true);
      setError(null);

      // Send message to backend
      const response = await sendChatMessage(sessionId, content);

      // Remove typing indicator and add assistant response
      setIsTyping(false);
      const assistantMessage: ChatMessageType = {
        role: "assistant",
        content: response.response,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Update preferences state
      if (response.preferences_complete) {
        setPreferencesComplete(true);
        if (response.current_preferences) {
          setCurrentPreferences(response.current_preferences);
          onPreferencesComplete?.(sessionId, response.current_preferences);
        }
      } else if (response.current_preferences) {
        setCurrentPreferences(response.current_preferences);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      setIsTyping(false);
      setError("Failed to send message. Please try again.");

      // Add error message
      const errorMessage: ChatMessageType = {
        role: "assistant",
        content: "I'm having trouble responding right now. Please try again.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartSearch = () => {
    if (sessionId && currentPreferences) {
      onPreferencesComplete?.(sessionId, currentPreferences);
    }
  };

  if (!sessionId && isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">
            Connecting to reAItor...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-sm">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            reAItor
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Tell me about your dream home
          </p>
        </div>
      </div>

      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 p-3"
          >
            <div className="max-w-4xl mx-auto flex items-center justify-between">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
              >
                ✕
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-950 p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Preferences Complete Banner */}
      <AnimatePresence>
        {preferencesComplete && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="bg-green-50 dark:bg-green-900/20 border-t border-green-200 dark:border-green-800 p-4"
          >
            <div className="max-w-4xl mx-auto flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-800 dark:text-green-200">
                  ✓ Preferences collected successfully!
                </p>
                <p className="text-xs text-green-600 dark:text-green-300 mt-1">
                  Ready to search for your perfect home
                </p>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleStartSearch}
                className="rounded-full bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
              >
                Start Search
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Input */}
      <ChatInput
        onSend={handleSendMessage}
        disabled={isLoading || preferencesComplete}
        placeholder={
          preferencesComplete
            ? "Click 'Start Search' to find properties"
            : "Type your message..."
        }
      />
    </div>
  );
}
