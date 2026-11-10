# AWS Lambda Layer — `wa-layer`

This directory provides the dependency manifest (`package.json`) required to package the shared AWS Lambda Layer (`wa-layer`) for `wa-get-attendees-lambda` and `wa-post-attendee-lambda`.

---

## 📁 Required Layer Structure

AWS Lambda requires all Node.js layer dependencies to reside under the root folder `nodejs/`:

```text
wa-layer.zip
└── nodejs/
    ├── package.json
    └── node_modules/
        ├── @aws-sdk/client-dynamodb/
        ├── @aws-sdk/lib-dynamodb/
        └── @aws-sdk/client-sns/
```

---

## 📦 Packaging Instructions

Participants must manually construct the layer archive according to AWS Lambda runtime specifications:

1. **Create the `nodejs/` directory**:
   ```bash
   mkdir nodejs
   ```

2. **Copy manifest and install production dependencies**:
   ```bash
   cp package.json nodejs/
   cd nodejs
   npm install --omit=dev
   cd ..
   ```

3. **Archive into `wa-layer.zip`**:
   - Ensure `nodejs/` is located at the root of the archive.
   - **Linux / macOS**:
     ```bash
     zip -r wa-layer.zip nodejs/
     ```
   - **Windows PowerShell**:
     ```powershell
     Compress-Archive -Path nodejs -DestinationPath wa-layer.zip
     ```

4. **Publish & Attach to Lambda**:
   - In AWS Lambda Console, navigate to **Layers** -> **Create layer**.
   - **Name**: `wa-layer`
   - **Compatible runtimes**: `Node.js 20.x`, `Node.js 24.x`
   - Upload `wa-layer.zip` and attach the created layer version to `wa-get-attendees-lambda` and `wa-post-attendee-lambda`.
   *(Note: `wa-health-lambda` does not require this layer since it has zero external dependencies).*
