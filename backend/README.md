# Wedding Attendance — Backend Lambda (`wa-lambda`)

This directory contains the stateless **Node.js 24 ESM** serverless handler for the Wedding Attendance & RSVP Guestbook application.

---

## 🔐 Mandatory Environment Configuration (`.env`)

Unlike basic demonstration functions with hardcoded defaults, [`index.js`](index.js) enforces **strict runtime environment validation**. If any mandatory environment variable is missing or invalid, the Lambda function will reject incoming requests with HTTP `500 Configuration Error` and log an `[ERROR]` audit entry to Amazon CloudWatch Logs.

### ⚠️ Challenge Notice: Incomplete `.env.example`

The provided [`.env.example`](.env.example) file is **intentionally incomplete** and contains blank values:

```dotenv
AWS_REGION=
TABLE_NAME=

# TODO: Add the remaining required environment variables below
```

To successfully deploy and run `wa-lambda`, you must:
1. Copy `.env.example` to `.env` (or configure Lambda Environment Variables in the AWS Console).
2. **Inspect [`index.js`](index.js)** (look for `REQUIRED_ENV_KEYS` and `validateEnvironment()`) to discover **all mandatory environment variable names** that the handler expects.
3. Determine the exact required values based on the project's resource naming rules, DynamoDB table schema, and ticket code format (`WA-XXXXXX`).

---

## 🛠️ How `.env` is Loaded by the Handler

`index.js` includes a built-in, zero-dependency `.env` loader that checks for a local `.env` file in the Lambda execution directory (`/var/task/.env`) during cold-start initialization, while also supporting native AWS Lambda Environment Variables:

| Method | How to Configure |
|---|---|
| **Option A: Bundled `.env` File** | Create `backend/.env` with all required key-value pairs and include it alongside `index.js` in the Lambda code editor or `.zip` deployment archive. |
| **Option B: Lambda Console Environment Variables** | In AWS Lambda Console -> **Configuration** -> **Environment variables** -> **Edit**, add each required key and value. |