import { Text, TextInput, View } from "react-native";

export type ProposalDraft = { scope: string; amount: string; days: string };

export const invalidTermsMessage = "Enter a USD cost with at most two decimal places, 0–3650 whole days, and a work scope.";

export function parseProposalTerms(draft: ProposalDraft) {
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(draft.amount.trim());
  const cost = match ? Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0")) : NaN;
  const impact = /^\d+$/.test(draft.days.trim()) ? Number(draft.days) : NaN;
  const scope = draft.scope.trim();
  if (!scope || !Number.isSafeInteger(cost) || cost > 10_000_000_000 || !Number.isInteger(impact) || impact > 3650) return null;
  return { cost, impact, scope };
}

export function ProposalTermsFields({ draft, onChange, editingSuggestion = false, disabled = false }: {
  draft: ProposalDraft;
  onChange: (draft: ProposalDraft) => void;
  editingSuggestion?: boolean;
  disabled?: boolean;
}) {
  const scopeLabel = editingSuggestion ? "Edited work scope" : "Proposed work scope";
  const costLabel = editingSuggestion ? "Edited cost" : "Proposed cost";
  const daysLabel = editingSuggestion ? "Edited additional days" : "Additional days";
  const labelClass = "mb-2 text-[11px] font-semibold text-ink";
  const fieldClass = "mb-4 min-h-[44px] rounded-xl border border-line bg-canvas px-3 text-[13px] text-ink";
  return (
    <View>
      <Text className={labelClass}>{scopeLabel}</Text>
      <TextInput accessibilityLabel={scopeLabel} value={draft.scope} editable={!disabled}
        onChangeText={(scope) => onChange({ ...draft, scope })} multiline maxLength={2000}
        className="mb-4 min-h-[90px] rounded-xl border border-line bg-canvas p-3 text-[13px] text-ink" />
      <Text className={labelClass}>{costLabel} ($)</Text>
      <TextInput accessibilityLabel={costLabel} value={draft.amount} editable={!disabled}
        onChangeText={(amount) => onChange({ ...draft, amount })} keyboardType="decimal-pad" className={fieldClass} />
      <Text className={labelClass}>{daysLabel}</Text>
      <TextInput accessibilityLabel={daysLabel} value={draft.days} editable={!disabled}
        onChangeText={(days) => onChange({ ...draft, days })} keyboardType="number-pad" className={fieldClass} />
    </View>
  );
}
