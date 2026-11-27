import { expect, test, type Page } from "@playwright/test";
import type { ChangeOrder } from "../../src/features/change-orders/types";
import type { StoredSuggestion, SuggestionResponse } from "../../src/features/change-orders/suggestions";
import { mockAuth, signIn } from "./staff-session";

const change: ChangeOrder = {
  id: "12", code: "TEST-12", project_id: "north-park", title: "Sample shelving",
  description: "Fit two extra shelf brackets.", severity: "normal", status: "submitted",
  submitted_by: "field", author: "Demo field worker", sent_for_approval: false, approved_scope: null,
  amount: 18, impact_days: 0, history: [], photo_keys: [], suggestion: null, created_at: "2026-11-01",
};
const estimate: StoredSuggestion = {
  id: 3, in_scope: false, scope: "Fit the new brackets", rationale: "The original scope covers one shelf.",
  currency: "USD", cost_low_cents: 10100, cost_cents: 13456, cost_high_cents: 16789,
  amount: 134.56, impact_days: 2, confidence: 0.78, response: null, rating: null,
};
const original = "Install one shelf in the sample office.";

async function openReview(page: Page, options: { list404?: boolean; ai503?: boolean; conflict?: boolean; existing?: StoredSuggestion } = {}) {
  await mockAuth(page, "estimator");
  let stored = options.existing;
  const writes: string[] = [];
  await page.route("**/api/v1/changes", route => route.fulfill({ json: [change] }));
  await page.route("**/api/v1/changes/12/suggestions", route => route.fulfill(
    options.list404 ? { status: 404, json: { detail: "Not found" } } : { json: stored ? [stored] : [] },
  ));
  await page.route("**/api/v1/changes/12/suggestion", route => {
    writes.push("generate");
    expect(route.request().postDataJSON()).toEqual({ original_scope: original });
    if (options.ai503) return route.fulfill({ status: 503, json: { detail: "AI suggestions are not available. The office can enter cost and days manually." } });
    stored = { ...estimate };
    return route.fulfill({ json: stored });
  });
  await page.route("**/api/v1/suggestions/3/response", route => {
    const body = route.request().postDataJSON();
    writes.push(body.response);
    expect(body).toEqual({ response: body.response, rating: 4 });
    stored = { ...estimate, response: body.response, rating: body.rating };
    if (options.conflict) {
      stored = { ...estimate, response: "dismissed", rating: 2 };
      return route.fulfill({ status: 409, json: { detail: "Suggestion already answered" } });
    }
    return route.fulfill({ json: stored });
  });
  await page.route("**/api/v1/changes/12/review", route => { writes.push("review"); return route.fulfill({ json: change }); });
  await signIn(page);
  await page.getByRole("button", { name: "Review next request" }).click();
  return writes;
}

for (const response of ["accepted", "edited", "dismissed"] as SuggestionResponse[]) {
  test(`estimator records a rated ${response} response separately from sending terms`, async ({ page }) => {
    const writes = await openReview(page);
    await page.getByLabel("Original proposal scope").fill(original);
    await page.getByRole("button", { name: "Generate suggestion" }).click();
    await expect(page.getByText("$101.00 – $167.89", { exact: true })).toBeVisible();
    await expect(page.getByText("Confidence · 78%")).toBeVisible();
    const proposed = page.getByLabel("Proposed cost", { exact: true });
    await expect(proposed).toHaveValue("18");
    await page.getByRole("button", { name: "Rate 4 of 5" }).click();
    if (response === "edited") {
      await page.getByRole("button", { name: "Edit suggested terms" }).click();
      await page.getByLabel("Edited cost", { exact: true }).fill("200.25");
      await expect(proposed).toHaveValue("18");
      await page.getByRole("button", { name: "Apply edited terms to draft" }).click();
    } else {
      const action = response === "accepted" ? "Accept and apply to draft" : "Dismiss suggestion";
      await page.getByRole("button", { name: action }).click();
    }
    await expect(page.getByText(/Rated 4\/5/).filter({ visible: true })).toBeVisible();
    await expect(proposed).toHaveValue({ accepted: "134.56", edited: "200.25", dismissed: "18" }[response]);
    expect(writes).toEqual(["generate", response]);
    await page.getByRole("button", { name: "Back to requests" }).click();
    await page.getByRole("button", { name: "Open TEST-12: Sample shelving" }).click();
    await expect(page.getByText(/Rated 4\/5/).filter({ visible: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Dismiss suggestion" })).toHaveCount(0);
  });
}

test("an older API never receives an AI request; a manual proposal is still available", async ({ page }) => {
  const writes = await openReview(page, { list404: true });
  await expect(page.getByRole("alert")).toContainText("unavailable on this API");
  await expect(page.getByRole("button", { name: "Generate suggestion" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Send estimate to GC" })).toBeEnabled();
  expect(writes).toEqual([]);
});

test("a model outage leaves manual terms intact", async ({ page }) => {
  const writes = await openReview(page, { ai503: true });
  await page.getByLabel("Original proposal scope").fill(original);
  await page.getByRole("button", { name: "Generate suggestion" }).click();
  await expect(page.getByRole("alert")).toContainText("AI suggestions are not available");
  await expect(page.getByLabel("Proposed cost", { exact: true })).toHaveValue("18");
  await expect(page.getByRole("button", { name: "Send estimate to GC" })).toBeEnabled();
  expect(writes).toEqual(["generate"]);
});

test("conflicting feedback reloads the saved response and preserves the proposal draft", async ({ page }) => {
  await openReview(page, { existing: { ...estimate, confidence: null, cost_low_cents: null, cost_high_cents: null }, conflict: true });
  await expect(page.getByText("Range unavailable")).toBeVisible();
  await expect(page.getByText("Confidence · Unavailable")).toBeVisible();
  await page.getByRole("button", { name: "Rate 4 of 5" }).click();
  await page.getByRole("button", { name: "Accept and apply to draft" }).click();
  await expect(page.getByText("Dismissed · Rated 2/5")).toBeVisible();
  await expect(page.getByLabel("Proposed cost", { exact: true })).toHaveValue("18");
});
