/**
 * AWS Lambda Handler — wa-get-attendees-lambda
 * Runtime: Node.js 20.x / 24.x / 26.x ESM
 * Route: GET /attendees
 * 
 * Required Environment Variables (AWS Lambda Console):
 * - TABLE_NAME: Target DynamoDB table name (e.g., "wa-attendance-table")
 * 
 * Note: AWS_REGION is automatically injected by the AWS Lambda runtime environment.
 */

import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, ScanCommand } from "@aws-sdk/lib-dynamodb";

const REGION = process.env.AWS_REGION || "us-east-1";
const TABLE_NAME = (process.env.TABLE_NAME || "").trim();

const ddbClient = new DynamoDBClient({ region: REGION });
const docClient = DynamoDBDocumentClient.from(ddbClient, {
  marshallOptions: { removeUndefinedValues: true }
});

const CORS_HEADERS = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,Authorization"
};

export const handler = async (event, context) => {
  const requestId = context?.awsRequestId || "get-" + Date.now();
  const method = event?.httpMethod || event?.requestContext?.http?.method || "GET";

  console.log(JSON.stringify({
    level: "INFO",
    message: "Retrieve attendees request received",
    requestId,
    httpMethod: method,
    tableName: TABLE_NAME,
    timestamp: new Date().toISOString()
  }));

  if (method === "OPTIONS") {
    return {
      statusCode: 200,
      headers: CORS_HEADERS,
      body: JSON.stringify({ message: "CORS Preflight OK" })
    };
  }

  if (!TABLE_NAME) {
    console.error(JSON.stringify({
      level: "ERROR",
      message: "Configuration Error: TABLE_NAME environment variable is missing",
      requestId
    }));
    return {
      statusCode: 500,
      headers: CORS_HEADERS,
      body: JSON.stringify({ status: "error", message: "Configuration Error: TABLE_NAME is missing" })
    };
  }

  try {
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
      message: "Retrieved attendees successfully",
      requestId,
      count: attendees.length,
      stats,
      timestamp: new Date().toISOString()
    }));

    return {
      statusCode: 200,
      headers: CORS_HEADERS,
      body: JSON.stringify({
        status: "success",
        stats,
        data: attendees
      })
    };
  } catch (err) {
    console.error(JSON.stringify({
      level: "ERROR",
      message: "DynamoDB Scan failed",
      requestId,
      error: err.message,
      stack: err.stack
    }));

    return {
      statusCode: 500,
      headers: CORS_HEADERS,
      body: JSON.stringify({
        status: "error",
        message: "Failed to retrieve attendees from database",
        details: err.message
      })
    };
  }
};
