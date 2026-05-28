import { readJson } from "./lib.js";

export const acceptanceCatalogPath = "docs/acceptance/source/acceptance_catalog.json";
export const acceptanceCatalog = readJson(acceptanceCatalogPath);
export const acceptanceItems = acceptanceCatalog.acceptance_items;
export const acceptanceIds = acceptanceItems.map((item) => item.id);
export const priorityByAcceptanceId = Object.fromEntries(acceptanceItems.map((item) => [item.id, item.priority]));
export const acceptanceItemById = Object.fromEntries(acceptanceItems.map((item) => [item.id, item]));

export const allowedTraceStates = [
  "local_verified",
  "implemented_unverified",
  "scaffolded",
  "requires_aws",
  "not_started"
];
