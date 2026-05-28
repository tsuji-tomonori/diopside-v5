import { synthLocalInventory } from "../infra/bin/app.js";
import { createLocalApi } from "../apps/api/src/local-api.js";
import { assert, readText } from "./lib.js";

const inventory = synthLocalInventory("dev");
const catalog = inventory.intent_catalog;

const edge = catalog.EdgeStaticConstruct.edgeRoutingIntent;
assert(edge.viewerRequestFunction === "saphnexa-viewer-router", "CloudFront Function intent missing");
assert(edge.singleEntryOrigin === "cloudfront", "single entry origin intent mismatch");
assert(edge.originAccess === "oac-only", "OAC only intent missing");
assert(edge.internalApiPrefix === "/api/", "internal API prefix intent missing");
assert(edge.authPrefix === "/auth/", "auth prefix intent missing");
assert(edge.spaFallback === "/chat/index.html", "SPA fallback intent missing");
assert(edge.wafAttached === true, "WAF attachment intent missing");
for (const prefix of ["/admin/docs/", "/admin/test-reports/"]) {
  assert(edge.adminArtifactPrefixes.includes(prefix), `admin artifact prefix missing: ${prefix}`);
  assert(edge.signedCookieRequiredPrefixes.includes(prefix), `signed cookie prefix missing: ${prefix}`);
}

const routesSource = readText("apps/web/src/routes.ts");
for (const path of ["/", "/chat", "/admin", "/admin/docs/latest/", "/admin/test-reports/allure/latest/"]) {
  assert(routesSource.includes(`path: "${path}"`), `single entry route missing: ${path}`);
}
assert(routesSource.includes("rewrite: \"/chat/index.html\""), "root rewrite intent missing");

const realtime = catalog.RealtimeConstruct.channelPolicyIntent;
assert(realtime.ticketTtlSeconds === 60, "ws ticket TTL intent mismatch");
assert(realtime.ticketSingleUse === true, "ws ticket single-use intent missing");
assert(realtime.userScopedPattern === "/users/{user_id}/chat/*", "ws user channel scope intent missing");
assert(realtime.subscribeAuthorizer === "ws-ticket", "ws-ticket authorizer intent missing");
const api = createLocalApi();
const csrf = api.request("user-owner", "getMe").body.csrf_token;
const ticket = api.request("user-owner", "issueWsTicket", { csrf_token: csrf, now_ms: 0 });
assert(ticket.status === 201, "local ws ticket issue failed");
assert(ticket.body.expires_in_seconds === realtime.ticketTtlSeconds, "local ws ticket TTL mismatch");
assert(ticket.body.channels.every((channel) => channel.startsWith("/users/user-owner/chat/")), "local ws ticket scope mismatch");
assert(api.request("user-owner", "consumeWsTicket", { ticket_id: ticket.body.ticket, now_ms: 1000 }).status === 200, "local ws ticket consume failed");
assert(api.request("user-owner", "consumeWsTicket", { ticket_id: ticket.body.ticket, now_ms: 2000 }).body.error_code === "WS_TICKET_REUSED", "local ws ticket must be single-use");

const data = catalog.DataConstruct.kmsPolicyIntent;
assert(data.keyRotationEnabled === true, "KMS rotation intent missing");
assert(data.bucketEncryption === "SSE-KMS", "SSE-KMS intent missing");
assert(data.deniedPublicAccess === true, "public access deny intent missing");
for (const principal of ["s3.amazonaws.com", "lambda.amazonaws.com"]) {
  assert(data.allowedServicePrincipals.includes(principal), `KMS service principal missing: ${principal}`);
}

const rag = catalog.RagProcessingConstruct.queuePolicyIntent;
assert(rag.queues.length === 3, "queue intent count mismatch");
assert(rag.deadLetterQueues.length === rag.queues.length, "DLQ intent count mismatch");
assert(rag.maxReceiveCount === 3, "DLQ maxReceiveCount intent mismatch");
assert(rag.visibilityTimeoutSeconds >= 300, "queue visibility timeout intent mismatch");

const obs = catalog.ObservabilityCicdConstruct.iamReviewIntent;
assert(obs.cdkNagEnabled === true, "cdk-nag intent missing");
assert(obs.wildcardActionRequiresFinding === true, "IAM wildcard review intent missing");
assert(obs.githubOidcDeployRoleScopedToRepo === true, "GitHub OIDC repo scope intent missing");
assert(obs.permissionsBoundaryRequired === true, "permissions boundary intent missing");

const baseline = readText("infra/aspects/security-baseline.js");
for (const token of ["CloudFront must attach WAF", "IAM wildcard actions", "cdk-nag findings", "SQS queues must attach DLQs", "CloudWatch log retention"]) {
  assert(baseline.includes(token), `security baseline missing: ${token}`);
}

console.log("edge security intent check passed");
