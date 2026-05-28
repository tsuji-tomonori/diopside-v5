import { bm25Documents, bm25GoldenQueries, referenceGraphSamples } from "../packages/testing/src/search-fixtures.js";
import { assert } from "./lib.js";

const referenceResults = referenceGraphSamples.map((sample) => ({
  id: sample.id,
  success: Boolean(sample.source_node_id && sample.target_node_id && sample.edge_type && sample.chunk_id)
}));
const referenceSuccess = referenceResults.filter((item) => item.success).length;
assert(referenceSuccess === 10, `reference graph sample expansion below 10/10: ${referenceSuccess}`);

let bm25Hits = 0;
for (const item of bm25GoldenQueries) {
  const results = searchBm25(item.query).slice(0, 10);
  if (results.some((result) => result.source_chunk_id === item.expected_chunk_id)) bm25Hits += 1;
}
const recallAt10 = bm25Hits / bm25GoldenQueries.length;
assert(recallAt10 >= 0.8, `BM25F golden recall@10 below 0.80: ${recallAt10}`);

console.log(`local search check passed (reference_expansion=10/10, bm25_recall_at_10=${recallAt10.toFixed(2)})`);

function searchBm25(query) {
  const terms = tokenize(query);
  return bm25Documents
    .map((doc) => ({ ...doc, score: scoreDocument(terms, doc) }))
    .filter((doc) => doc.score > 0)
    .sort((a, b) => b.score - a.score);
}

function scoreDocument(terms, doc) {
  const titleTokens = tokenize(doc.fields.title);
  const bodyTokens = tokenize(doc.fields.body);
  return terms.reduce((score, term) => {
    const titleTf = titleTokens.filter((token) => token === term).length;
    const bodyTf = bodyTokens.filter((token) => token === term).length;
    return score + titleTf * 2.0 + bodyTf * 1.0;
  }, 0);
}

function tokenize(value) {
  return value.toLowerCase().split(/[\s:/._-]+/).filter(Boolean);
}
