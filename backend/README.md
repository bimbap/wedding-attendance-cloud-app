# Wedding Attendance — Backend Lambda (`wa-lambda`)

This directory contains the **Node.js 24 ESM** serverless handler for the Wedding Attendance & RSVP Guestbook application.

---

## 🔐 Lambda Environment Variables

[`index.js`](index.js) enforces runtime environment validation via `process.env`. All required variables must be configured in **AWS Lambda Environment Variables** (**Configuration** -> **Environment variables**).

The provided [`.env.example`](.env.example) reference is **intentionally incomplete**:

```dotenv
TABLE_NAME=
```

Inspect [`index.js`](index.js) to identify all required environment variable keys and configure their appropriate values in the AWS Lambda Console.
