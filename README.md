# Wedding Attendance & RSVP Guestbook — Serverless Multi-Tier Application

**LKS Cloud Computing · Level: Intermediate to Advanced · Scenario: AWS Amplify, API Gateway, Lambda, CloudWatch & DynamoDB**

---

## 📋 Overview

**Wedding Attendance & RSVP Guestbook** is a production-grade, multi-tier serverless web application designed for modern wedding events and receptions. It replaces paper-based guestbooks with an automated digital RSVP portal, live guest attendance statistics, reserved seating calculation, and a live digital wishes wall.

This application demonstrates the complete **Serverless Application Pattern on AWS**:
1. **Frontend Tier**: Single Page Application (SPA) deployed globally via **AWS Amplify Hosting**.
2. **API Management Tier**: Fully managed HTTPS REST API with Lambda Proxy integration and CORS preflight handling on **Amazon API Gateway**.
3. **Compute Tier**: Stateless event-driven microservice running on **AWS Lambda** (Node.js 20.x / 24.x ESM).
4. **Database Tier**: Auto-scaling NoSQL key-value store on **Amazon DynamoDB**.
5. **Observability Tier**: Structured JSON application logging in **Amazon CloudWatch Logs**.

---

## 🏗️ Architecture

<p align="center">
  <img src="architecture/Wedding%20Attendance%20Architecture.png" alt="Wedding Attendance Architecture Diagram" width="100%">
</p>

---

## 📁 Project Structure

```text
pr-wedding-attendance-app/
├── README.md                      # Project brief and deployment instructions
├── architecture/                  # Visual architecture blueprint
│   ├── Wedding Attendance Architecture.png
│   └── wedding-attendance.drawio
├── frontend/                      # Web application ready for AWS Amplify Hosting
│   ├── README.md                  # Amplify deployment instructions
│   ├── index.html                 # Wedding RSVP & digital guestbook
│   ├── style.css                  # Responsive UI styling
│   ├── app.js                     # Dynamic controller & API Gateway integration
│   └── amplify.yml                # AWS Amplify Hosting build specification
├── backend/                       # Serverless Lambda function
│   ├── README.md                  # Lambda runtime & environment configuration instructions
│   ├── .env.example               # Environment variable reference template
│   ├── index.js                   # Node.js ESM handler (DynamoDB DocumentClient)
│   ├── package.json               # Backend dependencies manifest
│   └── layer/                     # Lambda Layer dependencies (@aws-sdk/client-dynamodb)
│       ├── package.json
│       ├── build-layer.sh
│       ├── build-layer.ps1
│       └── README.md
└── infrastructure/                # Provisioning specifications
    └── dynamodb-table.json        # DynamoDB table schema
```

---

## 🔧 API Endpoints

**Base URL**: `https://{api-id}.execute-api.us-east-1.amazonaws.com/prod`

All endpoints (except `/health`) support preflight CORS options (`OPTIONS`).

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check & service status |
| `GET` | `/attendees` | Retrieve list of confirmed attendees and live statistics |
| `POST` | `/attendees` | Submit new attendance RSVP with guest details |
| `OPTIONS` | `/attendees` | Preflight CORS handshake |

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

---

## 🚀 Deployment Guide

> 💡 **Resource Naming Prefix**: All resources must use the prefix **`wa-`** (e.g. `wa-attendance-table`, `wa-lambda`, `wa-api-gateway`, `wa-amplify`). Use the pre-provisioned **`LabRole`** for execution permissions.

### 1. Amazon DynamoDB Table
- **Table Name**: `wa-attendance-table`
- **Partition Key**: `guestId` (String)
- **Table Class**: DynamoDB Standard
- **Capacity Mode**: On-demand (`PAY_PER_REQUEST`)

### 2. Lambda Layer (`wa-layer`)
1. Run `./build-layer.sh` (or `./build-layer.ps1`) inside [`backend/layer/`](backend/layer/) to generate `wa-layer.zip`.
2. Publish as an AWS Lambda Layer named `wa-layer` for Node.js runtimes.

### 3. AWS Lambda Backend (`wa-lambda`)
1. Create function `wa-lambda` with runtime `Node.js 20.x` or `Node.js 24.x` (x86_64) and execution role `LabRole`.
2. Deploy the code from [`backend/index.js`](backend/index.js) and attach `wa-layer`.
3. Configure the required **Environment variables** under **Configuration -> Environment variables** (see [`backend/README.md`](backend/README.md) and [`backend/index.js`](backend/index.js)).

### 4. Amazon API Gateway (`wa-api-gateway`)
1. Create a **REST API** (Regional) named `wa-api-gateway`.
2. Create resources:
   - `/health` with `GET` method (Lambda Proxy Integration to `wa-lambda`).
   - `/attendees` with `GET` and `POST` methods (Lambda Proxy Integration to `wa-lambda`).
3. Enable CORS on `/attendees` (`GET`, `POST`, `OPTIONS`).
4. Deploy API to a new stage named **`prod`** and copy the Invoke URL.

### 5. AWS Amplify Hosting (`wa-amplify`)
Deploy the responsive frontend web application to AWS Amplify Hosting via archive upload (`wa-amplify`).  
See [`frontend/README.md`](frontend/README.md) for step-by-step deployment and API connection instructions.
