---
name: test-generator
description: Built-in test generation skill — comprehensive, multi-layer testing methodology adapted to repo stack
---

# Test Generator

Generates comprehensive test suites for a Linear ticket. Detects the repo's tech stack, selects applicable test layers based on code changes, and writes all tests in a single session.

## Stack Detection

| Stack | Signal Files | Test Layers |
|-------|-------------|-------------|
| Backend | requirements.txt, pyproject.toml, go.mod, Cargo.toml, pom.xml, Gemfile | unit, integration, contract, security, resilience, e2e-api |
| Frontend | next.config.*, vite.config.*, angular.json, package.json with react/vue/angular/svelte | unit, e2e-browser |
| Fullstack | Both backend + frontend signals | All layers |

## Smart Layer Selection

Not every ticket needs every test layer. Select layers based on what files are being changed:

| Test Layer | Trigger Keywords in Changed Files |
|-----------|----------------------------------|
| **Unit tests** | Always included |
| **Integration tests** | Always included |
| **Contract tests** | api/, routes/, endpoint, openapi, schema, swagger, graphql |
| **Security tests** | auth, permission, middleware, token, session, password, rbac, oauth, jwt |
| **Resilience tests** | retry, timeout, circuit, fallback, client/, http, grpc, queue |
| **E2E API tests** | api/, routes/, endpoint, handler, controller, view |
| **E2E browser tests** | page, component, view, screen, layout, modal |

---

## Phase 1: Discover Existing Patterns

Before writing any tests, understand the repo's testing conventions:

```bash
# Find test framework and config
ls pytest.ini pyproject.toml setup.cfg jest.config.* vitest.config.* 2>/dev/null
cat pyproject.toml 2>/dev/null | grep -A 20 '\[tool.pytest'
cat package.json 2>/dev/null | grep -E '"(jest|vitest|mocha|playwright)"'

# Find existing test files and structure
find . -type f -name "test_*.py" -o -name "*.test.ts" -o -name "*.spec.ts" 2>/dev/null | head -20

# Find fixtures, factories, conftest
find . -name "conftest.py" -o -name "factories.py" -o -name "fixtures.*" 2>/dev/null
```

**Rules:**
- Use the SAME test framework already in the repo (pytest, jest, vitest, go test, etc.)
- Follow the SAME directory structure (tests/unit/, tests/integration/, __tests__/, etc.)
- Reuse existing fixtures, factories, and helpers — do NOT recreate them
- Match naming conventions (test_*.py, *.test.ts, *.spec.ts, etc.)
- If no tests exist, use the framework's standard conventions

---

## Phase 2: Test Setup

Only create infrastructure that doesn't already exist:

**Python repos:**
- `conftest.py` with shared fixtures (test client, auth helpers, DB setup)
- Use Testcontainers for real DB in integration tests (not SQLite)
- Reuse existing app factory pattern if available

**Node.js repos:**
- Shared test utilities and mocks
- Use existing test setup files (setupTests.ts, globalSetup.ts)

**Verification:**
```bash
# Confirm test framework is installed and runnable
pytest --version 2>/dev/null || npm test -- --version 2>/dev/null || go test -h 2>/dev/null
```

---

## Phase 3: Unit Tests

**Purpose:** Test business logic in isolation. All external I/O is mocked.

**Rules:**
- One test file per source module (e.g., `test_auth_service.py` for `auth_service.py`)
- Mock ALL external dependencies: database, HTTP clients, file I/O, message queues
- Test the happy path + at least 3 error scenarios per function
- Each acceptance criterion from the ticket must have a corresponding test
- Edge cases mentioned in ticket comments must be tested

**Python pattern:**
```python
@pytest.fixture
def service(mock_db, mock_http_client):
    return MyService(db=mock_db, client=mock_http_client)

def test_happy_path(service):
    result = service.process(valid_input)
    assert result.status == "success"

def test_invalid_input_raises(service):
    with pytest.raises(ValidationError):
        service.process(invalid_input)

def test_db_failure_handled(service, mock_db):
    mock_db.find.side_effect = ConnectionError("timeout")
    with pytest.raises(ServiceUnavailable):
        service.process(valid_input)
```

**Node.js pattern:**
```typescript
describe('MyService', () => {
  it('should process valid input', async () => {
    const result = await service.process(validInput);
    expect(result.status).toBe('success');
  });

  it('should throw on invalid input', async () => {
    await expect(service.process(invalidInput)).rejects.toThrow(ValidationError);
  });
});
```

**Verification:**
```bash
# Every service file should have a corresponding test file
for f in $(find app/services -name "*.py" ! -name "__init__.py" ! -name "test_*" 2>/dev/null); do
  module=$(basename "$f" .py)
  test_file=$(find tests -name "test_${module}.py" 2>/dev/null)
  [ -n "$test_file" ] && echo "[OK] $module" || echo "[MISSING] test_${module}.py"
done
```

---

## Phase 4: Integration Tests

**Purpose:** Test full request → service → database flows with a real database.

**Rules:**
- Use Testcontainers (Python/Java) or Docker-based test DB — never SQLite as substitute
- Test all relevant HTTP status codes: 200, 201, 204, 400, 401, 403, 404, 409, 422
- One test file per route group or API resource
- Each test must clean up its own data (use transactions or truncation)
- Test with the real app client (httpx.AsyncClient, supertest, etc.)

**Python pattern (FastAPI + Testcontainers):**
```python
@pytest.mark.asyncio
async def test_create_resource(client, auth_headers):
    response = await client.post("/api/resources", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]

@pytest.mark.asyncio
async def test_create_duplicate_returns_409(client, auth_headers, seed_resource):
    response = await client.post("/api/resources", json=duplicate_payload, headers=auth_headers)
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_get_without_auth_returns_401(client):
    response = await client.get("/api/resources")
    assert response.status_code == 401
```

**Verification:**
```bash
# Each route group should have integration tests
echo "Integration test files:"
find tests/integration -name "test_*.py" 2>/dev/null || find tests -name "*integration*" 2>/dev/null
```

---

## Phase 5: Contract Tests (if API endpoints affected)

**Purpose:** Lock the API surface — detect breaking schema changes.

**Rules:**
- Generate an OpenAPI baseline from the running app
- Validate response schemas match the baseline
- Detect breaking changes: removed endpoints, changed field types, removed required fields
- Only apply if the ticket touches API endpoints or schemas

**Pattern:**
```python
def test_response_matches_schema(client, openapi_schema):
    response = client.get("/api/resources")
    validate(instance=response.json(), schema=openapi_schema["paths"]["/api/resources"]["get"]["responses"]["200"])

def test_no_breaking_changes(current_schema, baseline_schema):
    removed = set(baseline_schema["paths"]) - set(current_schema["paths"])
    assert not removed, f"Breaking change: endpoints removed: {removed}"
```

**Verification:**
```bash
# Contract test files exist
find tests -name "*contract*" -o -name "*schema*" 2>/dev/null
```

---

## Phase 6: Security Tests (if auth/input affected)

**Purpose:** Verify authentication, authorization, and input validation boundaries.

**Rules:**
- Test JWT/token vulnerabilities: expired tokens, invalid signatures, missing tokens
- Test authorization boundaries: cross-user access, privilege escalation
- Test input validation: injection attempts, oversized payloads, special characters
- Test security headers if applicable (X-Content-Type-Options, X-Frame-Options)
- Only apply if the ticket touches auth, permissions, or input handling

**Pattern:**
```python
def test_expired_token_returns_401(client):
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/protected", headers=headers)
    assert response.status_code == 401

def test_user_cannot_access_other_user_resource(client, user_a_headers, user_b_resource):
    response = client.get(f"/api/resources/{user_b_resource.id}", headers=user_a_headers)
    assert response.status_code == 403

def test_sql_injection_prevented(client, auth_headers):
    response = client.get("/api/search", params={"q": "'; DROP TABLE users;--"}, headers=auth_headers)
    assert response.status_code in (400, 200)  # must not crash
```

**Verification:**
```bash
# Security test files exist with auth scenarios
find tests -name "*security*" -o -name "*auth*" 2>/dev/null
```

---

## Phase 7: Resilience Tests (if external calls affected)

**Purpose:** Verify graceful degradation when external dependencies fail.

**When to apply:** Only if the ticket touches code that calls external services, databases, or message queues.

**Rules:**
- Test timeout handling for every external call
- Test connection error recovery
- Test malformed response handling
- Test 5xx error recovery from downstream services
- Mock the failure modes — never test against real external services

**Pattern:**
```python
def test_timeout_returns_service_unavailable(service, mock_client):
    mock_client.get.side_effect = httpx.TimeoutException("timeout")
    with pytest.raises(ServiceUnavailable):
        service.fetch_data()

def test_connection_error_handled(service, mock_client):
    mock_client.get.side_effect = httpx.ConnectError("refused")
    result = service.fetch_data_with_fallback()
    assert result == default_fallback_value

def test_malformed_response_handled(service, mock_client):
    mock_client.get.return_value = httpx.Response(200, json={"unexpected": "schema"})
    with pytest.raises(ParseError):
        service.fetch_data()
```

**Verification:**
```bash
# Resilience test files exist
find tests -name "*resilience*" -o -name "*timeout*" -o -name "*retry*" 2>/dev/null
```

---

## Phase 8: E2E Tests

### E2E API Tests (backend)

**Purpose:** Test complete multi-step business workflows.

**Rules:**
- Test full CRUD lifecycle: Create → Read → Update → List → Delete → Verify deleted
- Use numbered test steps for explicit ordering
- State carries forward between steps (class attributes or module-level vars)
- Clean up all test data after the workflow completes

**Pattern:**
```python
class TestResourceLifecycle:
    resource_id = None

    def test_step_1_create(self, client, auth_headers):
        response = client.post("/api/resources", json=payload, headers=auth_headers)
        assert response.status_code == 201
        self.__class__.resource_id = response.json()["id"]

    def test_step_2_read(self, client, auth_headers):
        response = client.get(f"/api/resources/{self.resource_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_step_3_delete(self, client, auth_headers):
        response = client.delete(f"/api/resources/{self.resource_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_step_4_verify_deleted(self, client, auth_headers):
        response = client.get(f"/api/resources/{self.resource_id}", headers=auth_headers)
        assert response.status_code == 404
```

### E2E Browser Tests (frontend)

**Purpose:** Test critical UI workflows in a real browser.

**Rules:**
- Use Playwright with Page Object Model pattern
- Use `data-testid` selectors — never CSS classes
- No `time.sleep()` — use Playwright's built-in waiting (expect, wait_for_selector)
- Screenshots captured on failure automatically

**Pattern:**
```python
class LoginPage:
    def __init__(self, page):
        self.page = page
        self.email_input = page.locator('[data-testid="email-input"]')
        self.password_input = page.locator('[data-testid="password-input"]')
        self.submit_btn = page.locator('[data-testid="login-submit"]')

    async def login(self, email, password):
        await self.email_input.fill(email)
        await self.password_input.fill(password)
        await self.submit_btn.click()

def test_login_flow(page):
    login_page = LoginPage(page)
    login_page.login("user@example.com", "password")
    expect(page.locator('[data-testid="dashboard"]')).to_be_visible()
```

**Verification:**
```bash
# E2E test files exist
find tests -name "*e2e*" -o -name "*browser*" -o -name "*playwright*" 2>/dev/null
```

---

## Phase 9: Test Review (mandatory final gate)

Run this AFTER writing all test layers, BEFORE committing.

### Checklist

1. **External service leak scan** — No test should call real external services. All HTTP clients, DB connections, and message queue clients must be mocked or use Testcontainers.
   ```bash
   # Check for hardcoded URLs in test files (excluding mocks and fixtures)
   grep -rn "https\?://" tests/ --include="*.py" | grep -v "localhost" | grep -v "testcontainers" | grep -v "mock" | grep -v "fixture"
   ```

2. **DB safety audit** — No production database URLs, no hardcoded connection strings, no shared state between tests.
   ```bash
   grep -rn "postgresql://" tests/ --include="*.py" | grep -v "testcontainers" | grep -v "localhost"
   ```

3. **Mock target verification** — Every `mock.patch("app.services.foo.bar")` target must exist in the actual source code.
   ```bash
   grep -rn "mock.patch\|@patch\|mocker.patch" tests/ --include="*.py"
   # Manually verify each target path exists
   ```

4. **Duplication scan** — No copy-pasted test infrastructure (conftest code, fixture setup). Shared code belongs in conftest.py or helpers.
   ```bash
   # Look for duplicate fixture definitions
   grep -rn "^def.*fixture" tests/ --include="*.py" | sort | uniq -d
   ```

5. **Lint and format check:**
   ```bash
   # Python
   ruff check tests/ 2>/dev/null; ruff format --check tests/ 2>/dev/null
   # Node.js
   npx eslint tests/ 2>/dev/null
   ```

6. **Run full test suite** — All tests should run together without interference.
   ```bash
   pytest tests/ -v --tb=short 2>&1 | tail -40
   ```

7. **Acceptance criteria coverage** — Every acceptance criterion from the ticket has at least one test. List them and confirm.

---

## Critical Rules

1. **ONLY write tests.** Do NOT implement the fix/feature. Do NOT modify source code files.
2. **ONLY test the specific changes** listed in the scope. Do NOT test unrelated parts of the codebase.
3. **Every acceptance criterion** must have at least one corresponding test.
4. **Edge cases from ticket comments** must be tested.
5. **Follow the repo's existing test conventions** — same framework, directory structure, fixtures, naming.
6. **No catch-all test files** — tests go in module-aligned files.
7. **Verify mock targets exist** before mocking them. `mock.patch("app.foo.bar")` fails silently if `bar` doesn't exist.
8. **Tests SHOULD fail** initially — the implementation doesn't exist yet. If they all pass, you're testing the wrong thing.
9. **Never create or modify GitHub workflow files** (`.github/workflows/*.yml`) or CI/CD configs.
10. **Do NOT push.** Do NOT create a PR. Just commit locally.
