import { useEffect, useRef, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";

import {
  generateSuggestion, listSuggestions, recordSuggestionResponse, sampleSuggestions,
  type StoredSuggestion, type SuggestionResponse,
} from "@/features/change-orders/suggestions";
import { ApiError } from "@/lib/api";
import type { WorkspaceChange } from "./data";
import { invalidTermsMessage, parseProposalTerms, ProposalTermsFields, type ProposalDraft } from "./proposal-terms";
import { Button, Card } from "./ui";

const responseLabels = { accepted: "Accepted", edited: "Edited", dismissed: "Dismissed" };
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function SuggestionPanel({ change, reviewable, disabled, onApply, onSavingResponse }: {
  change: WorkspaceChange;
  reviewable: boolean;
  disabled: boolean;
  onApply: (draft: ProposalDraft) => void;
  onSavingResponse: (saving: boolean) => void;
}) {
  const [originalScope, setOriginalScope] = useState("");
  const [stored, setStored] = useState<StoredSuggestion | null>(null);
  const [ready, setReady] = useState(sampleSuggestions);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const inFlight = useRef(false);
  const [rating, setRating] = useState<number | null>(null);
  const [edited, setEdited] = useState<ProposalDraft | null>(null);

  useEffect(() => {
    if (sampleSuggestions) return;
    let current = true;
    // A successful list confirms J7 is installed. The older POST route can send photos.
    listSuggestions(change.id).then((items) => {
      if (!current) return;
      setStored(items[0] ?? null);
      setReady(true);
    }).catch((cause: unknown) => {
      if (!current) return;
      setError(cause instanceof ApiError && (cause.status === 404 || cause.status === 405)
        ? "AI suggestions are unavailable on this API. You can still enter proposal terms."
        : message(cause, "Could not load suggestions. You can still enter proposal terms."));
    });
    return () => { current = false; };
  }, [change.id, reload]);

  const suggestion = stored ?? (sampleSuggestions ? null : change.suggestion);
  const canGenerate = change.status === "submitted" || change.status === "in_review";
  const locked = working || disabled;
  const range = stored?.cost_low_cents != null && stored.cost_high_cents != null
    ? `${usd.format(stored.cost_low_cents / 100)} – ${usd.format(stored.cost_high_cents / 100)}`
    : "Range unavailable";
  const suggestedDraft = suggestion ? {
    scope: suggestion.scope,
    amount: stored ? (stored.cost_cents / 100).toFixed(2) : String(suggestion.amount),
    days: String(suggestion.impact_days),
  } : null;

  async function generate() {
    if (!ready || !canGenerate || inFlight.current || disabled) return;
    inFlight.current = true;
    setWorking(true);
    setError("");
    try {
      const result = await generateSuggestion(change.id, originalScope);
      setStored(result);
      setRating(null);
      setEdited(null);
    } catch (cause) {
      setError(message(cause, "Could not generate a suggestion. You can still enter proposal terms."));
    } finally {
      inFlight.current = false;
      setWorking(false);
    }
  }

  async function respond(response: SuggestionResponse) {
    if (!stored || stored.response || !ready || !reviewable || !suggestedDraft || inFlight.current || disabled) return;
    const draft = response === "edited" ? edited : suggestedDraft;
    if (!draft) return;
    if (response === "edited") {
      const terms = parseProposalTerms(draft);
      if (!terms) { setError(invalidTermsMessage); return; }
      if (terms.cost === stored.cost_cents && terms.scope === stored.scope.trim() && terms.impact === stored.impact_days) {
        setError("Change a term before applying an edit, or cancel and accept the suggestion.");
        return;
      }
    }
    inFlight.current = true;
    setWorking(true);
    onSavingResponse(true);
    setError("");
    try {
      const saved = await recordSuggestionResponse(stored, response, rating);
      setStored(saved);
      if (response !== "dismissed") onApply(draft);
      setEdited(null);
    } catch (cause) {
      setError(message(cause, "Could not save your response."));
      if (cause instanceof ApiError && cause.status === 409) {
        setReady(false);
        setRating(null);
        setEdited(null);
        setReload((n) => n + 1);
      }
    } finally {
      inFlight.current = false;
      setWorking(false);
      onSavingResponse(false);
    }
  }

  if (!suggestion && !canGenerate) return null;
  return (
    <Card className="gap-3 p-5">
      <Text accessibilityRole="header" className="text-[15px] font-semibold text-ink">AI scope and cost suggestion</Text>
      {sampleSuggestions && (
        <Text className="rounded-lg bg-sand p-3 text-[12px] text-ochre">
          Sample mode · Invented estimate. Feedback resets on reload.
        </Text>
      )}
      {canGenerate && (!stored || stored.response) && ready && (
        <>
          {!sampleSuggestions && (
            <>
              <Text className="text-[12px] text-muted">Compare the field report with the original proposal scope.</Text>
              <TextInput accessibilityLabel="Original proposal scope" placeholder="Original proposal scope"
                value={originalScope} onChangeText={setOriginalScope} multiline maxLength={10000}
                className="min-h-[80px] rounded-xl border border-line p-3 text-ink" />
            </>
          )}
          <Button variant="secondary" onPress={generate} busy={working}
            disabled={disabled || (!sampleSuggestions && originalScope.trim().length < 10)}>
            {sampleSuggestions ? "Generate sample suggestion" : "Generate suggestion"}
          </Button>
        </>
      )}
      {!ready && !error && <Text className="text-[12px] text-muted">Loading suggestions…</Text>}
      {suggestion && suggestedDraft && (
        <View className="gap-3">
          <View className="gap-2 rounded-xl bg-canvas p-4">
            <Text className="text-[12px] font-semibold text-forest">{suggestion.in_scope ? "Likely in scope" : "Likely extra work"}</Text>
            <Text className="text-[14px] text-ink">{suggestion.scope}</Text>
            <Text className="text-[12px] text-muted">Lump-sum range</Text>
            <Text className="text-[17px] font-semibold text-ink">{range}</Text>
            <Text className="text-[13px] text-ink">Best estimate · {usd.format(Number(suggestedDraft.amount))}</Text>
            <Text className="text-[13px] text-ink">Schedule · {suggestion.impact_days} additional {suggestion.impact_days === 1 ? "day" : "days"}</Text>
            <Text className="text-[12px] text-muted">Reason</Text>
            <Text className="text-[13px] leading-5 text-ink">{suggestion.rationale}</Text>
            <Text className="text-[12px] font-semibold text-ink">Confidence · {stored?.confidence == null ? "Unavailable" : `${Math.round(stored.confidence * 100)}%`}</Text>
          </View>
          {stored?.response && (
            <Text accessibilityLiveRegion="polite" className="text-[13px] font-semibold text-forest">
              {responseLabels[stored.response]} · {stored.rating == null ? "Unrated" : `Rated ${stored.rating}/5`}
            </Text>
          )}
          {reviewable && stored && !stored.response && ready && (
            <>
              <Text className="text-[12px] text-ink">Rate this suggestion (optional)</Text>
              <View className="flex-row flex-wrap gap-1">
                {[1, 2, 3, 4, 5].map((value) => (
                  <Pressable key={value} accessibilityRole="button" accessibilityLabel={`Rate ${value} of 5`}
                    accessibilityState={{ selected: rating === value, disabled: locked }} disabled={locked}
                    onPress={() => setRating(rating === value ? null : value)}
                    className={`min-h-[44px] min-w-[40px] flex-1 items-center justify-center rounded-lg border ${rating === value ? "border-forest bg-forest" : "border-line bg-white"}`}>
                    <Text className={rating === value ? "font-semibold text-white" : "text-ink"}>{value}</Text>
                  </Pressable>
                ))}
              </View>
              {edited ? (
                <>
                  <ProposalTermsFields draft={edited} onChange={setEdited} editingSuggestion disabled={locked} />
                  <Button onPress={() => respond("edited")} disabled={locked}>Apply edited terms to draft</Button>
                  <Button variant="quiet" disabled={locked} onPress={() => { setEdited(null); setError(""); }}>Cancel edit</Button>
                </>
              ) : (
                <>
                  <Button onPress={() => respond("accepted")} disabled={locked}>Accept and apply to draft</Button>
                  <Button variant="secondary" onPress={() => { setEdited(suggestedDraft); setError(""); }} disabled={locked}>Edit suggested terms</Button>
                  <Button variant="quiet" onPress={() => respond("dismissed")} disabled={locked}>Dismiss suggestion</Button>
                </>
              )}
            </>
          )}
          {reviewable && !stored && <Button variant="secondary" disabled={locked} onPress={() => onApply(suggestedDraft)}>Copy previous estimate to draft</Button>}
        </View>
      )}
      {!!error && <Text accessibilityRole="alert" className="text-[12px] leading-5 text-ochre">{error}</Text>}
      {!ready && !!error && <Button variant="quiet" onPress={() => { setError(""); setReload((n) => n + 1); }}>Reload suggestions</Button>}
    </Card>
  );
}

function message(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback;
}
