import crypto from "crypto";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// -----------------------------------------------------------------------------
// 1. Built-in Zero-Dependency .env Loader
// -----------------------------------------------------------------------------
const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadDotEnv() {
  const candidates = [
    path.join(__dirname, ".env"),
    path.resolve(process.cwd(), ".env")
  ];

  for (const envPath of candidates) {
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, "utf-8");
      for (const rawLine of content.split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith("#")) continue;
        const eqIdx = line.indexOf("=");
        if (eqIdx === -1) continue;
        const key = line.slice(0, eqIdx).trim();
        const val = line.slice(eqIdx + 1).trim().replace(/^['"]|['"]$/g, "");
        if (key && process.env[key] === undefined) {
          process.env[key] = val;
        }
      }
      break;
    }
  }
}

loadDotEnv();

// -----------------------------------------------------------------------------
// 2. Mandatory Environment Variable Validation
//    Participants must configure these in backend/.env or Lambda Configuration:
//    - AWS_REGION    (e.g. us-east-1)
//    - TABLE_NAME    (DynamoDB table name, e.g. wa-attendance-table)
//    - TICKET_PREFIX (Ticket ID prefix without hyphen, e.g. WA)
//    - SERVICE_NAME  (Service identifier for health telemetry, e.g. wa-attendance-api)
// -----------------------------------------------------------------------------
export const REQUIRED_ENV_KEYS = [
  "AWS_REGION",
  "TABLE_NAME",
  "TICKET_PREFIX",
  "SERVICE_NAME"
];

function validateEnvironment() {
  loadDotEnv();
  const missingKeys = REQUIRED_ENV_KEYS.filter(
    key => !process.env[key] || String(process.env[key]).trim() === ""
  );
  return {
    isValid: missingKeys.length === 0,
    missingKeys
  };
}

// Global DynamoDB client reference
let docClient = null;
let isLocalMockMode = false;
const inMemoryStore = [];

// Initialize DynamoDB Client (Graceful fallback to memory mock if run outside Lambda without node_modules)
try {
  const { DynamoDBClient } = await import("@aws-sdk/client-dynamodb");
  const { DynamoDBDocumentClient } = await import("@aws-sdk/lib-dynamodb");
  const ddbClient = new DynamoDBClient({
    region: process.env.AWS_REGION || "us-east-1"
  });
  docClient = DynamoDBDocumentClient.from(ddbClient, {
    marshallOptions: { removeUndefinedValues: true }
  });
} catch {
  isLocalMockMode = true;
  console.log(JSON.stringify({
    level: "INFO",
    message: "AWS SDK not found locally. Running with built-in In-Memory Mock Database for offline verification."
  }));
}

// Standard CORS headers for API Gateway Lambda Proxy integration
const CORS_HEADERS = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Requested-With"
};

/**
 * Standard HTTP response helper
 */
const buildResponse = (statusCode, bodyObj) => ({
  statusCode,
  headers: CORS_HEADERS,
  body: JSON.stringify(bodyObj)
});

/**
 * Main Lambda Handler
 */
export const handler = async (event, context) => {
  const requestId = context?.awsRequestId || "req-" + Date.now();
  
  // Normalize HTTP method and path for both REST API (v1) and HTTP API (v2)
  const method = event?.httpMethod || event?.requestContext?.http?.method || "GET";
  const reqPath = event?.path || event?.rawPath || "/";

  // Structured Logging for CloudWatch Logs
  console.log(JSON.stringify({
    level: "INFO",
    message: "Incoming Request Received",
    requestId,
    httpMethod: method,
    path: reqPath,
    sourceIp: event?.requestContext?.identity?.sourceIp || event?.requestContext?.http?.sourceIp,
    userAgent: event?.headers?.["User-Agent"] || event?.headers?.["user-agent"] || event?.requestContext?.http?.userAgent,
    mockMode: isLocalMockMode,
    timestamp: new Date().toISOString()
  }));

  // Handle Preflight CORS Request immediately
  if (method === "OPTIONS") {
    return buildResponse(200, { message: "CORS Preflight OK" });
  }

  // Enforce Mandatory Environment Variables (.env / Lambda Env Vars)
  const envCheck = validateEnvironment();
  if (!envCheck.isValid) {
    console.error(JSON.stringify({
      level: "ERROR",
      message: "Configuration Error: Missing required environment variables",
      requestId,
      missingKeys: envCheck.missingKeys,
      hint: "Inspect backend/README.md and backend/index.js to configure all required environment variables.",
      timestamp: new Date().toISOString()
    }));

    return buildResponse(500, {
      status: "error",
      message: `Configuration Error: Missing required environment variables: ${envCheck.missingKeys.join(", ")}`,
      requestId
    });
  }

  const TABLE_NAME = process.env.TABLE_NAME.trim();
  const TICKET_PREFIX = process.env.TICKET_PREFIX.trim().replace(/-$/, "");
  const SERVICE_NAME = process.env.SERVICE_NAME.trim();

  try {
    // -------------------------------------------------------------------------
    // Route 1: GET /health - Basic health check
    // -------------------------------------------------------------------------
    if (method === "GET" && (reqPath === "/health" || reqPath.endsWith("/health"))) {
      return buildResponse(200, {
        status: "healthy",
        service: SERVICE_NAME,
        region: process.env.AWS_REGION.trim(),
        tableName: TABLE_NAME,
        ticketPrefix: TICKET_PREFIX,
        mode: isLocalMockMode ? "InMemoryMock" : "DynamoDBLive",
        timestamp: new Date().toISOString()
      });
    }

    // -------------------------------------------------------------------------
    // Route 2: GET /attendees or GET / - List all attendees and compute summary stats
    // -------------------------------------------------------------------------
    if (method === "GET" && (reqPath === "/attendees" || reqPath.endsWith("/attendees") || reqPath === "/")) {
      let attendees = [];

      if (!isLocalMockMode && docClient) {
        const { ScanCommand } = await import("@aws-sdk/lib-dynamodb");
        const scanResult = await docClient.send(new ScanCommand({ TableName: TABLE_NAME }));
        attendees = scanResult.Items || [];
      } else {
        attendees = [...inMemoryStore];
      }

      // Sort descending by createdAt
      attendees.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

      // Calculate operational statistics for wedding organizers
      const isAttending = a => a.attendanceStatus === "Attending" || a.attendanceStatus === "Hadir";
      const isDeclined = a => a.attendanceStatus === "Declined" || a.attendanceStatus === "Tidak Hadir";
      const isTentative = a => a.attendanceStatus === "Tentative" || a.attendanceStatus === "Ragu-Ragu";

      const stats = {
        totalRsvp: attendees.length,
        totalAttending: attendees.filter(isAttending).length,
        totalHadir: attendees.filter(isAttending).length,
        totalDeclined: attendees.filter(isDeclined).length,
        totalTidakHadir: attendees.filter(isDeclined).length,
        totalTentative: attendees.filter(isTentative).length,
        totalRagu: attendees.filter(isTentative).length,
        totalPaxConfirmed: attendees
          .filter(isAttending)
          .reduce((sum, a) => sum + (Number(a.pax) || 1), 0)
      };

      console.log(JSON.stringify({
        level: "INFO",
        message: "Retrieved attendees list and summary statistics",
        requestId,
        count: attendees.length,
        stats,
        timestamp: new Date().toISOString()
      }));

      return buildResponse(200, {
        status: "success",
        stats,
        data: attendees
      });
    }

    // -------------------------------------------------------------------------
    // Route 3: POST /attendees - Register attendance RSVP & Wishes
    // -------------------------------------------------------------------------
    if (method === "POST" && (reqPath === "/attendees" || reqPath.endsWith("/attendees") || reqPath === "/")) {
      let body = {};
      try {
        body = typeof event.body === "string" ? JSON.parse(event.body || "{}") : (event.body || {});
      } catch (err) {
        console.warn(JSON.stringify({
          level: "WARN",
          message: "Failed to parse JSON request body",
          requestId,
          rawBody: event.body,
          error: err.message
        }));
        return buildResponse(400, { status: "error", message: "Invalid JSON format in request body" });
      }

      // Input Validation
      const { name, attendanceStatus, pax, wishes, relationship } = body;

      if (!name || typeof name !== "string" || name.trim().length === 0) {
        return buildResponse(400, { status: "error", message: "Field 'name' is required" });
      }

      // Normalize status (supports both English and legacy Indonesian inputs)
      let resolvedStatus = "Attending";
      if (attendanceStatus === "Declined" || attendanceStatus === "Tidak Hadir") {
        resolvedStatus = "Declined";
      } else if (attendanceStatus === "Tentative" || attendanceStatus === "Ragu-Ragu") {
        resolvedStatus = "Tentative";
      }

      const resolvedPax = resolvedStatus === "Attending" ? Math.max(1, Math.min(10, Number(pax) || 1)) : 0;
      const resolvedWishes = wishes && typeof wishes === "string" ? wishes.trim() : "Congratulations and best wishes for a wonderful life together!";
      const resolvedRelationship = relationship || "Friend";

      // Generate Unique Guest Ticket Code & ID using TICKET_PREFIX from environment
      const randomSuffix = crypto.randomBytes(3).toString("hex").toUpperCase();
      const guestId = `${TICKET_PREFIX}-${randomSuffix}`;
      const createdAt = new Date().toISOString();

      const newAttendee = {
        guestId,
        name: name.trim(),
        attendanceStatus: resolvedStatus,
        pax: resolvedPax,
        wishes: resolvedWishes,
        relationship: resolvedRelationship,
        createdAt,
        checkInTime: null
      };

      // Persist to DynamoDB or Mock Store
      if (!isLocalMockMode && docClient) {
        const { PutCommand } = await import("@aws-sdk/lib-dynamodb");
        await docClient.send(new PutCommand({
          TableName: TABLE_NAME,
          Item: newAttendee
        }));
      } else {
        inMemoryStore.push(newAttendee);
      }

      // Structured CloudWatch Audit Log
      console.log(JSON.stringify({
        level: "INFO",
        message: "New Wedding Guest Attendance Registered",
        requestId,
        guestId,
        name: newAttendee.name,
        attendanceStatus: resolvedStatus,
        pax: resolvedPax,
        tableName: TABLE_NAME,
        timestamp: createdAt
      }));

      return buildResponse(201, {
        status: "success",
        message: "Wedding Attendance RSVP successfully recorded! Thank you for your confirmation and warm blessings.",
        ticket: {
          guestId,
          name: newAttendee.name,
          attendanceStatus: resolvedStatus,
          pax: resolvedPax,
          createdAt
        }
      });
    }

    // Default 404 Route
    return buildResponse(404, {
      status: "error",
      message: `Resource not found for ${method} ${reqPath}`
    });

  } catch (error) {
    // Structured CloudWatch Error Log
    console.error(JSON.stringify({
      level: "ERROR",
      message: "Unhandled Exception in Lambda Handler",
      requestId,
      errorMessage: error.message,
      stack: error.stack,
      tableName: TABLE_NAME,
      timestamp: new Date().toISOString()
    }));

    return buildResponse(500, {
      status: "error",
      message: "Internal server error occurred while processing request",
      requestId,
      details: error.message
    });
  }
};
