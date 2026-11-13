/**
 * AWS Lambda Handler — wa-post-attendee-lambda
 * Runtime: Node.js 20.x / 24.x / 26.x ESM
 * Route: POST /attendees
 * 
 * Required Environment Variables (AWS Lambda Console):
 * - TABLE_NAME    : Target DynamoDB table name (e.g., "wa-attendance-table")
 * - TICKET_PREFIX : Prefix string prepended to generated ticket IDs (e.g., "WA")
 * - TOPIC_ARN     : (Optional / Bonus) Target SNS Topic ARN for real-time RSVP notification
 * 
 * Note: AWS_REGION is automatically injected by the AWS Lambda runtime environment.
 */

import crypto from "node:crypto";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand } from "@aws-sdk/lib-dynamodb";
import { SNSClient, PublishCommand } from "@aws-sdk/client-sns";

const REGION = process.env.AWS_REGION || "us-east-1";
const TABLE_NAME = (process.env.TABLE_NAME || "").trim();
const TICKET_PREFIX = (process.env.TICKET_PREFIX || "WA").trim().replace(/-$/, "");
const TOPIC_ARN = (process.env.TOPIC_ARN || "").trim();

const ddbClient = new DynamoDBClient({ region: REGION });
const docClient = DynamoDBDocumentClient.from(ddbClient, {
  marshallOptions: { removeUndefinedValues: true }
});

const snsClient = new SNSClient({ region: REGION });

const CORS_HEADERS = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,Authorization"
};

export const handler = async (event, context) => {
  const requestId = context?.awsRequestId || "post-" + Date.now();
  const method = event?.httpMethod || event?.requestContext?.http?.method || "POST";

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

  let body = {};
  try {
    body = typeof event.body === "string" ? JSON.parse(event.body || "{}") : (event.body || {});
  } catch (err) {
    return {
      statusCode: 400,
      headers: CORS_HEADERS,
      body: JSON.stringify({ status: "error", message: "Invalid JSON format in request body" })
    };
  }

  const { name, attendanceStatus, pax, wishes, relationship } = body;

  if (!name || typeof name !== "string" || name.trim().length === 0) {
    return {
      statusCode: 400,
      headers: CORS_HEADERS,
      body: JSON.stringify({ status: "error", message: "Field 'name' is required" })
    };
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
    createdAt,
    checkInTime: null
  };

  try {
    // 1. Persist guest record to DynamoDB
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

    // 2. Trigger SNS Notification on Success (if TOPIC_ARN is configured)
    let notificationSent = false;
    if (TOPIC_ARN) {
      try {
        const subject = `[RSVP Confirmed] ${newAttendee.name} (${newAttendee.attendanceStatus})`;
        const messageBody = [
          `=========================================`,
          `NEW WEDDING ATTENDANCE RSVP RECORDED`,
          `=========================================`,
          `Guest Name    : ${newAttendee.name}`,
          `Status        : ${newAttendee.attendanceStatus}`,
          `Reserved Seats: ${newAttendee.pax} Pax`,
          `Relationship  : ${newAttendee.relationship}`,
          `Ticket ID     : ${newAttendee.guestId}`,
          `Wishes/Notes  : "${newAttendee.wishes}"`,
          `Timestamp     : ${createdAt}`,
          `=========================================`,
          `Notification dispatched via Amazon SNS`
        ].join("\n");

        await snsClient.send(new PublishCommand({
          TopicArn: TOPIC_ARN,
          Subject: subject.slice(0, 100),
          Message: messageBody
        }));

        notificationSent = true;
        console.log(JSON.stringify({
          level: "INFO",
          message: "SNS notification successfully published",
          requestId,
          topicArn: TOPIC_ARN
        }));
      } catch (snsErr) {
        console.warn(JSON.stringify({
          level: "WARN",
          message: "Failed to publish SNS notification (non-fatal)",
          requestId,
          error: snsErr.message
        }));
      }
    }

    // 3. Return HTTP 201 Created Response
    return {
      statusCode: 201,
      headers: CORS_HEADERS,
      body: JSON.stringify({
        status: "success",
        message: "Wedding Attendance RSVP successfully recorded! Thank you for your confirmation and warm blessings.",
        ticket: {
          guestId,
          name: newAttendee.name,
          attendanceStatus: resolvedStatus,
          pax: resolvedPax,
          createdAt
        },
        notificationSent
      })
    };

  } catch (err) {
    console.error(JSON.stringify({
      level: "ERROR",
      message: "Failed to save attendee to DynamoDB",
      requestId,
      error: err.message,
      stack: err.stack
    }));

    return {
      statusCode: 500,
      headers: CORS_HEADERS,
      body: JSON.stringify({
        status: "error",
        message: "Internal server error occurred while processing request",
        details: err.message
      })
    };
  }
};
