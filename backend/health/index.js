/**
 * AWS Lambda Handler — wa-health-lambda
 * Runtime: Node.js 20.x / 24.x / 26.x ESM
 * Route: GET /health
 * 
 * Responsibilities:
 * - Service health probing
 * - System runtime and region reporting
 * - Zero database or external service dependency (ultra-lightweight & fast)
 */

const REGION = process.env.AWS_REGION || "us-east-1";

const CORS_HEADERS = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,Authorization"
};

export const handler = async (event, context) => {
  const requestId = context?.awsRequestId || "health-" + Date.now();
  const method = event?.httpMethod || event?.requestContext?.http?.method || "GET";

  console.log(JSON.stringify({
    level: "INFO",
    message: "Health check probe received",
    requestId,
    httpMethod: method,
    region: REGION,
    timestamp: new Date().toISOString()
  }));

  if (method === "OPTIONS") {
    return {
      statusCode: 200,
      headers: CORS_HEADERS,
      body: JSON.stringify({ message: "CORS Preflight OK" })
    };
  }

  return {
    statusCode: 200,
    headers: CORS_HEADERS,
    body: JSON.stringify({
      status: "healthy",
      service: "wa-health-service",
      region: REGION,
      runtime: `Node.js ${process.version}`,
      timestamp: new Date().toISOString()
    })
  };
};
