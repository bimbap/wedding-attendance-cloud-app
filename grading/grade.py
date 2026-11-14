#!/usr/bin/env python3
"""
CLI Runner for Wedding Reception Cloud App Serverless Grading.
Mirrors aws-grading's workflow and JSON/CSV/XLSX export pipeline.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

GRADING_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GRADING_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from grading.checks import (  # noqa: E402
    AwsClient,
    CheckResult,
    EXPECTED_REGION,
    EXPECTED_SNS_EMAILS,
    TOTAL_CHECKS,
    run_all_checks,
)
from grading.exporter import (  # noqa: E402
    PASS_THRESHOLD,
    build_participant_result,
    save_csv,
    save_json,
    save_xlsx,
)


def enable_windows_ansi() -> None:
    if os.name == "nt":
        os.system("")


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


class MockAwsClient(AwsClient):
    """Deterministic offline mock for self-testing all 36 checks + XLSX export."""

    def __init__(self, region: str = EXPECTED_REGION):
        super().__init__(region=region)
        self._created_id = "WA-MOCK01"

    def call(self, args: list[str], use_region: bool = True) -> tuple[bool, Any, str]:
        svc = args[0]
        op = args[1] if len(args) > 1 else ""
        if svc == "sts" and op == "get-caller-identity":
            return True, {"Account": "123456789012", "Arn": "arn:aws:sts::123456789012:assumed-role/LabRole/grader"}, ""
        if svc == "iam" and op == "get-role":
            return True, {"Role": {"Arn": "arn:aws:iam::123456789012:role/LabRole"}}, ""
        if svc == "dynamodb" and op == "describe-table":
            return True, {
                "Table": {
                    "TableStatus": "ACTIVE",
                    "BillingModeSummary": {"BillingMode": "PAY_PER_REQUEST"},
                    "KeySchema": [{"AttributeName": "guestId", "KeyType": "HASH"}],
                    "AttributeDefinitions": [{"AttributeName": "guestId", "AttributeType": "S"}],
                    "TableClassSummary": {"TableClass": "STANDARD"},
                }
            }, ""
        if svc == "dynamodb" and op == "delete-item":
            return True, {}, ""
        if svc == "lambda" and op == "list-layer-versions":
            return True, {"LayerVersions": [{"Version": 1, "CompatibleRuntimes": ["nodejs24.x"], "CompatibleArchitectures": ["x86_64"]}]}, ""
        if svc == "lambda" and op == "get-function":
            fn = args[args.index("--function-name") + 1]
            layers = [{"Arn": "arn:aws:lambda:us-east-1:123456789012:layer:wa-layer:1"}] if fn != "wa-health-lambda" else []
            env_vars = {"TABLE_NAME": "wa-attendance-table", "TICKET_PREFIX": "WA", "TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:wa-rsvp-topic"}
            return True, {
                "Configuration": {
                    "State": "Active",
                    "Runtime": "nodejs24.x",
                    "Handler": "index.handler",
                    "Role": "arn:aws:iam::123456789012:role/LabRole",
                    "MemorySize": 128 if fn == "wa-health-lambda" else 256,
                    "Timeout": 10 if fn == "wa-health-lambda" else 15,
                    "Layers": layers,
                    "Environment": {"Variables": env_vars if fn != "wa-health-lambda" else {}},
                }
            }, ""
        if svc == "lambda" and op == "get-function-configuration":
            return True, {"Environment": {"Variables": {"TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:wa-rsvp-topic"}}}, ""
        if svc == "lambda" and op == "get-function-event-invoke-config":
            return True, {"DestinationConfig": {"OnSuccess": {"Destination": "arn:aws:sns:us-east-1:123456789012:wa-rsvp-topic"}}}, ""
        if svc == "sns" and op == "list-topics":
            return True, {"Topics": [{"TopicArn": "arn:aws:sns:us-east-1:123456789012:wa-rsvp-topic"}]}, ""
        if svc == "sns" and op == "get-topic-attributes":
            return True, {"Attributes": {"DisplayName": "RSVP"}}, ""
        if svc == "sns" and op == "list-subscriptions-by-topic":
            return True, {
                "Subscriptions": [
                    {
                        "Protocol": "email",
                        "Endpoint": "mi1122320@gmail.com",
                        "SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:wa-rsvp-topic:mock-sub-1",
                    },
                    {
                        "Protocol": "email",
                        "Endpoint": "filzahyufi16@gmail.com",
                        "SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:wa-rsvp-topic:mock-sub-2",
                    },
                ]
            }, ""
        if svc == "apigateway" and op == "get-rest-apis":
            return True, {"items": [{"id": "mockapi123", "name": "wa-api-gateway", "endpointConfiguration": {"types": ["REGIONAL"]}}]}, ""
        if svc == "apigateway" and op == "get-stages":
            return True, {"item": [{"stageName": "prod"}]}, ""
        if svc == "apigateway" and op == "get-resources":
            return True, {"items": [{"id": "res_health", "path": "/health"}, {"id": "res_att", "path": "/attendees"}]}, ""
        if svc == "apigateway" and op == "get-integration":
            res_id = args[args.index("--resource-id") + 1]
            method = args[args.index("--http-method") + 1]
            if res_id == "res_health" and method == "GET":
                return True, {"type": "AWS_PROXY", "uri": "arn:aws:apigateway:us-east-1:lambda:path/.../wa-health-lambda/invocations"}, ""
            if res_id == "res_att" and method == "GET":
                return True, {"type": "AWS_PROXY", "uri": "arn:aws:apigateway:us-east-1:lambda:path/.../wa-get-attendees-lambda/invocations"}, ""
            if res_id == "res_att" and method == "POST":
                return True, {"type": "AWS_PROXY", "uri": "arn:aws:apigateway:us-east-1:lambda:path/.../wa-post-attendee-lambda/invocations"}, ""
            if res_id == "res_att" and method == "OPTIONS":
                return True, {"type": "MOCK", "uri": ""}, ""
            return False, None, "Integration not found"
        if svc == "apigateway" and op == "get-gateway-responses":
            return True, {
                "items": [
                    {"responseType": "DEFAULT_4XX", "responseParameters": {"gatewayresponse.header.Access-Control-Allow-Origin": "'*'"}},
                    {"responseType": "DEFAULT_5XX", "responseParameters": {"gatewayresponse.header.Access-Control-Allow-Origin": "'*'"}},
                ]
            }, ""
        if svc == "amplify" and op == "list-apps":
            return True, {
                "apps": [
                    {
                        "appId": "d123mockapp",
                        "name": "wa-amplify",
                        "defaultDomain": "d123mockapp.amplifyapp.com",
                        "customRules": [{"source": "/<*>", "target": "/index.html", "status": "200"}],
                    }
                ]
            }, ""
        if svc == "amplify" and op == "list-branches":
            return True, {"branches": [{"branchName": "main", "stage": "PRODUCTION"}]}, ""
        if svc == "amplify" and op == "get-app":
            return True, {
                "app": {
                    "appId": "d123mockapp",
                    "name": "wa-amplify",
                    "defaultDomain": "d123mockapp.amplifyapp.com",
                    "customRules": [{"source": "/<*>", "target": "/index.html", "status": "200"}],
                }
            }, ""
        if svc == "logs" and op == "describe-log-groups":
            return True, {
                "logGroups": [
                    {"logGroupName": "/aws/lambda/wa-health-lambda"},
                    {"logGroupName": "/aws/lambda/wa-get-attendees-lambda"},
                    {"logGroupName": "/aws/lambda/wa-post-attendee-lambda"},
                ]
            }, ""
        if svc == "cloudwatch" and op == "get-dashboard":
            body = {
                "widgets": [
                    {
                        "type": "metric",
                        "properties": {
                            "title": "Traffic, Errors & Performance",
                            "metrics": [
                                ["AWS/Lambda", "Invocations", "FunctionName", "wa-post-attendee-lambda"],
                                [".", "Errors", ".", "."],
                                [".", "Duration", ".", "."],
                            ],
                        },
                    }
                ]
            }
            return True, {"DashboardBody": json.dumps(body)}, ""
        if svc == "cloudwatch" and op == "list-metrics":
            return True, {
                "Metrics": [
                    {"Namespace": "AWS/Lambda", "MetricName": name, "Dimensions": [{"Name": "FunctionName", "Value": "wa-post-attendee-lambda"}]}
                    for name in ("Invocations", "Errors", "Duration")
                ]
            }, ""
        return False, None, f"Unmocked AWS command: {' '.join(args)}"

    def http_request(self, url: str, method: str = "GET", body: Any = None, headers: Any = None) -> tuple[int, dict[str, str], str]:
        if url.endswith("/health"):
            return 200, {"access-control-allow-origin": "*"}, '{"status":"healthy"}'
        if method == "OPTIONS":
            return 200, {"access-control-allow-origin": "*"}, ""
        if method == "POST":
            return 201, {"access-control-allow-origin": "*"}, f'{{"ticket":{{"guestId":"{self._created_id}"}}}}'
        if method == "GET":
            return 200, {"access-control-allow-origin": "*"}, f'{{"data":[{{"guestId":"{self._created_id}"}}]}}'
        return 404, {}, "{}"


def prompt_credentials_first(env: dict[str, str], region: str) -> dict[str, str]:
    """Prompt operator for AWS credentials at the start of grading, then verify STS identity."""
    print(f"\n{CYAN}[Step 1] AWS Credentials Setup{NC}")
    print(f"{DIM}Paste AWS Academy Learner Lab keys, or press Enter to use existing AWS CLI config/profile.{NC}")

    ak = input("AWS_ACCESS_KEY_ID (Enter = pakai default/env): ").strip()
    if ak:
        sk = input("AWS_SECRET_ACCESS_KEY: ").strip()
        st = input("AWS_SESSION_TOKEN (kosongkan jika IAM user permanen): ").strip()
        env["AWS_ACCESS_KEY_ID"] = ak
        env["AWS_SECRET_ACCESS_KEY"] = sk
        if st:
            env["AWS_SESSION_TOKEN"] = st
        else:
            env.pop("AWS_SESSION_TOKEN", None)

    client = AwsClient(region=region, env=env)
    ok, data, err = client.call(["sts", "get-caller-identity"], use_region=False)
    if ok and isinstance(data, dict) and data.get("Account"):
        print(f"{GREEN}[OK]{NC} AWS Credentials aktif — Account: {BOLD}{data['Account']}{NC}")
        return env

    print(f"{RED}[ERROR]{NC} AWS Credentials tidak valid / expired: {DIM}{err}{NC}")
    retry = input("Input ulang AWS Credentials? [Y/n]: ").strip().lower()
    if retry in ("", "y", "yes"):
        return prompt_credentials_first(env, region)
    return env


class LiveConsolePrinter:
    """Streams categorized check results to stdout as each check finishes."""

    def __init__(self) -> None:
        self._last_category = ""

    def __call__(self, chk: CheckResult, idx: int) -> None:
        if chk.category != self._last_category:
            self._last_category = chk.category
            print(f"\n  {CYAN}{BOLD}── {chk.category} ──{NC}", flush=True)
        badge = f"{GREEN}PASS{NC}" if chk.passed else f"{RED}FAIL{NC}"
        counter = f"{DIM}[{idx:>2}/{TOTAL_CHECKS}]{NC}"
        print(f"    {counter} [{badge}] {chk.name:<54} {DIM}| {chk.detail}{NC}", flush=True)


def print_summary(result: dict[str, Any], json_path: Path, csv_path: Path, xlsx_path: str, xlsx_mode: str) -> None:
    verdict_color = GREEN if result["status"] == "pass" else RED
    print(f"\n{CYAN}{'-' * 68}{NC}", flush=True)
    print(f"  Participant : {result['participant']['name']} ({result['participant'].get('institution') or '-'})")
    print(f"  Account ID  : {result['participant'].get('account_id') or '-'}")
    print(f"  Score       : {BOLD}{result['score']} / {result['max_score']}{NC} ({result['percentage']}%)")
    print(f"  Verdict     : {verdict_color}{BOLD}{result['status'].upper()}{NC} (Threshold > {PASS_THRESHOLD}%)")
    print(f"  JSON Export : {json_path}")
    print(f"  CSV Export  : {csv_path}")
    print(f"  XLSX Export : {xlsx_path} [{xlsx_mode}]")
    print(f"{CYAN}{'=' * 68}{NC}\n", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AWS Serverless Grading Tool (Wedding Reception Cloud App)")
    parser.add_argument("--region", default=EXPECTED_REGION, help="Target AWS region (default: us-east-1)")
    parser.add_argument("--profile", default="", help="AWS CLI profile name")
    parser.add_argument("--name", default="", help="Participant name")
    parser.add_argument("--institution", default="", help="Participant school / institution")
    parser.add_argument("--email", default="", help="Participant email")
    parser.add_argument(
        "--sns-emails",
        default=",".join(EXPECTED_SNS_EMAILS),
        help="Comma-separated expected SNS target emails, or 'any' for any confirmed email subscription",
    )
    parser.add_argument("--results-dir", default=str(GRADING_DIR / "results"), help="Output folder for JSON/CSV/XLSX")
    parser.add_argument("--append", action="store_true", help="Append to existing results.json for multi-participant ranking")
    parser.add_argument("--non-interactive", action="store_true", help="Skip interactive prompts")
    parser.add_argument("--mock-test", action="store_true", help="Run offline with synthetic AWS responses")
    return parser.parse_args()


def _resolve_sns_targets(raw_value: str) -> tuple[str, ...]:
    cleaned = raw_value.strip()
    if not cleaned or cleaned.lower() == "any":
        return ()
    return tuple(item.strip() for item in cleaned.split(",") if item.strip())


def main() -> int:
    enable_windows_ansi()
    args = parse_args()
    interactive = not args.non_interactive and not args.mock_test

    print(f"{CYAN}{'=' * 68}{NC}")
    print(f"{BOLD}  AWS SERVERLESS GRADING — WEDDING RECEPTION CLOUD APP{NC}")
    print(f"{CYAN}{'=' * 68}{NC}")

    env = os.environ.copy()
    if args.profile:
        env["AWS_PROFILE"] = args.profile

    name = args.name
    inst = args.institution
    email = args.email
    append_mode = args.append

    if interactive:
        env = prompt_credentials_first(env, args.region)
        print(f"\n{CYAN}[Step 2] Data Peserta{NC}")
        if not name:
            name = input("Nama Peserta (default: Participant): ").strip() or "Participant"
        if not inst:
            inst = input("Instansi / Sekolah (opsional): ").strip()
        if not email:
            email = input("Email (opsional): ").strip()
    else:
        name = name or ("Mock Participant" if args.mock_test else "Participant")

    sns_targets = _resolve_sns_targets(args.sns_emails)
    aws = MockAwsClient(region=args.region) if args.mock_test else AwsClient(region=args.region, env=env)
    print(f"\n{YELLOW}Running {TOTAL_CHECKS} automated checks in region {args.region} (live stream)...{NC}\n", flush=True)
    print(f"{CYAN}{'=' * 68}{NC}", flush=True)
    print(f"{BOLD}  LIVE GRADING — WEDDING RECEPTION SERVERLESS ARCHITECTURE{NC}", flush=True)
    print(f"{CYAN}{'=' * 68}{NC}", flush=True)
    ctx = run_all_checks(aws, region=args.region, on_check=LiveConsolePrinter(), expected_sns_emails=sns_targets)

    participant = {"name": name, "institution": inst, "email": email}
    result = build_participant_result(ctx, participant)

    results_dir = Path(args.results_dir)
    json_path = results_dir / "results.json"
    csv_path = results_dir / "results.csv"
    xlsx_path = results_dir / "results.xlsx"

    payload = save_json(result, json_path, append=append_mode)
    save_csv(payload, csv_path)
    saved_xlsx, xlsx_mode = save_xlsx(payload, json_path, xlsx_path)

    print_summary(result, json_path, csv_path, saved_xlsx, xlsx_mode)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
