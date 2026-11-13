# Wedding Attendance — Backend Lambda Microservices

This directory contains the serverless compute handlers for the Wedding Attendance & RSVP application, decomposed into three single-purpose microservice functions for modern cloud reliability.

---

## 🏗️ Microservice Architecture

Each Lambda function handles a specific API Gateway route and HTTP method:

| Function Name | Directory | Route | Method | Memory | Timeout | Required Env Vars | Attached Layer |
|---|---|---|---|---|---|---|---|
| **`wa-health-lambda`** | [`health/`](health/) | `/health` | `GET` | `128 MB` | `5s` | *None* | *None (zero external dependencies)* |
| **`wa-get-attendees-lambda`** | [`get-attendees/`](get-attendees/) | `/attendees` | `GET` | `128 MB` | `10s` | `TABLE_NAME` | `wa-layer` (DynamoDB SDK) |
| **`wa-post-attendee-lambda`** | [`post-attendee/`](post-attendee/) | `/attendees` | `POST` | `128 MB` | `10s` | `TABLE_NAME`, `TICKET_PREFIX`, `TOPIC_ARN` | `wa-layer` (DynamoDB & SNS SDK) |

---

## 📁 Directory Structure

```text
backend/
├── README.md                      # Backend microservices guide (this document)
├── .env.example                   # Environment variable reference
├── package.json                   # Shared root package manifest
├── layer/                         # Shared AWS SDK Layer (@aws-sdk/client-dynamodb, @aws-sdk/client-sns)
│   ├── README.md                  # Layer packaging guide
│   └── package.json               # Layer dependencies manifest
├── health/                        # wa-health-lambda
│   ├── README.md                  # Health probe configuration & response spec
│   └── index.js                   # Pure Node.js health probe
├── get-attendees/                 # wa-get-attendees-lambda
│   ├── README.md                  # Attendees query, stats aggregator & response spec
│   └── index.js                   # Scans DynamoDB & calculates attendance statistics
└── post-attendee/                 # wa-post-attendee-lambda
    ├── README.md                  # Ingestion, validation, ticket generator & SNS alert spec
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

## ⚙️ Function Runtime & Performance Settings

All functions use standard AWS Lambda configuration:
- **Runtime**: `Node.js 20.x`, `Node.js 24.x`, or `Node.js 26.x` (ESM mode)
- **Architecture**: `x86_64`
- **Handler**: `index.handler`
- **Memory Allocation**: `128 MB`
- **Timeout**:
  - `wa-health-lambda`: `5 seconds`
  - `wa-get-attendees-lambda`: `10 seconds`
  - `wa-post-attendee-lambda`: `10 seconds`
- **Execution Role**: Use pre-configured `LabRole`