import { localCostEstimate } from "../packages/model-catalog/src/cost-estimate.js";
import { assert } from "./lib.js";

const total = localCostEstimate.line_items.reduce((sum, item) => sum + item.monthly_usd, 0);
assert(total === localCostEstimate.monthly_usd, "cost estimate line items must sum to monthly_usd");
assert(localCostEstimate.monthly_usd <= 550, "monthly estimate must be <= 550 USD");
assert(localCostEstimate.assumption.includes("50 DAU"), "cost assumption must mention 50 DAU");
assert(localCostEstimate.assumption.includes("10 questions/user/day"), "cost assumption must mention expected question volume");

console.log("cost estimate check passed");
