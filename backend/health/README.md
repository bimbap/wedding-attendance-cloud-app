# Health Probe Microservice (`wa-health-lambda`)

A lightweight, zero-dependency health check probe executed on API Gateway `GET /health` requests to verify backend availability and runtime diagnostics.

---

## ⚙️ Function Configuration

| Parameter | Recommended Specification | Notes |
|---|---|---|
| **Function Name** | `wa-health-lambda` | Standard competition resource naming |
| **Runtime** | `Node.js 20.x` or `Node.js 24.x` | Native ESM module |
| **Handler** | `index.handler` | Points to [`index.js`](index.js) |
| **Architecture** | `x86_64` | Standard x86 architecture |
| **Memory Allocation** | `128 MB` | Optimal memory footprint |
| **Timeout** | `5 seconds` | Lightweight in-memory execution (< 50 ms) |
| **Execution Role** | `LabRole` | Pre-configured AWS Academy role |
| **Attached Layer** | *None* | Zero external dependencies (uses native Node.js) |
| **Environment Variables** | *None* | No custom variables needed |

---

## 🌐 API Gateway Integration

- **Resource**: `/health`
- **Method**: `GET`
- **Integration Type**: `Lambda Proxy Integration` (`AWS_PROXY`)
- **CORS Preflight**: Handled via `OPTIONS` Mock Integration (or direct CLI access)

---

## 📤 Sample Response (`200 OK`)

```json
{
  "status": "healthy",
  "service": "wa-health-lambda",
  "timestamp": "2026-11-10T11:00:00.000Z"
}
```

