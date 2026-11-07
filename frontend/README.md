# Wedding Attendance — Frontend Application (`wa-amplify`)

This directory contains the responsive web application for the Wedding Attendance & RSVP Guestbook.

---

## 🚀 AWS Amplify Hosting Deployment

Deploy this frontend to **AWS Amplify Hosting** using manual archive deployment:

1. **Package Assets**:
   Compress the contents of this directory (`index.html`, `style.css`, `app.js`, `amplify.yml`) into a `.zip` archive (e.g., `frontend.zip`).
   > *Note: Ensure the files reside at the root of the archive, not nested inside a subfolder.*

2. **Deploy to Amplify**:
   - In AWS Console, open **AWS Amplify**.
   - Choose **Deploy an app** -> **Deploy without Git provider**.
   - **App name**: `wa-amplify`
   - **Branch / Environment**: `main`
   - Upload `frontend.zip` and click **Save and deploy**.

3. **Connect API Endpoint**:
   - Open your public Amplify application URL.
   - Click the gear icon (**Configure API**) in the header bar.
   - Paste your Amazon API Gateway stage Invoke URL (e.g., `https://{api-id}.execute-api.us-east-1.amazonaws.com/prod`).
   - The indicator will turn green (`Connected: AWS Cloud API`), enabling live RSVP operations.

