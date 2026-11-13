# Post Attendee Microservice (`wa-post-attendee-lambda`)

Validates guest RSVP payloads, generates a unique ticket ID (`WA-XXXXXX`), writes the record to Amazon DynamoDB, and dispatches a notification event to Amazon SNS on `POST /attendees`.

---

## ⚙️ Function Configuration

| Parameter | Recommended Specification | Notes |
|---|---|---|
| **Function Name** | `wa-post-attendee-lambda` | Standard competition resource naming |
| **Runtime** | `Node.js 20.x`, `Node.js 24.x`, or `Node.js 26.x` | Native ESM module |
| **Handler** | `index.handler` | Points to [`index.js`](index.js) |
| **Architecture** | `x86_64` | Standard x86 architecture |
| **Memory Allocation** | `256 MB` | Optimal for document validation & write ops |
| **Timeout** | `15 seconds` | Accommodates DynamoDB write + SNS publish network roundtrips |
| **Execution Role** | `LabRole` | Must have DynamoDB write and SNS publish permissions |
| **Attached Layer** | `wa-layer` | Required for DynamoDB SDK & `@aws-sdk/client-sns` |
| **Attached Package** | `package.json` | Input the package with `index.js` in lambda explorer for Node.js runtime |

---

## 🔐 Environment Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `TABLE_NAME` | **Yes** | Target Amazon DynamoDB table name | `wa-attendance-table` |
| `TICKET_PREFIX` | **Yes** | Prefix for generated guest passes | `WA` |
| `TOPIC_ARN` | *Optional* | Amazon SNS Topic ARN for real-time email alerts | `arn:aws:sns:us-east-1:123456789012:wa-rsvp-topic` |

*(Note: `AWS_REGION` is automatically provided by the Lambda runtime).*

---

## 🌐 API Gateway Integration

- **Resource**: `/attendees`
- **Method**: `POST`
- **Integration Type**: `Lambda Proxy Integration` (`AWS_PROXY`)
- **CORS Preflight**: Required (`OPTIONS` Mock Integration)

---

## 📥 Sample Request Payload

```json
{
  "name": "Jordan Lee & Partner",
  "relationship": "Family",
  "attendanceStatus": "Attending",
  "pax": 2,
  "wishes": "Wishing you both a lifetime of happiness!"
}
```

---

## 📤 Sample Response (`201 Created`)

```json
{
  "status": "success",
  "message": "Wedding Attendance RSVP successfully recorded! Your digital ticket has been generated.",
  "ticket": {
    "guestId": "WA-8F21CB",
    "name": "Jordan Lee & Partner",
    "relationship": "Family",
    "attendanceStatus": "Attending",
    "pax": 2,
    "wishes": "Wishing you both a lifetime of happiness!",
    "createdAt": "2026-11-10T10:15:30.000Z"
  }
}
```

