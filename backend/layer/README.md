# AWS Lambda Layer — `wa-layer`

A reusable dependency layer for the **Wedding Attendance Application** (`wa-lambda`).

---

## ⚡ Why Use a Lambda Layer?

1. **Lightweight Handler (<10 KB)**: The function code [`backend/index.js`](../index.js) contains zero bundled `node_modules`, allowing instant viewing and editing directly in the AWS Management Console Code Editor.
2. **Standard Node.js Search Path**: AWS Lambda automatically mounts layers to `/opt`. Placing packages in `nodejs/node_modules/` allows standard ESM `import { DynamoDBClient } from "@aws-sdk/client-dynamodb"` to resolve automatically without any bundler.
3. **Reusability**: One layer can be shared across multiple Lambda functions across stages (`dev`, `prod`).

---

## 📁 Layer Folder Structure

AWS Lambda strictly requires Node.js layers to follow this exact folder layout inside the `.zip`:

```text
wa-layer.zip
└── nodejs/
    ├── package.json
    └── node_modules/
        ├── @aws-sdk/client-dynamodb/
        └── @aws-sdk/lib-dynamodb/
```

---

## 🚀 Building & Publishing the Layer

### Step 1: Build the Zip Archive

```bash
# On Linux / macOS:
cd backend/layer
chmod +x build-layer.sh
./build-layer.sh

# On Windows PowerShell:
cd backend/layer
./build-layer.ps1
```

---

### Step 2: Publish Layer to AWS

#### Via AWS Console:
1. Open **AWS Lambda Console** -> Click **Layers** (left sidebar) -> Click **Create layer**.
2. **Name**: `wa-layer`
3. **Upload**: Select `wa-layer.zip`.
4. **Compatible runtimes**: `Node.js 20.x`, `Node.js 24.x`.
5. Click **Create**.

#### Via AWS CLI:
```bash
aws lambda publish-layer-version \
  --layer-name wa-layer \
  --description "DynamoDB DocumentClient dependencies for Wedding Attendance" \
  --zip-file fileb://wa-layer.zip \
  --compatible-runtimes nodejs20.x nodejs22.x nodejs24.x
```

---

### Step 3: Attach Layer to `wa-lambda`

1. Open your Lambda function `wa-lambda` in the AWS Console.
2. Scroll to the bottom to the **Layers** section -> Click **Add a layer**.
3. Choose **Custom layers** -> Select `wa-layer` -> Version `1`.
4. Click **Add**.

