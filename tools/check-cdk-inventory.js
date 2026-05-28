import { synthLocalInventory } from "../infra/bin/app.js";
import { assert } from "./lib.js";

const inventory = synthLocalInventory("dev");
assert(inventory.region === "ap-northeast-1", "CDK inventory must target ap-northeast-1");
assert(inventory.construct_count === 7, "CDK inventory must contain 7 constructs");
for (const construct of ["EdgeStaticConstruct", "IdentityConstruct", "ApiConstruct", "RealtimeConstruct", "DataConstruct", "RagProcessingConstruct", "ObservabilityCicdConstruct"]) {
  assert(inventory.constructs.includes(construct), `missing construct ${construct}`);
  assert(inventory.intent_catalog[construct].resources.length > 0, `missing resources for ${construct}`);
  assert(inventory.intent_catalog[construct].outputs.length > 0, `missing outputs for ${construct}`);
}
assert(inventory.intent_catalog.EdgeStaticConstruct.edgeRoutingIntent.viewerRequestFunction, "edge routing intent missing");
assert(inventory.intent_catalog.RealtimeConstruct.channelPolicyIntent.subscribeAuthorizer === "ws-ticket", "realtime channel policy intent missing");
assert(inventory.intent_catalog.DataConstruct.kmsPolicyIntent.bucketEncryption === "SSE-KMS", "KMS intent missing");
assert(inventory.intent_catalog.RagProcessingConstruct.queuePolicyIntent.deadLetterQueues.length > 0, "DLQ intent missing");
assert(inventory.intent_catalog.ObservabilityCicdConstruct.iamReviewIntent.cdkNagEnabled === true, "cdk-nag intent missing");

console.log("local CDK synth inventory check passed");
