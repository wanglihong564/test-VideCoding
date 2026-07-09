#!/usr/bin/env python3
"""Read-only prelaunch repository scanner.

This script gathers launch-readiness signals without modifying the target
project. It does not run tests, audits, or security probes. Treat its output as
triage input for the prelaunch-test-audit workflow, not as a final audit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    "target",
    "bin",
    "obj",
}
EXCLUDED_FILES = {
    "prelaunch_static_scan.py",
}

TEXT_EXTENSIONS = {
    ".env",
    ".example",
    ".ini",
    ".json",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".py",
    ".rb",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".php",
    ".yml",
    ".yaml",
    ".toml",
    ".xml",
    ".properties",
    ".gradle",
    ".kts",
    ".md",
    ".txt",
    ".sh",
    ".ps1",
    ".dockerfile",
}

SECRET_KEY_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|pwd|private[_-]?key|access[_-]?key|client[_-]?secret)"
)
SECRET_VALUE_RE = re.compile(r"[:=]\s*['\"]?([A-Za-z0-9_./+=-]{12,})['\"]?")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
ROUTE_HINT_RE = re.compile(
    r"(@(?:app|router)\.route|@(?:get|post|put|patch|delete)\(|\b(?:app|router)\.(?:get|post|put|patch|delete|use)\(|\bRoute::|\bHttp(?:Get|Post|Put|Patch|Delete)|\bfastify\.(?:get|post|put|patch|delete)\(|@(?:RestController|Controller|RequestMapping|GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping)|\b(?:path|re_path)\()"
)
TEST_RESULT_RE = re.compile(r"(?i)\b(pass(?:ed)?|fail(?:ed)?|error|skipped?)\b")
JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
TS_EXTENSIONS = {".ts", ".tsx"}
PY_EXTENSIONS = {".py"}
JVM_EXTENSIONS = {".java", ".kt"}
PHP_EXTENSIONS = {".php"}
NODE_ROUTE_RE = re.compile(
    r"\b(?:app|router|fastify)\.(get|post|put|patch|delete|use)\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
FASTAPI_ROUTE_RE = re.compile(
    r"@(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
LARAVEL_ROUTE_RE = re.compile(r"\bRoute::(get|post|put|patch|delete|any)\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
DJANGO_ROUTE_RE = re.compile(r"\b(?:path|re_path)\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
SPRING_ROUTE_RE = re.compile(
    r"@(GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping|RequestMapping)\s*(?:\(\s*(?:value\s*=\s*)?['\"]([^'\"]*)['\"])?",
    re.IGNORECASE,
)
NEST_ROUTE_RE = re.compile(r"@(Controller|Get|Post|Put|Patch|Delete)\b\s*(?:\(\s*['\"]([^'\"]*)['\"])?", re.IGNORECASE)
NEXT_METHOD_RE = re.compile(r"export\s+async\s+function\s+(GET|POST|PUT|PATCH|DELETE)", re.IGNORECASE)
ASSERTION_RE = re.compile(
    r"(?i)(\bassert\b|expect\(|should\(|assertThat\(|self\.assert|pytest\.raises|toBe\(|toEqual\(|toHaveBeenCalled|toMatchObject)"
)
WEAK_ASSERTION_RE = re.compile(
    r"(?i)(status(?:_code)?\s*(?:==|toBe|toEqual)?\s*\(?20[0-4]\)?|toHaveStatus\(\s*20[0-4]\s*\)|success\s*[:=]\s*true|expect\(true\)\.toBe\(true\))"
)
STATUS_ASSERTION_RE = re.compile(
    r"(?i)(expect\([^)]*(?:status|statusCode|status_code)[^)]*\)\.(?:toBe|toEqual)\(\s*20[0-4]\s*\)|toHaveStatus\(\s*20[0-4]\s*\)|assert(?:Equal)?\([^,\n]*(?:status|status_code|statusCode)[^,\n]*,\s*20[0-4]\s*\))"
)
TAUTOLOGY_ASSERTION_RE = re.compile(
    r"(?i)(expect\(\s*true\s*\)\.(?:toBe|toEqual)\(\s*true\s*\)|expect\(\s*1\s*\)\.(?:toBe|toEqual)\(\s*1\s*\)|assert\s+true\b|assert(?:Equal)?\(\s*true\s*,\s*true\s*\))"
)
BUSINESS_ASSERTION_RE = re.compile(
    r"(?i)(database|db\.|repository|persist|save|insert|update|delete|amount|price|inventory|stock|role|permission|owner|user_id|order_id|balance|ledger|refund|payment|status_changed|audit)"
)
SECURITY_FILE_RE = re.compile(r"(?i)(auth|middleware|guard|permission|policy|security|cors|csrf|jwt|session|rbac|acl)")
RISK_TERMS = {
    "money": ("pay", "payment", "refund", "price", "billing", "invoice", "order", "checkout", "subscription", "credit"),
    "permissions": ("admin", "role", "permission", "auth", "login", "password", "token", "oauth", "user", "account"),
    "data": ("delete", "remove", "update", "import", "export", "upload", "download", "profile", "record"),
    "availability": ("search", "report", "bulk", "queue", "webhook", "ai", "generate", "sms", "email"),
}


def is_text_candidate(path: Path) -> bool:
    if path.name in {".env", ".env.example", "Dockerfile"}:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def iter_files(root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for filename in filenames:
            if filename in EXCLUDED_FILES:
                continue
            path = Path(dirpath) / filename
            files.append(path)
            if len(files) >= max_files:
                return files
    return files


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path, max_bytes: int = 500_000) -> str:
    data = path.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


def parse_package_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(read_text(path))
    except Exception as exc:
        return {"error": str(exc)}
    return {
        "scripts": data.get("scripts", {}),
        "dependencies": sorted((data.get("dependencies") or {}).keys()),
        "devDependencies": sorted((data.get("devDependencies") or {}).keys()),
    }


def detect_manifests(files: list[Path], root: Path) -> dict[str, list[str]]:
    names = {}
    for path in files:
        names.setdefault(path.name, []).append(rel(path, root))
    manifest_names = [
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pyproject.toml",
        "requirements.txt",
        "poetry.lock",
        "uv.lock",
        "Cargo.toml",
        "Cargo.lock",
        "go.mod",
        "go.sum",
        "pom.xml",
        "mvnw",
        "build.gradle",
        "build.gradle.kts",
        "gradlew",
        "composer.json",
        "composer.lock",
        "artisan",
        "manage.py",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
    ]
    return {name: names[name] for name in manifest_names if name in names}


def analyze_package_managers(manifests: dict[str, list[str]]) -> list[str]:
    notes: list[str] = []
    if "package.json" in manifests:
        locks = [name for name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock") if name in manifests]
        if locks:
            notes.append(f"JavaScript lockfile present: {', '.join(locks)}")
        else:
            notes.append("JavaScript package.json found without a recognized lockfile.")
    if "pyproject.toml" in manifests or "requirements.txt" in manifests:
        locks = [name for name in ("poetry.lock", "uv.lock") if name in manifests]
        if locks:
            notes.append(f"Python lockfile present: {', '.join(locks)}")
        else:
            notes.append("Python dependency manifest found; verify pinning/lock strategy.")
    if "Cargo.toml" in manifests and "Cargo.lock" not in manifests:
        notes.append("Cargo.toml found without Cargo.lock.")
    if "go.mod" in manifests and "go.sum" not in manifests:
        notes.append("go.mod found without go.sum.")
    return notes


def find_package_scripts(root: Path, manifests: dict[str, list[str]]) -> list[dict[str, Any]]:
    packages = []
    for package_rel in manifests.get("package.json", []):
        path = root / package_rel
        parsed = parse_package_json(path)
        packages.append({"path": package_rel, **parsed})
    return packages


def package_names(packages: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for package in packages:
        names.update(package.get("dependencies") or [])
        names.update(package.get("devDependencies") or [])
    return names


def detect_frameworks(files: list[Path], root: Path, manifests: dict[str, list[str]], packages: list[dict[str, Any]]) -> list[str]:
    frameworks: set[str] = set()
    deps = package_names(packages)
    if "express" in deps:
        frameworks.add("Express")
    if "fastify" in deps:
        frameworks.add("Fastify")
    if "next" in deps:
        frameworks.add("Next.js")
    if "@nestjs/core" in deps or "@nestjs/common" in deps:
        frameworks.add("NestJS")
    if "manage.py" in manifests:
        frameworks.add("Django")
    if "artisan" in manifests:
        frameworks.add("Laravel")

    for path in files:
        r = rel(path, root).lower()
        if "pages/api/" in r or "/app/api/" in r or r.startswith("app/api/"):
            frameworks.add("Next.js API Routes")
        if r.endswith("urls.py"):
            frameworks.add("Django")
        if r in {"routes/api.php", "routes/web.php"} or r.endswith("/routes/api.php") or r.endswith("/routes/web.php"):
            frameworks.add("Laravel")
        if path.name in {"pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "requirements.txt", "pyproject.toml"}:
            try:
                text = read_text(path, 200_000).lower()
            except OSError:
                continue
            if "spring-boot" in text or "springframework.boot" in text:
                frameworks.add("Spring Boot")
            if "django" in text:
                frameworks.add("Django")
            if "fastapi" in text:
                frameworks.add("FastAPI")
            if "laravel/framework" in text:
                frameworks.add("Laravel")
    for path in files:
        if not is_text_candidate(path):
            continue
        try:
            text = read_text(path, 120_000)
        except OSError:
            continue
        if "@RestController" in text or "@RequestMapping" in text or "@GetMapping" in text:
            frameworks.add("Spring Boot")
        if "@Controller" in text and ("@Get" in text or "@Post" in text or "@Put" in text):
            frameworks.add("NestJS")
        if FASTAPI_ROUTE_RE.search(text):
            frameworks.add("FastAPI")
        if NODE_ROUTE_RE.search(text):
            frameworks.add("Express/Fastify-style routing")
    return sorted(frameworks)


def normalize_route_path(path: str) -> str:
    if not path:
        return "/"
    cleaned = path.strip()
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return re.sub(r"//+", "/", cleaned)


def spring_method(annotation: str) -> str:
    mapping = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "PatchMapping": "PATCH",
        "DeleteMapping": "DELETE",
    }
    return mapping.get(annotation, "ANY")


def nest_method(annotation: str) -> str:
    mapping = {
        "Get": "GET",
        "Post": "POST",
        "Put": "PUT",
        "Patch": "PATCH",
        "Delete": "DELETE",
        "Controller": "ANY",
    }
    return mapping.get(annotation, "ANY")


def next_route_from_file(path: Path, root: Path, text: str) -> dict[str, str] | None:
    r = rel(path, root).replace("\\", "/")
    lower = r.lower()
    route_path = None
    if lower.startswith("pages/api/"):
        route_path = "/" + r[len("pages/api/") :]
        route_path = re.sub(r"\.(js|jsx|ts|tsx)$", "", route_path, flags=re.IGNORECASE)
        route_path = route_path.replace("/index", "")
    elif lower.startswith("app/api/") and lower.endswith(("/route.js", "/route.ts", "/route.tsx", "/route.jsx")):
        route_path = "/" + r[len("app/") :]
        route_path = re.sub(r"/route\.(js|jsx|ts|tsx)$", "", route_path, flags=re.IGNORECASE)
    if route_path is None:
        return None
    methods = sorted({match.group(1).upper() for match in NEXT_METHOD_RE.finditer(text)})
    return {"method": ",".join(methods) if methods else "ANY", "path": normalize_route_path(route_path)}


def risk_hint_details_for(method: str, route_path: str, handler: str, file_path: str) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []

    def add_matches(source: str, strength: str, value: str) -> None:
        haystack = value.lower()
        for risk, terms in RISK_TERMS.items():
            if any(term in haystack for term in terms):
                details.append({"risk": risk, "strength": strength, "source": source})

    add_matches("path", "strong", route_path)
    add_matches("handler", "medium", handler)
    add_matches("file", "weak", file_path)
    if method.upper() in {"DELETE", "PUT", "PATCH"}:
        details.append({"risk": "data", "strength": "strong", "source": "method"})

    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for detail in details:
        unique[(detail["risk"], detail["strength"], detail["source"])] = detail
    return list(unique.values())


def risk_hints_from_details(details: list[dict[str, str]]) -> list[str]:
    return sorted({detail["risk"] for detail in details})


def route_entry(framework: str, method: str, route_path: str, path: Path, root: Path, line_no: int, handler: str) -> dict[str, Any]:
    r = rel(path, root)
    normalized = normalize_route_path(route_path)
    risk_details = risk_hint_details_for(method.upper(), normalized, handler, r)
    return {
        "method": method.upper(),
        "path": normalized,
        "file": r,
        "line": line_no,
        "framework": framework,
        "handler": handler.strip()[:160],
        "risk_hints": risk_hints_from_details(risk_details),
        "risk_hint_details": risk_details,
    }


def extract_route_inventory(files: list[Path], root: Path) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for path in files:
        if not is_text_candidate(path):
            continue
        try:
            text = read_text(path, 300_000)
        except OSError:
            continue
        next_route = next_route_from_file(path, root, text)
        if next_route:
            routes.append(route_entry("Next.js API Routes", next_route["method"], next_route["path"], path, root, 1, path.name))
        ext = path.suffix.lower()
        for line_no, line in enumerate(text.splitlines(), start=1):
            if ext in PY_EXTENSIONS:
                for match in FASTAPI_ROUTE_RE.finditer(line):
                    routes.append(route_entry("FastAPI", match.group(1), match.group(2), path, root, line_no, line))
                if path.name == "urls.py":
                    for match in DJANGO_ROUTE_RE.finditer(line):
                        routes.append(route_entry("Django", "ANY", match.group(1), path, root, line_no, line))
            if ext in JS_EXTENSIONS:
                for match in NODE_ROUTE_RE.finditer(line):
                    routes.append(route_entry("Express/Fastify-style routing", match.group(1), match.group(2), path, root, line_no, line))
            if ext in PHP_EXTENSIONS:
                for match in LARAVEL_ROUTE_RE.finditer(line):
                    routes.append(route_entry("Laravel", match.group(1), match.group(2), path, root, line_no, line))
            if ext in JVM_EXTENSIONS:
                for match in SPRING_ROUTE_RE.finditer(line):
                    annotation = match.group(1)
                    route_path = match.group(2) or ""
                    routes.append(route_entry("Spring Boot", spring_method(annotation), route_path, path, root, line_no, line))
            if ext in TS_EXTENSIONS:
                for match in NEST_ROUTE_RE.finditer(line):
                    annotation = match.group(1)
                    route_path = match.group(2) or ""
                    routes.append(route_entry("NestJS", nest_method(annotation), route_path, path, root, line_no, line))
    unique: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for route in routes:
        key = (route["method"], route["path"], route["file"], route["line"])
        unique[key] = route
    return list(unique.values())[:300]


def find_security_surface(files: list[Path], root: Path, routes: list[dict[str, Any]]) -> dict[str, Any]:
    security_files: list[str] = []
    for path in files:
        r = rel(path, root)
        if SECURITY_FILE_RE.search(r):
            security_files.append(r)
    high_risk_routes = [
        route
        for route in routes
        if any(detail["strength"] in {"strong", "medium"} for detail in route.get("risk_hint_details", []))
        or route["method"] in {"DELETE", "PUT", "PATCH"}
        or re.search(r"(?i)(admin|webhook|upload|payment|auth|token|password|export|import)", route["path"])
    ][:100]
    notes: list[str] = []
    if security_files:
        notes.append("Review security/auth/middleware/guard files for authentication and authorization coverage.")
    if any("permissions" in route["risk_hints"] for route in high_risk_routes):
        notes.append("Permission-sensitive routes detected; verify horizontal and vertical access control.")
    if any("money" in route["risk_hints"] for route in high_risk_routes):
        notes.append("Money/order/payment routes detected; verify backend-owned amounts, idempotency, and webhook signatures.")
    if any("upload" in route["path"].lower() for route in high_risk_routes):
        notes.append("Upload routes detected; verify file type, size, path traversal, malware, and storage permissions.")
    return {
        "security_files": sorted(set(security_files))[:150],
        "high_risk_routes": high_risk_routes,
        "notes": notes,
    }


def inspect_test_quality(files: list[Path], root: Path) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_warning(file_path: str, pattern: str, risk: str) -> None:
        key = (file_path, pattern)
        if key not in seen:
            warnings.append({"file": file_path, "pattern": pattern, "risk": risk})
            seen.add(key)

    for path in files:
        r = rel(path, root)
        if not re.search(r"(?i)(^test_|_test\.|\.test\.|\.spec\.|/tests?/)", path.as_posix()):
            continue
        if not is_text_candidate(path):
            continue
        try:
            text = read_text(path, 250_000)
        except OSError:
            continue
        if not ASSERTION_RE.search(text):
            add_warning(r, "no obvious assertion", "test may not verify behavior")
            continue
        if TAUTOLOGY_ASSERTION_RE.search(text):
            add_warning(r, "tautological assertion", "test can pass without exercising product behavior")
        status_matches = len(STATUS_ASSERTION_RE.findall(text))
        weak_matches = len(WEAK_ASSERTION_RE.findall(text))
        assertion_matches = len(ASSERTION_RE.findall(text))
        has_business_assertion = bool(BUSINESS_ASSERTION_RE.search(text))
        if status_matches and not has_business_assertion:
            add_warning(r, "only HTTP status assertions", "may not validate persisted business results")
        if weak_matches and weak_matches >= max(1, assertion_matches // 2):
            add_warning(r, "status/success-heavy assertions", "may not validate business results")
        if re.search(r"(?i)(jest\.mock|MagicMock|mockResolvedValue|mockReturnValue|patch\()", text) and not re.search(
            r"(?i)(database|db\.|repository|persist|save|insert|update|delete|amount|inventory|role|permission)",
            text,
        ):
            add_warning(r, "mock-heavy test without obvious business assertion", "may test mocks instead of real behavior")
    return warnings[:100]


def find_route_candidates(files: list[Path], root: Path) -> list[str]:
    candidates: list[str] = []
    name_re = re.compile(r"(?i)(route|router|controller|endpoint|api)")
    for path in files:
        if not is_text_candidate(path):
            continue
        if name_re.search(path.name):
            candidates.append(rel(path, root))
            continue
        try:
            text = read_text(path, 100_000)
        except OSError:
            continue
        if ROUTE_HINT_RE.search(text):
            candidates.append(rel(path, root))
    return sorted(set(candidates))[:100]


def find_test_candidates(files: list[Path], root: Path) -> list[str]:
    test_re = re.compile(r"(?i)(^test_|_test\.|\.test\.|\.spec\.|/tests?/)")
    return sorted(rel(path, root) for path in files if test_re.search(path.as_posix()))[:150]


def find_config_candidates(files: list[Path], root: Path) -> dict[str, list[str]]:
    groups = {
        "env_examples": [],
        "ci": [],
        "docker": [],
        "migrations": [],
    }
    for path in files:
        r = rel(path, root)
        lower = r.lower()
        if path.name.startswith(".env") or lower.endswith(".env.example") or "env.example" in lower:
            groups["env_examples"].append(r)
        if ".github/workflows/" in lower or lower.startswith(".gitlab-ci") or "azure-pipelines" in lower:
            groups["ci"].append(r)
        if "dockerfile" in lower or "docker-compose" in lower:
            groups["docker"].append(r)
        if "migration" in lower or "migrations/" in lower:
            groups["migrations"].append(r)
    return {key: values[:100] for key, values in groups.items() if values}


def scan_secrets(files: list[Path], root: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for path in files:
        if len(hits) >= 100:
            break
        if not is_text_candidate(path):
            continue
        try:
            text = read_text(path, 300_000)
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if PRIVATE_KEY_RE.search(line):
                hits.append({"path": rel(path, root), "line": str(line_no), "reason": "private key marker"})
            elif SECRET_KEY_RE.search(line):
                value_match = SECRET_VALUE_RE.search(line)
                if not value_match:
                    continue
                raw_value = value_match.group(1)
                if "(" in line and not re.search(r"['\"][^'\"]{12,}['\"]", line):
                    continue
                if raw_value.startswith(("scan_", "find_", "detect_", "summarize_")):
                    continue
                redacted = re.sub(SECRET_VALUE_RE, ": <redacted>", line.strip())
                if not re.search(r"(?i)(example|placeholder|changeme|your_|dummy|test)", redacted):
                    hits.append({"path": rel(path, root), "line": str(line_no), "reason": redacted[:160]})
            if len(hits) >= 100:
                break
    return hits


def summarize_test_log(path: Path) -> dict[str, Any]:
    text = read_text(path, 1_000_000)
    counts: dict[str, int] = {"pass": 0, "fail": 0, "error": 0, "skip": 0}
    interesting: list[str] = []
    for line in text.splitlines():
        if TEST_RESULT_RE.search(line):
            lower = line.lower()
            if "fail" in lower:
                counts["fail"] += 1
            if "error" in lower:
                counts["error"] += 1
            if "pass" in lower:
                counts["pass"] += 1
            if "skip" in lower:
                counts["skip"] += 1
            if len(interesting) < 30:
                interesting.append(line[:220])
    return {"path": str(path), "counts": counts, "sample_lines": interesting}


def build_scan(root: Path, max_files: int, test_log: Path | None) -> dict[str, Any]:
    files = iter_files(root, max_files=max_files)
    manifests = detect_manifests(files, root)
    packages = find_package_scripts(root, manifests)
    frameworks = detect_frameworks(files, root, manifests, packages)
    route_inventory = extract_route_inventory(files, root)
    route_candidates = find_route_candidates(files, root)
    test_candidates = find_test_candidates(files, root)
    config_candidates = find_config_candidates(files, root)
    security_surface = find_security_surface(files, root, route_inventory)
    test_quality_warnings = inspect_test_quality(files, root)
    secret_hits = scan_secrets(files, root)
    result: dict[str, Any] = {
        "root": str(root),
        "files_scanned": len(files),
        "manifests": manifests,
        "package_manager_notes": analyze_package_managers(manifests),
        "package_json": packages,
        "frameworks": frameworks,
        "route_inventory": route_inventory,
        "route_candidates": route_candidates,
        "test_candidates": test_candidates,
        "config_candidates": config_candidates,
        "security_surface": security_surface,
        "test_quality_warnings": test_quality_warnings,
        "potential_secret_hits": secret_hits,
        "suggested_safe_commands": suggest_commands(manifests, packages),
        "suggested_next_checks": suggest_next_checks(route_inventory, test_candidates, config_candidates, secret_hits, test_quality_warnings),
    }
    if test_log:
        result["test_log_summary"] = summarize_test_log(test_log)
    return result


def suggest_commands(manifests: dict[str, list[str]], packages: list[dict[str, Any]]) -> list[str]:
    commands: list[str] = []
    runner = "npm"
    if "pnpm-lock.yaml" in manifests:
        runner = "pnpm"
    elif "yarn.lock" in manifests:
        runner = "yarn"
    for package in packages:
        scripts = package.get("scripts") or {}
        package_dir = str(Path(package["path"]).parent).replace("\\", "/")
        prefix = "" if package_dir == "." else f"cd {package_dir} && "
        for script_name in sorted(scripts):
            lower = script_name.lower()
            if any(term in lower for term in ("test", "e2e", "integration", "unit", "lint", "build", "typecheck", "check")):
                commands.append(f"{prefix}{runner} run {script_name}")
    if "pnpm-lock.yaml" in manifests:
        commands.append("pnpm audit")
    elif "package-lock.json" in manifests or "package.json" in manifests:
        commands.append("npm audit")
    if "requirements.txt" in manifests or "pyproject.toml" in manifests:
        commands.append("pip-audit")
        commands.append("python -m pytest")
    if "manage.py" in manifests:
        commands.append("python manage.py test")
    if "pom.xml" in manifests:
        commands.append("mvn test")
        commands.append("mvn verify")
    if "build.gradle" in manifests or "build.gradle.kts" in manifests:
        if "gradlew" in manifests:
            commands.append("./gradlew test")
        else:
            commands.append("gradle test")
    if "composer.json" in manifests:
        commands.append("vendor/bin/phpunit")
    if "artisan" in manifests:
        commands.append("php artisan test")
    if "Cargo.lock" in manifests:
        commands.append("cargo audit")
    if "Cargo.toml" in manifests:
        commands.append("cargo test")
    if "go.mod" in manifests:
        commands.append("go test ./...")
    return sorted(set(commands))


def suggest_next_checks(
    routes: list[dict[str, Any]],
    tests: list[str],
    configs: dict[str, list[str]],
    secret_hits: list[dict[str, str]],
    test_quality_warnings: list[dict[str, str]],
) -> list[str]:
    checks: list[str] = []
    if routes:
        checks.append("Review route inventory for auth, authorization, validation, and sensitive response fields.")
        if any(route["risk_hints"] for route in routes):
            checks.append("Prioritize route tests for entries with money, permissions, data, or availability risk hints.")
    if not tests:
        checks.append("No obvious test files found; identify manual checks or add regression coverage for high-risk flows.")
    if test_quality_warnings:
        checks.append("Weak-test patterns detected; verify important tests assert real business outcomes.")
    if "migrations" in configs:
        checks.append("Review migrations for backup, rollback, idempotency, and old-data compatibility.")
    if "env_examples" not in configs:
        checks.append("No env example detected; verify required production variables are documented elsewhere.")
    if secret_hits:
        checks.append("Potential secret-like values found; confirm whether they are real secrets and rotate if needed.")
    return checks


def render_markdown(scan: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Prelaunch Static Scan")
    lines.append("")
    lines.append(f"Root: `{scan['root']}`")
    lines.append(f"Files scanned: {scan['files_scanned']}")
    lines.append("")
    lines.append("## Manifests")
    for name, paths in scan["manifests"].items():
        lines.append(f"- `{name}`: {', '.join(f'`{p}`' for p in paths)}")
    if not scan["manifests"]:
        lines.append("- None detected")
    lines.append("")
    lines.append("## Package Manager Notes")
    for note in scan["package_manager_notes"] or ["No package manager issues detected from manifests."]:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("## Package Scripts")
    for package in scan["package_json"]:
        scripts = package.get("scripts") or {}
        lines.append(f"- `{package['path']}` scripts: {', '.join(sorted(scripts.keys())) or 'none'}")
    if not scan["package_json"]:
        lines.append("- No package.json files detected")
    lines.append("")
    lines.append("## Frameworks")
    for framework in scan["frameworks"] or ["None detected"]:
        lines.append(f"- {framework}")
    lines.append("")
    lines.append("## Route Inventory")
    if scan["route_inventory"]:
        lines.append("| Method | Path | Framework | File | Risk hints |")
        lines.append("|---|---|---|---|---|")
        for route in scan["route_inventory"][:80]:
            file_ref = f"{route['file']}:{route['line']}"
            hints = ", ".join(
                f"{detail['risk']}({detail['strength']}:{detail['source']})"
                for detail in route.get("risk_hint_details", [])
            ) or "-"
            lines.append(f"| {route['method']} | `{route['path']}` | {route['framework']} | `{file_ref}` | {hints} |")
    else:
        lines.append("- None detected")
    lines.append("")
    lines.append("## Route Candidates")
    for path in scan["route_candidates"][:50]:
        lines.append(f"- `{path}`")
    if not scan["route_candidates"]:
        lines.append("- None detected")
    lines.append("")
    lines.append("## Test Candidates")
    for path in scan["test_candidates"][:50]:
        lines.append(f"- `{path}`")
    if not scan["test_candidates"]:
        lines.append("- None detected")
    lines.append("")
    lines.append("## Config Candidates")
    for group, paths in scan["config_candidates"].items():
        lines.append(f"- {group}: {', '.join(f'`{p}`' for p in paths[:20])}")
    if not scan["config_candidates"]:
        lines.append("- None detected")
    lines.append("")
    lines.append("## Security Surface")
    surface = scan["security_surface"]
    if surface["security_files"]:
        lines.append("Security/auth-related files:")
        for path in surface["security_files"][:50]:
            lines.append(f"- `{path}`")
    else:
        lines.append("Security/auth-related files: none detected")
    if surface["high_risk_routes"]:
        lines.append("")
        lines.append("High-risk route hints:")
        for route in surface["high_risk_routes"][:50]:
            hints = ", ".join(
                f"{detail['risk']}({detail['strength']}:{detail['source']})"
                for detail in route.get("risk_hint_details", [])
            ) or "method/path risk"
            lines.append(f"- `{route['method']} {route['path']}` in `{route['file']}:{route['line']}` ({hints})")
    if surface["notes"]:
        lines.append("")
        lines.append("Security notes:")
        for note in surface["notes"]:
            lines.append(f"- {note}")
    lines.append("")
    lines.append("## Test Quality Warnings")
    for warning in scan["test_quality_warnings"][:50]:
        lines.append(f"- `{warning['file']}`: {warning['pattern']} ({warning['risk']})")
    if not scan["test_quality_warnings"]:
        lines.append("- None detected by heuristic scan")
    lines.append("")
    lines.append("## Potential Secret Hits")
    for hit in scan["potential_secret_hits"][:50]:
        lines.append(f"- `{hit['path']}:{hit['line']}` {hit['reason']}")
    if not scan["potential_secret_hits"]:
        lines.append("- None detected by heuristic scan")
    lines.append("")
    lines.append("## Suggested Safe Commands")
    for command in scan["suggested_safe_commands"] or ["None inferred"]:
        lines.append(f"- `{command}`")
    lines.append("")
    lines.append("## Suggested Next Checks")
    for check in scan["suggested_next_checks"] or ["Use manual risk triage from SKILL.md."]:
        lines.append(f"- {check}")
    if "test_log_summary" in scan:
        lines.append("")
        lines.append("## Test Log Summary")
        summary = scan["test_log_summary"]
        lines.append(f"Log: `{summary['path']}`")
        lines.append(f"Counts: `{summary['counts']}`")
        for sample in summary["sample_lines"]:
            lines.append(f"- {sample}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only prelaunch repository scanner")
    parser.add_argument("root", nargs="?", default=".", help="Repository root to scan")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--max-files", type=int, default=5000)
    parser.add_argument("--test-log", type=Path, help="Optional test output log to summarize")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        parser.error(f"root does not exist: {root}")
    if args.test_log and not args.test_log.exists():
        parser.error(f"test log does not exist: {args.test_log}")

    scan = build_scan(root, max_files=args.max_files, test_log=args.test_log)
    if args.format == "json":
        print(json.dumps(scan, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(scan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
