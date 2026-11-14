# Automated Grading — Wedding Reception Serverless Cloud App

Standalone Windows `.bat` + Python grading suite aligned with [`aws-grading`](https://github.com/bimbap/aws-grading) conventions and the **Serverless Cloud Architecture** practice module.

---

## 🛠️ Prerequisites & Installation Tutorial

Before running the grader, make sure **Python 3.10+**, **AWS CLI v2**, and **`jq`** are installed and available in your terminal `PATH`.

### 1. Install AWS CLI v2

**Option A — Using `winget` (PowerShell / CMD):**
```powershell
winget install -e --id Amazon.AWSCLI
```

**Option B — Official Windows MSI Installer:**
1. Download the 64-bit installer: <https://awscli.amazonaws.com/AWSCLIV2.msi>
2. Run the `.msi` installer and follow the setup wizard.

**Option C — macOS / Linux:**
```bash
# macOS (Homebrew)
brew install awscli

# Ubuntu / Debian
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install
```

Verify installation (restart your terminal first if needed):
```powershell
aws --version
```

---

### 2. Install `jq` (JSON Processor)

**Option A — Using `winget` (Windows PowerShell / CMD):**
```powershell
winget install -e --id jqlang.jq
```

**Option B — Using Chocolatey or Scoop (Windows):**
```powershell
# Chocolatey
choco install jq

# Scoop
scoop install jq
```

**Option C — macOS / Linux / Git Bash:**
```bash
# macOS (Homebrew)
brew install jq

# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y jq
```

Verify installation (restart your terminal if needed):
```powershell
jq --version
```

> **Note:** On **Windows**, you can also use the built-in **AWS CLI** + `jq` inside **Git Bash**, **PowerShell**, or **Command Prompt (CMD)** once both binaries are on `PATH`.

---

## 🚀 Quick Start (Windows)

Double-click [`../grade.bat`](../grade.bat) in Windows Explorer, or run from PowerShell / CMD / Git Bash:

```powershell
.\grade.bat
```

1. **Step 1 — AWS Credentials:** Paste `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` (AWS Academy Learner Lab), or press **Enter** to use your active AWS CLI profile/environment.
2. **Step 2 — Participant Info:** Enter participant name, institution (optional), and email (optional).
3. **Live Grading & Export:** Each of the **37 checks** streams live to the console as it finishes. Running the grader again overwrites the previous files in `grading/results/`.

---

## 📊 Export Output (`grading/results/`)

- `results.json` — Structured result compatible with `aws-grading/grading/export/convert_csv_to_xlsx.py`
- `results.csv` — Flattened CSV report (with formula-injection sanitization)
- `results.xlsx` — Styled Excel report. Uses `aws-grading`'s `openpyxl` formatter when `openpyxl` is installed, with automatic built-in OOXML `.xlsx` fallback.

**Passing Criterion:** **Score > 70%** (minimum **26 / 37** checks passed).

---

## 📋 Grading Rubric (37 Checks)

| Category | Checks | Key Verified Specifications |
|---|---|---|
| **IAM** | 2 | Active STS Caller Identity, `LabRole` exists |
| **DynamoDB** | 4 | `wa-attendance-table` (`ACTIVE`), `PAY_PER_REQUEST`, `guestId` (`S`) without sort key, `STANDARD` class |
| **Lambda Layer** | 2 | `wa-layer` exists, Node.js `20.x–26.x` (`nodejs24.x`) & `x86_64` |
| **Lambda** | 11 | `wa-health-lambda`, `wa-get-attendees-lambda`, `wa-post-attendee-lambda` (`index.handler`, `x86_64`, `LabRole`, memory/timeout, `wa-layer`, `TABLE_NAME`, `TICKET_PREFIX`) |
| **SNS** | 3 | `wa-rsvp-topic` (`RSVP`), confirmed email subscriptions targeting `mi1122320@gmail.com` & `filzahyufi16@gmail.com`, `TOPIC_ARN` or async EventInvokeDestination |
| **API Gateway** | 5 | `wa-api-gateway` (`REGIONAL`, `ipv4`, `SecurityPolicy_TLS13_1_3_2025_09`), `prod` stage, `AWS_PROXY` routes (`/health`, `/attendees`), `OPTIONS` CORS mock, `DEFAULT_4XX` & `DEFAULT_5XX` CORS |
| **Amplify** | 3 | `wa-amplify`, `main` branch, SPA `200` rewrite rule → `/index.html` |
| **E2E API** | 4 | Live `GET /health` (`200`), `OPTIONS /attendees` (`200` + CORS), `POST /attendees` (`201` + `guestId`), `GET /attendees` persistence + auto-cleanup |
| **CloudWatch** | 3 | `/aws/lambda/wa-*` log groups, `wa-cloudwatch` dashboard (`Traffic, Errors & Performance`), configured & live `AWS/Lambda` metrics (`Invocations`, `Errors`, `Duration`) |
