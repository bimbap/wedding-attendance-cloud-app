# Wedding Attendance — Backend Lambda Microservices

This directory contains the serverless compute handlers for the Wedding Attendance & RSVP application, decomposed into three single-purpose microservice functions for modern cloud reliability.

---

## 🏗️ Microservice Architecture

Each Lambda function handles a specific API Gateway route and HTTP method:

| Function Name | Directory | Route | Method | Required Env Vars | Attached Layer |
|---|---|---|---|---|---|
| **`wa-health-lambda`** | [`health/`](health/) | `/health` | `GET` | *None* | *None (zero external dependencies)* |
| **`wa-get-attendees-lambda`** | [`get-attendees/`](get-attendees/) | `/attendees` | `GET` | `TABLE_NAME` | `wa-layer` (DynamoDB SDK) |
| **`wa-post-attendee-lambda`** | [`post-attendee/`](post-attendee/) | `/attendees` | `POST` | `TABLE_NAME`, `TICKET_PREFIX`, `TOPIC_ARN` | `wa-layer` (DynamoDB & SNS SDK) |

---

## 📁 Directory Structure

```text
backend/
├── README.md                      # Backend microservices guide
├── .env.example                   # Environment variable reference
├── package.json                   # Shared root package manifest
├── layer/                         # Shared AWS SDK Layer (@aws-sdk/client-dynamodb, @aws-sdk/client-sns)
│   ├── README.md                  # Layer packaging guide
│   └── package.json               # Layer dependencies manifest
├── health/                        # wa-health-lambda
│   └── index.js                   # Pure Node.js health probe
├── get-attendees/                 # wa-get-attendees-lambda
│   └── index.js                   # Scans DynamoDB & calculates attendance statistics
└── post-attendee/                 # wa-post-attendee-lambda
    └── index.js                   # Persists RSVP to DynamoDB & triggers SNS notification
```

---

## 🔐 Environment Variables Configuration

Configure the required variables per function in the **AWS Lambda Console** (**Configuration** -> **Environment variables**):

### 1. `wa-health-lambda`
- No custom environment variables required.

### 2. `wa-get-attendees-lambda`
- `TABLE_NAME`: Target DynamoDB table name (e.g., `wa-attendance-table`).

### 3. `wa-post-attendee-lambda`
- `TABLE_NAME`: Target DynamoDB table name (e.g., `wa-attendance-table`).
- `TICKET_PREFIX`: Prefix for generated guest tickets (e.g., `WA`).
- `TOPIC_ARN`: *(Optional / Bonus)* Target Amazon SNS Topic ARN (e.g., `arn:aws:sns:us-east-1:123456789012:wa-rsvp-topic`) to receive real-time email alerts whenever a new guest RSVP is confirmed.

*(Note: `AWS_REGION` is automatically provided by the Lambda runtime).*

---

## ⚙️ Function Runtime Settings

All functions use standard AWS Lambda configuration:
- **Runtime**: `Node.js 20.x` or `Node.js 24.x`
- **Architecture**: `x86_64`
- **Handler**: `index.handler`
- **Execution Role**: Use pre-configured `LabRole`
