"""AWS Serverless infrastructure and E2E checks for Wedding Reception Cloud App."""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable


SUPPORTED_NODE_RUNTIMES = {"nodejs20.x", "nodejs22.x", "nodejs24.x", "nodejs26.x"}
EXPECTED_REGION = "us-east-1"
EXPECTED_TABLE = "wa-attendance-table"
EXPECTED_LAYER = "wa-layer"
EXPECTED_TOPIC = "wa-rsvp-topic"
EXPECTED_SNS_EMAILS = ("mi1122320@gmail.com", "filzahyufi16@gmail.com")
EXPECTED_API_NAME = "wa-api-gateway"
EXPECTED_STAGE = "prod"
EXPECTED_AMPLIFY_APP = "wa-amplify"
EXPECTED_DASHBOARD = "wa-cloudwatch"
EXPECTED_CW_METRICS = ("Invocations", "Errors", "Duration")
TOTAL_CHECKS = 37
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EXPECTED_LAMBDAS = {
    "wa-health-lambda": {"min_mem": 128, "min_timeout": 5, "needs_layer": False, "env_keys": []},
    "wa-get-attendees-lambda": {"min_mem": 128, "min_timeout": 10, "needs_layer": True, "env_keys": ["TABLE_NAME"]},
    "wa-post-attendee-lambda": {
        "min_mem": 128,
        "min_timeout": 10,
        "needs_layer": True,
        "env_keys": ["TABLE_NAME", "TICKET_PREFIX"],
    },
}


@dataclass
class CheckResult:
    """Single grading check outcome."""

    category: str
    name: str
    passed: bool
    detail: str
    region: str = EXPECTED_REGION
    points: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "points": self.points if self.passed else 0,
            "status": "pass" if self.passed else "fail",
            "detail": self.detail,
            "passed": self.passed,
            "region": self.region,
        }


@dataclass
class GradingContext:
    """Shared state discovered across grading checks."""

    region: str = EXPECTED_REGION
    account_id: str = ""
    topic_arn: str = ""
    api_id: str = ""
    invoke_url: str = ""
    checks: list[CheckResult] = field(default_factory=list)
    on_check: Callable[[CheckResult, int], None] | None = None

    def add(self, category: str, name: str, passed: bool, detail: str) -> None:
        result = CheckResult(category, name, passed, detail, self.region)
        self.checks.append(result)
        if self.on_check is not None:
            self.on_check(result, len(self.checks))


class AwsClient:
    """Executes AWS CLI commands and HTTP probes."""

    def __init__(self, region: str = EXPECTED_REGION, env: dict[str, str] | None = None):
        self.region = region
        self.env = env if env is not None else os.environ.copy()

    def call(self, args: list[str], use_region: bool = True) -> tuple[bool, Any, str]:
        cmd = ["aws"]
        if use_region:
            cmd.extend(["--region", self.region])
        cmd.extend(args)
        cmd.extend(["--output", "json"])
        try:
            proc = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=25,
            )
        except FileNotFoundError:
            return False, None, "AWS CLI ('aws') not found in PATH"
        except subprocess.TimeoutExpired:
            return False, None, f"Timed out running: {' '.join(args[:3])}"

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "Unknown AWS CLI error").strip()
            return False, None, err.splitlines()[-1] if err else "AWS CLI error"

        raw = proc.stdout.strip()
        if not raw:
            return True, {}, ""
        try:
            return True, json.loads(raw), ""
        except json.JSONDecodeError:
            return True, raw, ""

    def http_request(
        self,
        url: str,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], str]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req_headers = dict(headers or {})
        if body is not None:
            req_headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                return resp.status, resp_headers, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            resp_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            payload = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            return exc.code, resp_headers, payload
        except Exception as exc:
            return 0, {}, str(exc)


def check_iam(aws: AwsClient, ctx: GradingContext) -> None:
    ok, data, err = aws.call(["sts", "get-caller-identity"], use_region=False)
    if ok and isinstance(data, dict) and data.get("Account"):
        ctx.account_id = str(data["Account"])
        arn_tail = str(data.get("Arn", "")).split(":")[-1]
        ctx.add(
            "IAM",
            "Caller Identity Valid",
            True,
            f"STS identity verified on account {ctx.account_id} ({arn_tail})",
        )
    else:
        ctx.add("IAM", "Caller Identity Valid", False, err or "Failed to verify STS caller identity")

    ok_role, role_data, role_err = aws.call(["iam", "get-role", "--role-name", "LabRole"], use_region=False)
    role_arn = (role_data or {}).get("Role", {}).get("Arn", "") if isinstance(role_data, dict) else ""
    ctx.add(
        "IAM",
        "LabRole IAM Role Exists",
        bool(ok_role and role_arn),
        f"Execution role 'LabRole' verified ({role_arn})" if ok_role and role_arn else (role_err or "IAM role 'LabRole' not found"),
    )


def check_dynamodb(aws: AwsClient, ctx: GradingContext) -> None:
    ok, data, err = aws.call(["dynamodb", "describe-table", "--table-name", EXPECTED_TABLE])
    if not ok or not isinstance(data, dict) or "Table" not in data:
        msg = err or f"DynamoDB table '{EXPECTED_TABLE}' not found"
        ctx.add("DynamoDB", f"Table Exists ({EXPECTED_TABLE})", False, msg)
        ctx.add("DynamoDB", "Billing Mode (PAY_PER_REQUEST)", False, "Skipped: DynamoDB table not found")
        ctx.add("DynamoDB", "Primary Key (guestId String, No Sort Key)", False, "Skipped: DynamoDB table not found")
        ctx.add("DynamoDB", "Table Class (STANDARD)", False, "Skipped: DynamoDB table not found")
        return

    tbl = data["Table"]
    status = tbl.get("TableStatus", "UNKNOWN")
    ctx.add(
        "DynamoDB",
        f"Table Exists ({EXPECTED_TABLE})",
        status == "ACTIVE",
        f"Table '{EXPECTED_TABLE}' is ACTIVE" if status == "ACTIVE" else f"Table status is {status}, expected ACTIVE",
    )

    billing = (tbl.get("BillingModeSummary") or {}).get("BillingMode", "PROVISIONED")
    ctx.add(
        "DynamoDB",
        "Billing Mode (PAY_PER_REQUEST)",
        billing == "PAY_PER_REQUEST",
        "Billing mode is PAY_PER_REQUEST (On-Demand)"
        if billing == "PAY_PER_REQUEST"
        else f"Billing mode is {billing}, expected PAY_PER_REQUEST",
    )

    keys = tbl.get("KeySchema") or []
    attrs = {a["AttributeName"]: a["AttributeType"] for a in (tbl.get("AttributeDefinitions") or [])}
    key_ok = (
        len(keys) == 1
        and keys[0].get("AttributeName") == "guestId"
        and keys[0].get("KeyType") == "HASH"
        and attrs.get("guestId") == "S"
    )
    key_desc = ", ".join(f"{k.get('AttributeName')}:{k.get('KeyType')}" for k in keys)
    ctx.add(
        "DynamoDB",
        "Primary Key (guestId String, No Sort Key)",
        key_ok,
        "Partition key is 'guestId' (String) with no sort key"
        if key_ok
        else f"Found key schema [{key_desc}] (guestId type: {attrs.get('guestId', 'N/A')}), expected 'guestId' (S)",
    )

    tbl_class = (tbl.get("TableClassSummary") or {}).get("TableClass", "STANDARD")
    ctx.add(
        "DynamoDB",
        "Table Class (STANDARD)",
        tbl_class == "STANDARD",
        "Table class is STANDARD" if tbl_class == "STANDARD" else f"Table class is {tbl_class}, expected STANDARD",
    )


def check_lambda_layer(aws: AwsClient, ctx: GradingContext) -> None:
    ok, data, err = aws.call(["lambda", "list-layer-versions", "--layer-name", EXPECTED_LAYER])
    versions = (data or {}).get("LayerVersions", []) if ok and isinstance(data, dict) else []
    if not versions:
        ctx.add("Lambda Layer", f"Layer Exists ({EXPECTED_LAYER})", False, err or f"Lambda layer '{EXPECTED_LAYER}' not found")
        ctx.add("Lambda Layer", "Layer Runtime & Arch (Node.js 24.x, x86_64)", False, "Skipped: Lambda layer not found")
        return

    latest = max(versions, key=lambda v: v.get("Version", 0))
    ver_num = latest.get("Version", 1)
    ctx.add(
        "Lambda Layer",
        f"Layer Exists ({EXPECTED_LAYER})",
        True,
        f"Layer '{EXPECTED_LAYER}' active (Latest version: v{ver_num})",
    )

    runtimes = sorted(set(latest.get("CompatibleRuntimes") or []))
    arches = sorted(set(latest.get("CompatibleArchitectures") or []))
    rt_ok = bool(set(runtimes) & SUPPORTED_NODE_RUNTIMES)
    arch_ok = not arches or ("x86_64" in arches)
    rt_disp = ", ".join(runtimes) if runtimes else "unspecified"
    arch_disp = ", ".join(arches) if arches else "x86_64 (default)"
    ctx.add(
        "Lambda Layer",
        "Layer Runtime & Arch (Node.js 24.x, x86_64)",
        rt_ok and arch_ok,
        f"Compatible runtime {rt_disp} on {arch_disp}"
        if (rt_ok and arch_ok)
        else f"Runtime={rt_disp}, Arch={arch_disp}; expected Node.js 20.x-26.x on x86_64",
    )


def _check_single_lambda(aws: AwsClient, ctx: GradingContext, fn_name: str, spec: dict[str, Any]) -> None:
    ok, data, err = aws.call(["lambda", "get-function", "--function-name", fn_name])
    if not ok or not isinstance(data, dict) or "Configuration" not in data:
        msg = err or f"Lambda function '{fn_name}' not found"
        ctx.add("Lambda", f"Function Exists ({fn_name})", False, msg)
        ctx.add("Lambda", f"Runtime, Handler, Arch & Role ({fn_name})", False, "Skipped: function not found")
        ctx.add("Lambda", f"Memory, Timeout & Layer ({fn_name})", False, "Skipped: function not found")
        if spec["env_keys"]:
            ctx.add("Lambda", f"Environment Variables ({fn_name})", False, "Skipped: function not found")
        return

    cfg = data["Configuration"]
    state = cfg.get("State", "Active")
    ctx.add(
        "Lambda",
        f"Function Exists ({fn_name})",
        state == "Active",
        f"Function '{fn_name}' is Active" if state == "Active" else f"Function state is {state}, expected Active",
    )

    runtime = cfg.get("Runtime", "")
    handler = cfg.get("Handler", "")
    role = cfg.get("Role", "")
    role_name = role.split("/")[-1] if role else "none"
    archs = cfg.get("Architectures") or ["x86_64"]
    rhr_ok = (
        runtime in SUPPORTED_NODE_RUNTIMES
        and handler == "index.handler"
        and "x86_64" in archs
        and role.endswith("LabRole")
    )
    ctx.add(
        "Lambda",
        f"Runtime, Handler, Arch & Role ({fn_name})",
        rhr_ok,
        f"Runtime {runtime}, handler {handler} ({', '.join(archs)}) via {role_name}"
        if rhr_ok
        else f"Found {runtime or 'none'} / {handler or 'none'} ({', '.join(archs)}) via {role_name}; expected Node.js 20.x-26.x, index.handler, x86_64, LabRole",
    )

    mem = int(cfg.get("MemorySize") or 0)
    timeout = int(cfg.get("Timeout") or 0)
    layers = [l.get("Arn", "") for l in (cfg.get("Layers") or [])]
    layer_ok = (not spec["needs_layer"]) or any(f":layer:{EXPECTED_LAYER}:" in arn for arn in layers)
    mtl_ok = mem >= spec["min_mem"] and timeout >= spec["min_timeout"] and layer_ok
    layer_note = (
        "no layer required"
        if not spec["needs_layer"]
        else ("Layer 'wa-layer' attached" if layer_ok else "missing Layer 'wa-layer'")
    )
    ctx.add(
        "Lambda",
        f"Memory, Timeout & Layer ({fn_name})",
        mtl_ok,
        f"Memory {mem}MB, timeout {timeout}s, {layer_note}"
        if mtl_ok
        else f"Memory {mem}MB (min {spec['min_mem']}MB), timeout {timeout}s (min {spec['min_timeout']}s), {layer_note}",
    )

    if spec["env_keys"]:
        env_vars = (cfg.get("Environment") or {}).get("Variables") or {}
        table_ok = env_vars.get("TABLE_NAME") == EXPECTED_TABLE
        prefix_ok = ("TICKET_PREFIX" not in spec["env_keys"]) or bool(str(env_vars.get("TICKET_PREFIX", "")).strip())
        env_ok = table_ok and prefix_ok
        detail_parts = [f"TABLE_NAME={env_vars.get('TABLE_NAME', '<missing>')}"]
        if "TICKET_PREFIX" in spec["env_keys"]:
            detail_parts.append(f"TICKET_PREFIX={env_vars.get('TICKET_PREFIX', '<missing>')}")
        if fn_name == "wa-post-attendee-lambda":
            topic_val = env_vars.get("TOPIC_ARN")
            detail_parts.append("TOPIC_ARN configured" if topic_val else "TOPIC_ARN unset (optional if AsyncDest used)")
        ctx.add(
            "Lambda",
            f"Environment Variables ({fn_name})",
            env_ok,
            f"Required environment variables configured ({', '.join(detail_parts)})"
            if env_ok
            else f"Environment variable mismatch ({', '.join(detail_parts)})",
        )


def check_lambdas(aws: AwsClient, ctx: GradingContext) -> None:
    for fn_name, spec in EXPECTED_LAMBDAS.items():
        _check_single_lambda(aws, ctx, fn_name, spec)


def check_sns(
    aws: AwsClient,
    ctx: GradingContext,
    expected_emails: tuple[str, ...] = EXPECTED_SNS_EMAILS,
) -> None:
    ok, data, err = aws.call(["sns", "list-topics"])
    topics = (data or {}).get("Topics", []) if ok and isinstance(data, dict) else []
    matched = [t["TopicArn"] for t in topics if t.get("TopicArn", "").endswith(f":{EXPECTED_TOPIC}")]
    if not matched:
        ctx.add("SNS", f"Topic Exists ({EXPECTED_TOPIC})", False, err or f"Topic '{EXPECTED_TOPIC}' not found")
        ctx.add("SNS", "Email Subscriptions Confirmed & Target", False, "Skipped: topic missing")
        ctx.add("SNS", "Lambda -> SNS Notification Binding", False, "Skipped: topic missing")
        return

    ctx.topic_arn = matched[0]
    ok_attr, attr_data, _ = aws.call(["sns", "get-topic-attributes", "--topic-arn", ctx.topic_arn])
    disp = ((attr_data or {}).get("Attributes") or {}).get("DisplayName", "") if ok_attr else ""
    ctx.add(
        "SNS",
        f"Topic Exists ({EXPECTED_TOPIC})",
        True,
        f"Topic '{EXPECTED_TOPIC}' active (Display name: {disp})" if disp else f"Topic '{EXPECTED_TOPIC}' active (Display name unset)",
    )

    ok_sub, sub_data, err_sub = aws.call(["sns", "list-subscriptions-by-topic", "--topic-arn", ctx.topic_arn])
    subs = (sub_data or {}).get("Subscriptions", []) if ok_sub and isinstance(sub_data, dict) else []
    email_subs = [s for s in subs if str(s.get("Protocol", "")).lower() == "email"]

    confirmed_emails: set[str] = set()
    pending_emails: list[str] = []
    invalid_emails: list[str] = []
    for sub in email_subs:
        endpoint = str(sub.get("Endpoint", "")).strip()
        arn = str(sub.get("SubscriptionArn", "")).strip()
        if not EMAIL_RE.match(endpoint):
            invalid_emails.append(endpoint or "<empty>")
            continue
        is_confirmed = arn.startswith("arn:aws:sns:") and "PendingConfirmation" not in arn
        if is_confirmed:
            confirmed_emails.add(endpoint.lower())
        else:
            pending_emails.append(endpoint)

    normalized_targets = [e.strip().lower() for e in expected_emails if e.strip()]
    if normalized_targets:
        matched_targets = [e for e in normalized_targets if e in confirmed_emails]
        missing_targets = [e for e in normalized_targets if e not in confirmed_emails and e not in {p.lower() for p in pending_emails}]
        pending_targets = [e for e in normalized_targets if e in {p.lower() for p in pending_emails} and e not in confirmed_emails]
        subs_ok = bool(email_subs) and not missing_targets and not pending_targets and not invalid_emails
        if subs_ok:
            detail_sub = f"Confirmed email subscriptions active for {', '.join(matched_targets)}"
        else:
            issues = []
            if pending_targets:
                issues.append(f"pending confirmation for {', '.join(pending_targets)}")
            if missing_targets:
                issues.append(f"missing target {', '.join(missing_targets)}")
            if invalid_emails:
                issues.append(f"invalid address {', '.join(invalid_emails)}")
            detail_sub = f"Subscription check failed: {'; '.join(issues) or (err_sub or 'no email subscriptions found')}"
    else:
        subs_ok = len(confirmed_emails) > 0 and not invalid_emails
        detail_sub = (
            f"Confirmed email subscriptions active ({', '.join(sorted(confirmed_emails))})"
            if subs_ok
            else (f"No confirmed email subscriptions (pending: {', '.join(pending_emails)})" if email_subs else (err_sub or "No email subscriptions found"))
        )

    ctx.add("SNS", "Email Subscriptions Confirmed & Target", subs_ok, detail_sub)

    # Check TOPIC_ARN env var or async destination on wa-post-attendee-lambda
    ok_fn, fn_data, _ = aws.call(["lambda", "get-function-configuration", "--function-name", "wa-post-attendee-lambda"])
    env_vars = ((fn_data or {}).get("Environment") or {}).get("Variables") or {} if ok_fn else {}
    env_match = env_vars.get("TOPIC_ARN") == ctx.topic_arn

    ok_dest, dest_data, _ = aws.call(
        ["lambda", "get-function-event-invoke-config", "--function-name", "wa-post-attendee-lambda"]
    )
    dest_arn = (
        (((dest_data or {}).get("DestinationConfig") or {}).get("OnSuccess") or {}).get("Destination", "")
        if ok_dest and isinstance(dest_data, dict)
        else ""
    )
    dest_match = dest_arn == ctx.topic_arn
    if env_match and dest_match:
        bind_detail = "Notification linked via TOPIC_ARN and EventInvokeConfig destination"
    elif env_match:
        bind_detail = "Notification linked via TOPIC_ARN environment variable"
    elif dest_match:
        bind_detail = "Notification linked via EventInvokeConfig async destination"
    else:
        bind_detail = "No SNS target configured via TOPIC_ARN or async destination"
    ctx.add("SNS", "Lambda -> SNS Notification Binding", env_match or dest_match, bind_detail)


def _find_route_target(
    aws: AwsClient, api_id: str, resources: list[dict[str, Any]], path: str, method: str
) -> tuple[bool, str]:
    res = next((r for r in resources if r.get("path") == path), None)
    if not res:
        return False, f"Resource '{path}' missing"
    ok, int_data, err = aws.call(
        ["apigateway", "get-integration", "--rest-api-id", api_id, "--resource-id", res["id"], "--http-method", method]
    )
    if not ok or not isinstance(int_data, dict):
        return False, err or f"{method} {path} integration missing"
    int_type = int_data.get("type", "")
    uri = int_data.get("uri", "")
    return True, f"{int_type}:{uri}"


def check_api_gateway(aws: AwsClient, ctx: GradingContext) -> None:
    ok, data, err = aws.call(["apigateway", "get-rest-apis"])
    items = (data or {}).get("items", []) if ok and isinstance(data, dict) else []
    api = next((a for a in items if a.get("name") == EXPECTED_API_NAME), None)
    if not api:
        ctx.add("API Gateway", f"REST API Exists ({EXPECTED_API_NAME})", False, err or f"REST API '{EXPECTED_API_NAME}' not found")
        for label in [
            f"Stage Deployed ({EXPECTED_STAGE})",
            "Routes & AWS_PROXY Integration (/health, /attendees)",
            "CORS OPTIONS Mock on /attendees",
            "CORS Gateway Responses (DEFAULT_4XX, DEFAULT_5XX)",
        ]:
            ctx.add("API Gateway", label, False, "Skipped: REST API missing")
        return

    ctx.api_id = api["id"]
    ep_cfg = api.get("endpointConfiguration") or {}
    ep_types = ep_cfg.get("types") or []
    ip_type = ep_cfg.get("ipAddressType") or "ipv4"
    sec_policy = api.get("securityPolicy")
    sec_ok = (sec_policy is None) or (sec_policy == "SecurityPolicy_TLS13_1_3_2025_09")
    ip_ok = ip_type.lower() == "ipv4"
    api_ok = ("REGIONAL" in ep_types) and ip_ok and sec_ok
    sec_note = f", {sec_policy}" if sec_policy else ""
    ep_str = "/".join(ep_types) if ep_types else "unknown"
    ctx.add(
        "API Gateway",
        f"REST API Exists ({EXPECTED_API_NAME})",
        api_ok,
        f"REST API '{EXPECTED_API_NAME}' active ({ep_str}, {ip_type.upper()}{sec_note}, ID: {ctx.api_id})"
        if api_ok
        else f"Endpoint configuration mismatch ({ep_str}, {ip_type}{sec_note}), expected REGIONAL / IPv4 / TLS 1.3",
    )

    ok_stg, stg_data, _ = aws.call(["apigateway", "get-stages", "--rest-api-id", ctx.api_id])
    stages = (stg_data or {}).get("item", []) if ok_stg and isinstance(stg_data, dict) else []
    prod_stage = next((s for s in stages if s.get("stageName") == EXPECTED_STAGE), None)
    if prod_stage:
        ctx.invoke_url = f"https://{ctx.api_id}.execute-api.{ctx.region}.amazonaws.com/{EXPECTED_STAGE}"
    ctx.add(
        "API Gateway",
        f"Stage Deployed ({EXPECTED_STAGE})",
        bool(prod_stage),
        f"Stage '{EXPECTED_STAGE}' deployed ({ctx.invoke_url})" if prod_stage else f"Deployment stage '{EXPECTED_STAGE}' not found",
    )

    ok_res, res_data, _ = aws.call(["apigateway", "get-resources", "--rest-api-id", ctx.api_id])
    resources = (res_data or {}).get("items", []) if ok_res and isinstance(res_data, dict) else []

    route_specs = [
        ("/health", "GET", "wa-health-lambda"),
        ("/attendees", "GET", "wa-get-attendees-lambda"),
        ("/attendees", "POST", "wa-post-attendee-lambda"),
    ]
    failed_routes: list[str] = []
    for path, method, fn in route_specs:
        found, info = _find_route_target(aws, ctx.api_id, resources, path, method)
        if not (found and info.startswith("AWS_PROXY:") and fn in info):
            failed_routes.append(f"{method} {path}")
    route_ok = len(failed_routes) == 0
    ctx.add(
        "API Gateway",
        "Routes & AWS_PROXY Integration (/health, /attendees)",
        route_ok,
        "All AWS_PROXY routes verified (GET /health, GET /attendees, POST /attendees)"
        if route_ok
        else f"Missing or misconfigured AWS_PROXY integration on: {', '.join(failed_routes)}",
    )

    opt_ok, opt_info = _find_route_target(aws, ctx.api_id, resources, "/attendees", "OPTIONS")
    mock_ok = opt_ok and opt_info.startswith("MOCK:")
    ctx.add(
        "API Gateway",
        "CORS OPTIONS Mock on /attendees",
        mock_ok,
        "OPTIONS preflight MOCK integration configured on /attendees" if mock_ok else f"OPTIONS MOCK integration missing ({opt_info})",
    )

    ok_gr, gr_data, _ = aws.call(["apigateway", "get-gateway-responses", "--rest-api-id", ctx.api_id])
    gr_items = {g.get("responseType"): g for g in ((gr_data or {}).get("items") or [])} if ok_gr else {}
    has_4xx = "gatewayresponse.header.Access-Control-Allow-Origin" in (gr_items.get("DEFAULT_4XX", {}).get("responseParameters") or {})
    has_5xx = "gatewayresponse.header.Access-Control-Allow-Origin" in (gr_items.get("DEFAULT_5XX", {}).get("responseParameters") or {})
    missing_gr = [name for name, ok_flag in (("DEFAULT_4XX", has_4xx), ("DEFAULT_5XX", has_5xx)) if not ok_flag]
    ctx.add(
        "API Gateway",
        "CORS Gateway Responses (DEFAULT_4XX, DEFAULT_5XX)",
        has_4xx and has_5xx,
        "CORS headers enabled on DEFAULT_4XX and DEFAULT_5XX"
        if (has_4xx and has_5xx)
        else f"CORS headers missing on: {', '.join(missing_gr)}",
    )


def check_amplify(aws: AwsClient, ctx: GradingContext) -> None:
    ok, data, err = aws.call(["amplify", "list-apps"])
    apps = (data or {}).get("apps", []) if ok and isinstance(data, dict) else []
    app = next((a for a in apps if a.get("name") == EXPECTED_AMPLIFY_APP), None)
    if not app:
        ctx.add("Amplify", f"Amplify App Exists ({EXPECTED_AMPLIFY_APP})", False, err or f"App '{EXPECTED_AMPLIFY_APP}' not found")
        ctx.add("Amplify", "Branch Active (main)", False, "Skipped: Amplify app missing")
        ctx.add("Amplify", "SPA 200 Rewrite Rule", False, "Skipped: Amplify app missing")
        return

    app_id = app["appId"]
    domain = app.get("defaultDomain") or app_id
    ctx.add(
        "Amplify",
        f"Amplify App Exists ({EXPECTED_AMPLIFY_APP})",
        True,
        f"Amplify app '{EXPECTED_AMPLIFY_APP}' active ({domain})",
    )

    ok_br, br_data, _ = aws.call(["amplify", "list-branches", "--app-id", app_id])
    branches = (br_data or {}).get("branches", []) if ok_br and isinstance(br_data, dict) else []
    main_br = next((b for b in branches if b.get("branchName") == "main"), None)
    ctx.add(
        "Amplify",
        "Branch Active (main)",
        bool(main_br),
        f"Production branch 'main' is active ({main_br.get('stage', 'PRODUCTION')})" if main_br else "Branch 'main' not found",
    )

    ok_app, app_data, _ = aws.call(["amplify", "get-app", "--app-id", app_id])
    full_app = (app_data or {}).get("app", {}) if ok_app and isinstance(app_data, dict) else {}
    rules = full_app.get("customRules") or app.get("customRules") or []
    spa_rule = next(
        (r for r in rules if str(r.get("status")) in ("200", "404-200") and "index.html" in str(r.get("target", ""))),
        None,
    )
    ctx.add(
        "Amplify",
        "SPA 200 Rewrite Rule",
        bool(spa_rule),
        f"SPA rewrite rule active ({spa_rule.get('source', '/<*>')} -> {spa_rule.get('target', '/index.html')}, status: {spa_rule.get('status')})"
        if spa_rule
        else "Missing CloudFront SPA rewrite rule (200 or 404-200) to /index.html",
    )


def _extract_dashboard_metrics(widgets: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    """Extract CloudWatch metric names and namespaces from dashboard widget definitions."""
    namespaces: set[str] = set()
    metric_names: set[str] = set()
    for widget in widgets:
        props = widget.get("properties") or {}
        current_ns = ""
        for row in props.get("metrics") or []:
            if not isinstance(row, list) or len(row) < 2:
                continue
            raw_ns = str(row[0]).strip()
            if raw_ns and raw_ns != ".":
                current_ns = raw_ns
            if current_ns:
                namespaces.add(current_ns)
            metric_name = str(row[1]).strip()
            if metric_name and metric_name != ".":
                metric_names.add(metric_name)
        serialized_props = json.dumps(props)
        for expected in EXPECTED_CW_METRICS:
            if expected in serialized_props:
                metric_names.add(expected)
    return namespaces, metric_names


def check_cloudwatch(aws: AwsClient, ctx: GradingContext) -> None:
    ok_lg, lg_data, err_lg = aws.call(["logs", "describe-log-groups", "--log-group-name-prefix", "/aws/lambda/wa-"])
    groups = {g.get("logGroupName", "") for g in ((lg_data or {}).get("logGroups") or [])} if ok_lg else set()
    expected_groups = {f"/aws/lambda/{fn}" for fn in EXPECTED_LAMBDAS}
    found_groups = sorted(groups & (expected_groups | {"/aws/lambda/wa-lambda"}))
    ctx.add(
        "CloudWatch",
        "Lambda Log Groups Present (/aws/lambda/wa-*)",
        len(found_groups) >= 1,
        f"Log groups active for {len(found_groups)} Lambda function(s) ({', '.join(found_groups)})"
        if found_groups
        else (err_lg or "No /aws/lambda/wa-* log groups found"),
    )

    ok_db, db_data, err_db = aws.call(["cloudwatch", "get-dashboard", "--dashboard-name", EXPECTED_DASHBOARD])
    if not ok_db or not isinstance(db_data, dict):
        ctx.add("CloudWatch", f"Dashboard Exists ({EXPECTED_DASHBOARD})", False, err_db or f"Dashboard '{EXPECTED_DASHBOARD}' not found")
        ctx.add("CloudWatch", "Dashboard & Lambda Metrics (Invocations, Errors, Duration)", False, "Skipped: CloudWatch dashboard not found")
        return

    body_str = db_data.get("DashboardBody", "{}")
    try:
        widgets = (json.loads(body_str) or {}).get("widgets", [])
    except json.JSONDecodeError:
        widgets = []
    has_widget = any("Traffic, Errors & Performance" in str((w.get("properties") or {}).get("title", "")) for w in widgets)
    ctx.add(
        "CloudWatch",
        f"Dashboard Exists ({EXPECTED_DASHBOARD})",
        has_widget or len(widgets) > 0,
        f"Dashboard '{EXPECTED_DASHBOARD}' configured with 'Traffic, Errors & Performance' widget"
        if has_widget
        else f"Dashboard '{EXPECTED_DASHBOARD}' active ({len(widgets)} widget(s)), missing 'Traffic, Errors & Performance' title",
    )

    dash_ns, dash_metrics = _extract_dashboard_metrics(widgets)
    found_dash_metrics = [m for m in EXPECTED_CW_METRICS if m in dash_metrics]
    missing_dash_metrics = [m for m in EXPECTED_CW_METRICS if m not in dash_metrics]

    ok_lm, lm_data, _ = aws.call(["cloudwatch", "list-metrics", "--namespace", "AWS/Lambda"])
    live_fn_names = set(EXPECTED_LAMBDAS.keys()) | {"wa-lambda"}
    live_metrics_found: set[str] = set()
    if ok_lm and isinstance(lm_data, dict):
        for item in lm_data.get("Metrics") or []:
            dims = {d.get("Name"): d.get("Value") for d in (item.get("Dimensions") or []) if isinstance(d, dict)}
            if dims.get("FunctionName") in live_fn_names and item.get("MetricName") in EXPECTED_CW_METRICS:
                live_metrics_found.add(str(item["MetricName"]))

    metrics_ok = len(missing_dash_metrics) == 0
    ns_note = ", ".join(sorted(dash_ns)) if dash_ns else "unspecified"
    live_note = (
        f"live metrics active: {', '.join(sorted(live_metrics_found))}"
        if live_metrics_found
        else "no live AWS/Lambda metrics emitted yet"
    )
    ctx.add(
        "CloudWatch",
        "Dashboard & Lambda Metrics (Invocations, Errors, Duration)",
        metrics_ok,
        f"Dashboard monitors {', '.join(found_dash_metrics)} ({ns_note}; {live_note})"
        if metrics_ok
        else f"Missing dashboard metrics: {', '.join(missing_dash_metrics)} ({live_note})",
    )


def check_e2e_api(aws: AwsClient, ctx: GradingContext) -> None:
    if not ctx.invoke_url:
        for label in [
            "E2E GET /health (200 healthy)",
            "E2E OPTIONS /attendees (CORS 200)",
            "E2E POST /attendees (201 Created)",
            "E2E GET /attendees (DynamoDB Persistence)",
        ]:
            ctx.add("E2E API", label, False, "Skipped: API Gateway prod InvokeURL unavailable")
        return

    # 1. GET /health
    st_h, _, body_h = aws.http_request(f"{ctx.invoke_url}/health")
    health_ok = False
    if st_h == 200:
        try:
            health_ok = json.loads(body_h).get("status") == "healthy"
        except json.JSONDecodeError:
            health_ok = False
    ctx.add(
        "E2E API",
        "E2E GET /health (200 healthy)",
        health_ok,
        "GET /health returned HTTP 200 with healthy status"
        if health_ok
        else f"GET /health failed (HTTP {st_h or 'error'})",
    )

    # 2. OPTIONS /attendees
    st_o, hdr_o, _ = aws.http_request(
        f"{ctx.invoke_url}/attendees",
        method="OPTIONS",
        headers={"Origin": "https://wa-amplify.amplifyapp.com", "Access-Control-Request-Method": "POST"},
    )
    acao = hdr_o.get("access-control-allow-origin", "")
    cors_ok = st_o in (200, 204) and bool(acao)
    ctx.add(
        "E2E API",
        "E2E OPTIONS /attendees (CORS 200)",
        cors_ok,
        f"OPTIONS /attendees preflight returned HTTP {st_o} (Allow-Origin: {acao})"
        if cors_ok
        else f"OPTIONS preflight failed (HTTP {st_o}, Allow-Origin: {acao or 'missing'})",
    )

    # 3. POST /attendees
    st_p, _, body_p = aws.http_request(
        f"{ctx.invoke_url}/attendees",
        method="POST",
        body={
            "name": "__GRADING_TEST_GUEST__",
            "attendanceStatus": "Attending",
            "pax": 2,
            "relationship": "Automated Grader",
            "wishes": "Automated E2E verification",
        },
    )
    created_id = ""
    if st_p == 201:
        try:
            parsed_p = json.loads(body_p)
            created_id = (parsed_p.get("ticket") or {}).get("guestId") or parsed_p.get("guestId") or ""
        except json.JSONDecodeError:
            created_id = ""
    post_ok = st_p == 201 and bool(created_id)
    ctx.add(
        "E2E API",
        "E2E POST /attendees (201 Created)",
        post_ok,
        f"POST /attendees returned HTTP 201 Created (Guest ID: {created_id})"
        if post_ok
        else f"POST /attendees failed (HTTP {st_p}, guestId={'missing' if not created_id else created_id})",
    )

    # 4. GET /attendees + cleanup synthetic item
    st_g, _, body_g = aws.http_request(f"{ctx.invoke_url}/attendees")
    persisted = False
    if st_g == 200 and created_id:
        try:
            items = json.loads(body_g).get("data") or json.loads(body_g).get("attendees") or []
            persisted = any(item.get("guestId") == created_id for item in items)
        except json.JSONDecodeError:
            persisted = False

    if created_id:
        aws.call(["dynamodb", "delete-item", "--table-name", EXPECTED_TABLE, "--key", json.dumps({"guestId": {"S": created_id}})])

    ctx.add(
        "E2E API",
        "E2E GET /attendees (DynamoDB Persistence)",
        persisted,
        "GET /attendees confirmed DynamoDB persistence (test record cleaned up)"
        if persisted
        else f"Submitted record not found via GET /attendees (HTTP {st_g})",
    )


def run_all_checks(
    aws: AwsClient,
    region: str = EXPECTED_REGION,
    on_check: Callable[[CheckResult, int], None] | None = None,
    expected_sns_emails: tuple[str, ...] = EXPECTED_SNS_EMAILS,
) -> GradingContext:
    """Execute the full serverless grading check suite."""
    ctx = GradingContext(region=region, on_check=on_check)
    check_iam(aws, ctx)
    check_dynamodb(aws, ctx)
    check_lambda_layer(aws, ctx)
    check_lambdas(aws, ctx)
    check_sns(aws, ctx, expected_emails=expected_sns_emails)
    check_api_gateway(aws, ctx)
    check_amplify(aws, ctx)
    check_e2e_api(aws, ctx)
    check_cloudwatch(aws, ctx)
    return ctx
