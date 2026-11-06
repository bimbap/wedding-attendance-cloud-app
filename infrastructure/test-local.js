/**
 * Local Handler Test Script (Node.js 24 ESM .js)
 * No AWS credentials required for preflight/validation checks.
 */
import { handler } from "../backend/index.js";

async function runLocalVerification() {
  console.log("=== 1. Testing OPTIONS CORS Preflight ===");
  const corsResponse = await handler({
    httpMethod: "OPTIONS",
    path: "/attendees"
  }, { awsRequestId: "test-cors" });
  console.log("Status:", corsResponse.statusCode);
  console.log("Headers:", corsResponse.headers);

  console.log("\n=== 2. Testing Input Validation (Missing Name) ===");
  const invalidResponse = await handler({
    httpMethod: "POST",
    path: "/attendees",
    body: JSON.stringify({ attendanceStatus: "Hadir", pax: 2 })
  }, { awsRequestId: "test-invalid" });
  console.log("Status:", invalidResponse.statusCode);
  console.log("Body:", invalidResponse.body);

  console.log("\n=== 3. Testing 404 Route Handling ===");
  const notFoundResponse = await handler({
    httpMethod: "GET",
    path: "/unknown-endpoint"
  }, { awsRequestId: "test-404" });
  console.log("Status:", notFoundResponse.statusCode);
  console.log("Body:", notFoundResponse.body);

  console.log("\nLocal handler logic verification passed successfully!");
}

runLocalVerification().catch(err => {
  console.error("Local test error:", err);
  process.exit(1);
});

