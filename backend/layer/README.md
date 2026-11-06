# AWS Lambda Layer — `wa-layer`

Dependency layer package (`@aws-sdk/client-dynamodb` and `@aws-sdk/lib-dynamodb`) for `wa-lambda`.

---

## 📁 Required Archive Structure

```text
wa-layer.zip
└── nodejs/
    ├── package.json
    └── node_modules/
        ├── @aws-sdk/client-dynamodb/
        └── @aws-sdk/lib-dynamodb/
```

---

## 🚀 Build Layer Archive

**Linux / macOS:**
```bash
cd backend/layer
chmod +x build-layer.sh
./build-layer.sh
```

**Windows PowerShell:**
```powershell
cd backend/layer
./build-layer.ps1
```

Upload the generated `wa-layer.zip` to **AWS Lambda -> Layers** (`wa-layer`) and attach it to `wa-lambda`.
