# Wedding Attendance & RSVP Guestbook — Serverless Multi-Tier Application

**LKS Cloud Computing · Level: Intermediate to Advanced · Scenario: AWS Amplify, API Gateway, Lambda, CloudWatch & DynamoDB**

---

## 📋 Read This First

**Wedding Attendance & RSVP Guestbook** is a production-grade, multi-tier serverless web application designed for modern wedding events and receptions. It replaces paper-based guestbooks with an automated digital RSVP portal, live guest attendance statistics, reserved seating calculation, and a live digital wishes wall.

This application demonstrates the complete **Serverless Application Pattern on AWS**:
1. **Frontend Tier**: Single Page Application (SPA) deployed globally via **AWS Amplify Hosting**.
2. **API Management Tier**: Fully managed HTTPS REST API with Lambda Proxy integration and CORS preflight handling on **Amazon API Gateway**.
3. **Compute Tier**: Stateless event-driven microservices running on **AWS Lambda** (Node.js 24 ESM).
4. **Database Tier**: Fully managed, auto-scaling NoSQL key-value store on **Amazon DynamoDB**.
5. **Observability Tier**: Structured JSON application logging, execution metrics, and latency audit trail in **Amazon CloudWatch Logs**.

---

## 🏗️ Architecture

**Wedding Attendance — Serverless Cloud Architecture**

<p align="center">
  <img src="architecture/Wedding%20Attendance%20Architecture.png" alt="Wedding Attendance Architecture Diagram" width="100%">
</p>

> 💡 *Editable diagram file is available at [`architecture/wedding-attendance.drawio`](architecture/wedding-attendance.drawio).*

---

## 📁 Project Structure

```text
pr-wedding-attendance-app/
├── README.md                      # Challenge brief, architecture & step-by-step lab guide
├── architecture/                  # Visual blueprints & editable draw.io diagrams
│   ├── Wedding Attendance Architecture.png  # High-resolution architecture preview
│   └── wedding-attendance.drawio  # Editable draw.io diagram file
├── frontend/                      # Web application ready for AWS Amplify Hosting
│   ├── index.html                 # Luxury emerald & gold wedding RSVP & digital guestbook
│   ├── style.css                  # Fully responsive CSS with modal passes & stats HUD
│   ├── app.js                     # Dynamic controller: API Gateway integration & local fallback
│   └── amplify.yml                # AWS Amplify Hosting build specification
├── backend/                       # Serverless Lambda function
│   ├── index.js                   # Node.js 24 ESM handler (DynamoDB DocClient + CloudWatch logger)
│   ├── package.json               # Node.js manifest with local test script
│   ├── layer/                     # AWS Lambda Layer packaging for dependencies
│   │   ├── package.json           # Layer dependency manifest (@aws-sdk/client-dynamodb)
│   │   ├── build-layer.sh         # Linux/macOS layer build script (nodejs/node_modules -> zip)
│   │   ├── build-layer.ps1        # Windows PowerShell layer build script
│   │   └── README.md              # Layer deployment and attachment instructions
│   └── events/                    # Ready-to-use Lambda Console test payloads
│       ├── post-rsvp-valid.json   # Valid RSVP event payload
│       ├── get-attendees.json     # Retrieve attendees event payload
│       └── options-cors.json      # Preflight CORS event payload
└── infrastructure/                # Setup assets, specifications & local testing
    ├── dynamodb-table.json        # DynamoDB table CLI creation schema
    └── test-local.js              # Zero-dependency local verification script
```

---

## 🔧 API Endpoints

**Base URL**: `https://{api-id}.execute-api.us-east-1.amazonaws.com/prod`

All endpoints (except `/health`) support preflight CORS options (`OPTIONS`). Requests submitting payloads must include `Content-Type: application/json`.

### Core Service & Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check & service status (no auth required) |

### Guest Attendance & RSVP

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/attendees` | Retrieve list of confirmed attendees and live aggregated statistics from DynamoDB |
| `POST` | `/attendees` | Submit new attendance RSVP with guest details, pax count, and wishes |
| `OPTIONS` | `/attendees` | Preflight CORS handshake returning allowed origins, headers, and methods |

#### Sample POST `/attendees` Request Payload:
```json
{
  "name": "David Miller & Partner",
  "relationship": "Close Friend",
  "attendanceStatus": "Attending",
  "pax": 2,
  "wishes": "Wishing you both a lifetime of love and happiness!"
}
```

#### Sample 201 Created Response:
```json
{
  "status": "success",
  "message": "Wedding Attendance RSVP successfully recorded! Thank you for your confirmation and warm blessings.",
  "ticket": {
    "guestId": "WA-9B41FA",
    "name": "David Miller & Partner",
    "attendanceStatus": "Attending",
    "pax": 2,
    "createdAt": "2026-11-05T21:48:30.000Z"
  }
}
```

---

## 🚀 Step-by-Step Deployment Guide (LKS Practice Mode)

> 💡 **Resource Naming Prefix**: All resources in this challenge use the mandatory prefix **`wa-`** (e.g. `wa-lambda`, `wa-attendance-table`, `wa-api-gateway`, `wa-amplify`).

### Step 1: Create Amazon DynamoDB Table
1. Open the **Amazon DynamoDB Console** -> click **Create table**.
2. Configure table settings:
   - **Table name**: `wa-attendance-table`
   - **Partition key**: `guestId` (Type: `String`)
   - **Table class**: `DynamoDB Standard`
   - **Capacity mode**: `On-demand` (Pay per request)
3. Click **Create table** and wait until Status is **Active**.

*(Or execute via AWS CLI)*:
```bash
aws dynamodb create-table --cli-input-json file://infrastructure/dynamodb-table.json
```

---

### Step 2: IAM Execution Role
In AWS Academy / Vocareum / LKS competition environments, select the pre-provisioned **`LabRole`**. It provides full permissions for Lambda to write logs to Amazon CloudWatch and perform `PutItem`, `Scan`, and `GetItem` on Amazon DynamoDB without needing manual policy creation.

---

### Step 3: Deploy AWS Lambda Backend & Dependency Layer
1. **(Optional Best Practice) Publish the Lambda Layer (`wa-layer`)**:
   - Run the layer build script inside [`backend/layer/`](backend/layer/) (`./build-layer.sh` or `./build-layer.ps1`).
   - In AWS Lambda Console -> **Layers** -> **Create layer** -> Name: `wa-layer` -> Upload `wa-layer.zip`.
2. **Create the Lambda Function**:
   - Open the **AWS Lambda Console** -> click **Create function**:
   - **Function name**: `wa-lambda`
   - **Runtime**: `Node.js 20.x` or `Node.js 24`
   - **Architecture**: `x86_64`
   - **Execution role**: Select **`LabRole`**.
3. **Deploy Code**:
   - In the **Code source** tab, paste [`backend/index.js`](backend/index.js) and click **Deploy**.
   - If using `wa-layer`, scroll down to **Layers** -> **Add a layer** -> Select `wa-layer` (Version 1).
4. **Configure Environment Variables**:
   - Under **Configuration** -> **Environment variables** -> click **Edit**:
   - Key: `TABLE_NAME` | Value: `wa-attendance-table`
   - Click **Save**.

---

### Step 4: Configure Amazon API Gateway (REST API)
1. Open the **Amazon API Gateway Console** -> click **Create API**.
2. Under **REST API** (not Private) -> click **Build**:
   - **API details**: Choose **New API**.
   - **API name**: `wa-api-gateway`
   - **API endpoint type**: `Regional`
   - Click **Create API**.
3. Create the `/health` Resource & Method:
   - Click **Create resource** -> **Resource name**: `health` (enable **CORS** checkbox) -> click **Create resource**.
   - With `/health` selected, click **Create method**:
     - **Method type**: `GET`
     - **Integration type**: `Lambda function`
     - Toggle **Lambda proxy integration**: **ON**
     - **Lambda function**: Select `wa-lambda`
     - Click **Create method**.
4. Create the `/attendees` Resource & Methods:
   - Select the root `/` resource -> click **Create resource** -> **Resource name**: `attendees` (enable **CORS** checkbox) -> click **Create resource**.
   - With `/attendees` selected, click **Create method**:
     - **Method type**: `GET` | **Integration type**: `Lambda function` | **Lambda proxy integration**: **ON** -> select `wa-lambda` -> click **Create method**.
   - With `/attendees` selected again, click **Create method**:
     - **Method type**: `POST` | **Integration type**: `Lambda function` | **Lambda proxy integration**: **ON** -> select `wa-lambda` -> click **Create method**.
5. Enable CORS on `/attendees`:
   - Select the `/attendees` resource -> click **Enable CORS**:
   - Check **`GET`**, **`POST`**, and **`OPTIONS`** under Gateway responses / methods.
   - **Access-Control-Allow-Origin**: `*`
   - **Access-Control-Allow-Headers**: `Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With`
   - Click **Save**.
6. Deploy the API to `prod` Stage:
   - Click **Deploy API** (top right orange button):
   - **Stage**: `*New stage*`
   - **Stage name**: `prod`
   - Click **Deploy**.
7. Copy the **Invoke URL** (e.g. `https://xxxxxx.execute-api.us-east-1.amazonaws.com/prod`).

---

### Step 5: Deploy Frontend to AWS Amplify Hosting
1. Compress all files inside `frontend/` (`index.html`, `style.css`, `app.js`, `amplify.yml`) into a `.zip` archive (e.g., `frontend.zip`).
2. Open the **AWS Amplify Console**:
   - Click **Deploy an app** -> Select **Deploy without Git provider**.
   - **App name**: `wa-amplify`
   - **Environment name**: `prod`
   - **Method**: Drag & drop `frontend.zip`.
3. Click **Save and deploy**.
4. Open the generated Amplify public URL in your browser.
5. Click the **Gear icon (Configure API)** in the top right corner of the website:
   - Paste your **API Gateway Invoke URL** from Step 4.
   - Click **Save & Connect**.
   - Notice the status dot turns green (**API Gateway Live**)!

---

## 🧪 Verification & Testing Commands

### 1. Test Health Check Endpoint
```bash
curl -i https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod/health
```
*Expected response: HTTP 200 with `{ "status": "healthy", "service": "wa-attendance-api" }`.*

### 2. Submit New Guest Attendance (POST)
```bash
curl -i -X POST https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod/attendees \
  -H "Content-Type: application/json" \
  -d '{
    "name": "David Miller & Partner",
    "relationship": "Close Friend",
    "attendanceStatus": "Attending",
    "pax": 2,
    "wishes": "Wishing you both a lifetime of love and happiness!"
  }'
```
*Expected response: HTTP 201 with generated ticket code `WA-XXXXXX`.*

### 3. Retrieve Live Attendance & Stats (GET)
```bash
curl -i https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod/attendees
```
*Expected response: HTTP 200 with `stats: { totalRsvp, totalAttending, totalPaxConfirmed }` and attendees list.*

### 4. Verify CloudWatch Logs Stream
```bash
aws logs tail /aws/lambda/wa-lambda --follow
```

---

## 🏆 Scoring Rubric (100 Points)

| No | Evaluation Criteria | Max Points |
|---|---|---|
| 1 | **DynamoDB Provisioning**: Table `wa-attendance-table` created with partition key `guestId` (String) and on-demand capacity. | 15 |
| 2 | **Lambda Logic & Resilience**: Node.js 24 handler `wa-lambda` validates fields, handles errors, and uses DynamoDB DocumentClient. | 25 |
| 3 | **CloudWatch Structured Logging**: Emits machine-readable JSON logs for all operations (`[INFO]`, `[ERROR]`, `requestId`) under `/aws/lambda/wa-lambda`. | 15 |
| 4 | **API Gateway & CORS**: REST API `wa-api-gateway` deployed to `prod` stage with `/attendees` and `/health` resources proxying to `wa-lambda` and preflight `OPTIONS` CORS enabled. | 25 |
| 5 | **Amplify Hosting Integration**: Web frontend `wa-amplify` deployed on Amplify, dynamically connects to API Gateway, and displays live passes. | 20 |
| **Total** | **LKS Cloud Computing Full Score** | **100** |
