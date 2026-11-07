# Wedding Attendance — Backend Lambda (`wa-lambda`)

This directory contains the **Node.js 24 ESM** serverless handler for the Wedding Attendance & RSVP Guestbook application.

---

## 🔐 Lambda Environment Variables

[`index.js`](index.js) enforces runtime environment validation via `process.env`. All required variables must be configured in **AWS Lambda Environment Variables** (**Configuration** -> **Environment variables**).

The provided [`.env.example`](.env.example) reference is **intentionally incomplete**:

```dotenv
TABLE_NAME=
```

Inspect [`index.js`](index.js) to identify all required environment variable keys and configure their appropriate values in the AWS Lambda Console:
- `TABLE_NAME`: Target DynamoDB table name (e.g., `wa-dynamodb` or `wa-attendance-table`).
- `TICKET_PREFIX`: Prefix for guest registration ticket code (e.g., `WA`).

---

## ⚙️ Lambda General Configuration

Configure these parameters under **Configuration** -> **General configuration**:

| Setting | Recommended Value |
|---|---|
| **Runtime** | `Node.js 20.x` or `Node.js 24.x` |
| **Handler** | `index.handler` |
| **Memory** | `256 MB` |
| **Timeout** | `15 sec` |

---

## 📦 Required `package.json` for ES Modules

Since [`index.js`](index.js) uses modern ECMAScript Module (ESM) syntax (`import`/`export`), AWS Lambda requires a [`package.json`](package.json) file in the root function directory (`/var/task/`) specifying `"type": "module"`:

```json
{
  "name": "wa-lambda",
  "version": "1.0.0",
  "type": "module"
}
```

> **Important**: If you deploy `index.js` alone without `package.json`, Node.js defaults to CommonJS and will fail with `SyntaxError: Cannot use import statement outside a module`. Ensure both `index.js` and `package.json` are deployed together to the Lambda function.

---

## 🧪 Lambda Console Test Events (Mock JSON)

Test your Lambda function directly inside the **AWS Lambda Console** (under the **Test** tab) using these standard API Gateway Lambda Proxy mock events:

### 1. Health Check (`GET /health`)
Verify configuration and environment variable loading without invoking DynamoDB:
```json
{
  "httpMethod": "GET",
  "path": "/health"
}
```

### 2. Submit Attendance RSVP (`POST /attendees`)
Verify database write operations (`PutCommand`) and ticket generation:
```json
{
  "httpMethod": "POST",
  "path": "/attendees",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"name\":\"Arya & Partner\",\"relationship\":\"Family\",\"attendanceStatus\":\"Attending\",\"pax\":2,\"wishes\":\"Congratulations and best wishes for a wonderful life together!\"}"
}
```

### 3. Retrieve Attendees & Summary Statistics (`GET /attendees`)
Verify database read operations (`ScanCommand`) and statistical calculations:
```json
{
  "httpMethod": "GET",
  "path": "/attendees"
}
```
