import type { Schema } from "./api";
export function commercialDraft(quote: Schema["QuoteRead"]) {
  return {
    title: quote.title,
    description: quote.description || "",
    notes: quote.notes || "",
    valid_until: quote.valid_until || "",
    markup_percentage: quote.breakdown.markup_percentage,
    final_price: quote.breakdown.final_price,
    manual: quote.final_price_overridden,
    adjustments: quote.breakdown.adjustments.map(
      ({ description, adjustment_type, value_type, value }) => ({
        description,
        adjustment_type,
        value_type,
        value,
      }),
    ),
  };
}
export function quotePatch(
  draft: ReturnType<typeof commercialDraft>,
  original: ReturnType<typeof commercialDraft>,
  pricing: boolean,
): Schema["QuoteUpdate"] {
  const body: Schema["QuoteUpdate"] = {};
  if (draft.title !== original.title) body.title = draft.title;
  for (const field of ["description", "notes", "valid_until"] as const) {
    if (draft[field] !== original[field]) body[field] = draft[field] || null;
  }
  if (pricing) {
    body.markup_percentage = draft.markup_percentage;
    body.final_price = draft.manual ? draft.final_price : null;
    body.adjustments = draft.adjustments;
  }
  return body;
}
