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
wedding-reception-cloud-app/
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
└── backend/                       # Serverless Lambda function
    ├── README.md                  # Lambda runtime & environment configuration instructions
    ├── .env.example               # Environment variable reference template
    ├── index.js                   # Node.js ESM handler (DynamoDB DocumentClient)
    ├── package.json               # Backend dependencies manifest
    └── layer/                     # Lambda Layer dependencies (@aws-sdk/client-dynamodb)
        ├── package.json
        ├── build-layer.sh
        ├── build-layer.ps1
        └── README.md
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

## 📌 Competition Instructions

This repository provides the starter source code for the **Wedding Attendance & RSVP Portal** competition scenario.


Refer to component-level directories for tier-specific packaging and configuration notes:
- **Frontend Application & Hosting**: [`frontend/README.md`](frontend/README.md)
- **Backend Lambda Function**: [`backend/README.md`](backend/README.md)
- **Lambda Layer Dependencies**: [`backend/layer/README.md`](backend/layer/README.md)

---

## 🧪 Testing & Verification

Once your API Gateway stage (`prod`) is deployed, verify your serverless backend endpoints using the following commands:

### 1. Health & Configuration Check
```bash
curl -s https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/health
```

### 2. Submit Attendance RSVP
```bash
curl -s -X POST https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/attendees \
  -H "Content-Type: application/json" \
  -d '{
    "name": "David Miller & Partner",
    "relationship": "Close Friend",
    "attendanceStatus": "Attending",
    "pax": 2,
    "wishes": "Wishing you both a wonderful journey ahead!"
  }'
```

### 3. Retrieve Guest List & Live Statistics
```bash
curl -s https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/attendees
```

### 4. CORS Preflight Handshake
```bash
curl -s -I -X OPTIONS https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/attendees \
  -H "Origin: https://wa-amplify.amplifyapp.com" \
  -H "Access-Control-Request-Method: POST"
```
