import crypto from "crypto";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, ScanCommand, PutCommand } from "@aws-sdk/lib-dynamodb";

const REGION = process.env.AWS_REGION || "us-east-1";

/**
 * Required Environment Variables Configuration:
 * Configure these keys in AWS Lambda Console (Configuration -> Environment variables):
 * 
 * - TABLE_NAME    : Name of the target DynamoDB table (e.g., "wa-dynamodb")
 * - TICKET_PREFIX : Prefix string prepended to generated ticket IDs (e.g., "WA" or "RSVP")
 * 
 * Note: AWS_REGION is automatically injected by the AWS Lambda runtime environment.
 */

export const REQUIRED_ENV_KEYS = [
  "TABLE_NAME",
  "TICKET_PREFIX" 
];

const ddbClient = new DynamoDBClient({ region: REGION });
const docClient = DynamoDBDocumentClient.from(ddbClient, {
  marshallOptions: { removeUndefinedValues: true }
});

const CORS_HEADERS = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Requested-With"
};

const buildResponse = (statusCode, bodyObj) => ({
  statusCode,
  headers: CORS_HEADERS,
  body: JSON.stringify(bodyObj)
});

function validateEnvironment() {
  const missingKeys = REQUIRED_ENV_KEYS.filter(
    key => !process.env[key] || String(process.env[key]).trim() === ""
  );
  return {
    isValid: missingKeys.length === 0,
    missingKeys
  };
}

export const handler = async (event, context) => {
  const requestId = context?.awsRequestId || "req-" + Date.now();
  const method = event?.httpMethod || event?.requestContext?.http?.method || "GET";
  const reqPath = event?.path || event?.rawPath || "/";

  console.log(JSON.stringify({
    level: "INFO",
    message: "Incoming Request Received",
    requestId,
    httpMethod: method,
    path: reqPath,
    sourceIp: event?.requestContext?.identity?.sourceIp || event?.requestContext?.http?.sourceIp,
    userAgent: event?.headers?.["User-Agent"] || event?.headers?.["user-agent"] || event?.requestContext?.http?.userAgent,
    timestamp: new Date().toISOString()
  }));

  if (method === "OPTIONS") {
    return buildResponse(200, { message: "CORS Preflight OK" });
  }

  const envCheck = validateEnvironment();
  if (!envCheck.isValid) {
    console.error(JSON.stringify({
      level: "ERROR",
      message: "Configuration Error: Missing required environment variables",
      requestId,
      missingKeys: envCheck.missingKeys,
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
  try {
    if (method === "GET" && (reqPath === "/health" || reqPath.endsWith("/health"))) {
      return buildResponse(200, {
        status: "healthy",
        region: REGION,
        tableName: TABLE_NAME,
        ticketPrefix: TICKET_PREFIX,
        timestamp: new Date().toISOString()
      });
    }

    if (method === "GET" && (reqPath === "/attendees" || reqPath.endsWith("/attendees") || reqPath === "/")) {
      const scanResult = await docClient.send(new ScanCommand({ TableName: TABLE_NAME }));
      const attendees = scanResult.Items || [];

      attendees.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

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

      const { name, attendanceStatus, pax, wishes, relationship } = body;

      if (!name || typeof name !== "string" || name.trim().length === 0) {
        return buildResponse(400, { status: "error", message: "Field 'name' is required" });
      }

      let resolvedStatus = "Attending";
      if (attendanceStatus === "Declined" || attendanceStatus === "Tidak Hadir") {
        resolvedStatus = "Declined";
      } else if (attendanceStatus === "Tentative" || attendanceStatus === "Ragu-Ragu") {
        resolvedStatus = "Tentative";
      }

      const resolvedPax = resolvedStatus === "Attending" ? Math.max(1, Math.min(10, Number(pax) || 1)) : 0;
      const resolvedWishes = wishes && typeof wishes === "string" ? wishes.trim() : "Congratulations and best wishes for a wonderful life together!";
      const resolvedRelationship = relationship || "Friend";

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
        createdAt
      };

      await docClient.send(new PutCommand({
        TableName: TABLE_NAME,
        Item: newAttendee
      }));

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

    return buildResponse(404, {
      status: "error",
      message: `Resource not found for ${method} ${reqPath}`
    });

  } catch (error) {
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
