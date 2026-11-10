# Get Attendees Microservice (`wa-get-attendees-lambda`)

Reads confirmed wedding attendees from Amazon DynamoDB, computes live attendance metrics (`totalRsvp`, `totalAttending`, `totalPaxConfirmed`), and returns the guestbook feed on `GET /attendees`.

---

## ⚙️ Function Configuration

| Parameter | Recommended Specification | Notes |
|---|---|---|
| **Function Name** | `wa-get-attendees-lambda` | Standard competition resource naming |
| **Runtime** | `Node.js 20.x` or `Node.js 24.x` | Native ESM module |
| **Handler** | `index.handler` | Points to [`index.js`](index.js) |
| **Architecture** | `x86_64` | Standard x86 architecture |
| **Memory Allocation** | `128 MB` | Optimal for batch scanning up to 100+ items |
| **Timeout** | `10 seconds` | Accommodates DynamoDB network latency & cold starts |
| **Execution Role** | `LabRole` | Must have DynamoDB read permissions |
| **Attached Layer** | `wa-layer` | Required for `@aws-sdk/client-dynamodb` & `@aws-sdk/lib-dynamodb` |
| **Attached Package** | `package.json` | Input the package with `index.js` in lambda explorer for Node.js runtime |

---

## 🔐 Environment Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `TABLE_NAME` | **Yes** | Target Amazon DynamoDB table name | `wa-attendance-table` |

*(Note: `AWS_REGION` is automatically provided by the Lambda runtime).*

---

## 🌐 API Gateway Integration

- **Resource**: `/attendees`
- **Method**: `GET`
- **Integration Type**: `Lambda Proxy Integration` (`AWS_PROXY`)
- **CORS Preflight**: Required (`OPTIONS` Mock Integration)

---

## 📤 Sample Response (`200 OK`)

```json
{
  "status": "success",
  "stats": {
    "totalRsvp": 3,
    "totalAttending": 2,
    "totalDeclined": 1,
    "totalPaxConfirmed": 4
  },
  "data": [
    {
      "guestId": "WA-9B41FA",
      "name": "Jordan Lee & Partner",
      "relationship": "Family",
      "attendanceStatus": "Attending",
      "pax": 2,
      "wishes": "Wishing you both a lifetime of happiness!",
      "createdAt": "2026-11-10T10:00:00.000Z"
    }
  ]
}
```

