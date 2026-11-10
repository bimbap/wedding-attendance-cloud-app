# Wedding Attendance & RSVP Guestbook — Serverless Multi-Tier Application

## 📋 Overview

**Wedding Attendance & RSVP Guestbook** is a production-grade, multi-tier serverless web application designed for modern wedding events and receptions. It replaces paper-based guestbooks with an automated digital RSVP portal, live guest attendance statistics, reserved seating calculation, and a live digital wishes wall.

This application demonstrates the complete **Serverless Application Pattern on AWS**:
1. **Frontend Tier**: Single Page Application (SPA) deployed globally via **AWS Amplify Hosting**.
2. **API Management Tier**: Fully managed HTTPS REST API with Lambda Proxy integration and CORS preflight handling on **Amazon API Gateway**.
3. **Compute Tier**: Decoupled serverless microservices running on **AWS Lambda** (`wa-health-lambda`, `wa-get-attendees-lambda`, `wa-post-attendee-lambda`).
4. **Notification Tier**: Event-driven real-time alerts via **Amazon SNS** (`wa-rsvp-topic`) notifying organizers on successful RSVP.
5. **Database Tier**: Auto-scaling NoSQL key-value store on **Amazon DynamoDB** (`wa-attendance-table`).
6. **Observability Tier**: Structured JSON application logging in **Amazon CloudWatch Logs**.

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
└── backend/                       # Serverless Lambda microservices
    ├── README.md                  # Microservices architecture & environment configuration
    ├── .env.example               # Environment variable reference
    ├── package.json               # Backend dependencies manifest
    ├── layer/                     # Shared Lambda Layer dependencies (DynamoDB & SNS SDKs)
    │   ├── README.md              # Layer manual packaging instructions
    │   └── package.json           # Layer dependency manifest
    ├── health/                    # wa-health-lambda
    │   └── index.js               # Health check probe
    ├── get-attendees/             # wa-get-attendees-lambda
    │   └── index.js               # Attendees reader & statistics computer
    └── post-attendee/             # wa-post-attendee-lambda
        └── index.js               # RSVP recorder & SNS event notification trigger
```

---

## 🔧 API Endpoints

**Base URL**: `https://{api-id}.execute-api.us-east-1.amazonaws.com/prod`

All endpoints (except `/health`) support preflight CORS options (`OPTIONS`).

| Method | Endpoint | CORS | Target Function / Integration | Description |
|---|---|---|---|---|
| `GET` | `/health` | `No` | `wa-health-lambda` | Health check & service status (Direct/CLI) |
| `GET` | `/attendees` | `Yes` | `wa-get-attendees-lambda` | Retrieve list of confirmed attendees and live statistics |
| `POST` | `/attendees` | `Yes` | `wa-post-attendee-lambda` | Submit new attendance RSVP & trigger SNS email notification |
| `OPTIONS` | `/attendees` | `Yes` | *API Gateway Mock* | Preflight CORS handshake |

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

## 📌 Instructions

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
