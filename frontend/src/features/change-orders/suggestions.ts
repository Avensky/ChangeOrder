import { requestJson } from "@/lib/api";
import type { Suggestion } from "./types";

export type SuggestionResponse = "accepted" | "edited" | "dismissed";
export type StoredSuggestion = Suggestion & {
  id: number;
  currency: string;
  cost_cents: number;
  cost_low_cents: number | null;
  cost_high_cents: number | null;
  confidence: number | null;
  response: SuggestionResponse | null;
  rating: number | null;
};

export const sampleSuggestions = process.env.EXPO_PUBLIC_SUGGESTION_PREVIEW === "true";

export function listSuggestions(changeId: string) {
  return requestJson<StoredSuggestion[]>(`/api/v1/changes/${encodeURIComponent(changeId)}/suggestions`);
}

export function generateSuggestion(changeId: string, originalScope: string) {
  if (sampleSuggestions) {
    // Invented fixture for a local demo. No project text or photos leave the screen.
    return Promise.resolve<StoredSuggestion>({
      id: 1, scope: "Install two additional sample shelving brackets.", in_scope: false,
      rationale: "The sample proposal includes shelving but excludes the two additional brackets.",
      currency: "USD", cost_low_cents: 12000, cost_cents: 14550, cost_high_cents: 17500,
      amount: 145.5, impact_days: 1, confidence: 0.75, response: null, rating: null,
    });
  }
  return requestJson<StoredSuggestion>(`/api/v1/changes/${encodeURIComponent(changeId)}/suggestion`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original_scope: originalScope.trim() }),
  }, 60_000);
}

export function recordSuggestionResponse(suggestion: StoredSuggestion, response: SuggestionResponse, rating: number | null) {
  if (sampleSuggestions) return Promise.resolve({ ...suggestion, response, rating });
  return requestJson<StoredSuggestion>(`/api/v1/suggestions/${suggestion.id}/response`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ response, rating }),
  });
}
