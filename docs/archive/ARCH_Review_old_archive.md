# Architectural Review: 2026-software-lab

### Structural Blueprint

┌─────────────────────────────────────────────────┐
│ DEVCONTAINER                                    │
│ Responsibility: "The Hotel Room"               │
│ - Minimal base OS                               │
│ - IDE integration (Cursor/VS Code)              │
│ - Nix installation                              │
│ - Extensions and editor settings                │
│ - Remote connection (SSH)                       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ NIX                                             │
│ Responsibility: "System Packages & Tools"       │
│ - Python runtime                                │
│ - uv (package manager)                          │
│ - System libraries (libffi, zlib, openssl)      │
│ - Node.js (if needed)                           │
│ - Databases (PostgreSQL, Redis, etc.)           │
│ - Build tools                                   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ UV + PYPROJECT.TOML                             │
│ Responsibility: "Python Dependencies"           │
│ - Application-specific Python packages          │
│ - Per-app virtual environments                  │
│ - Lockfiles for reproducibility                 │
└─────────────────────────────────────────────────┘


## Executive Summary

This review examines `flake.nix`, `.devcontainer/devcontainer.json`, `pyproject.toml`, and overall repository structure for bugs, inconsistencies, and opportunities for state-of-the-art improvements.

---

## 1. BUGS AND INCONSISTENCIES

### Critical Bugs

1. **Missing Entry Point Files**
   - `flake.nix` line 27: References `/apps/research-auditor/audit_env.py` - **FILE DOES NOT EXIST**
   - `flake.nix` line 52: References `apps/research-auditor/app.py` - **FILE DOES NOT EXIST**
   - `railway.toml` line 6: References `audit_env.py` - **FILE DOES NOT EXIST**
   - **Impact**: Container builds and Railway deployments will fail
   - **Actual entry point**: `app/main.py` (module path: `app.main`)

2. **Dual Dependency Management Systems**
   - `pyproject.toml` defines dependencies (modern, correct)
   - `apps/research-auditor/requirements.txt` also defines dependencies (legacy, redundant)
   - **Inconsistency**: `requirements.txt` has different versions than `pyproject.toml`
     - `requirements.txt` has `pydantic-ai` (unversioned)
     - `pyproject.toml` has `pydantic-ai-slim[openai]>=0.0.14`
   - **Impact**: Confusion about source of truth, potential version conflicts

3. **Nix Flake References Wrong Python Path**
   - `flake.nix` line 52: Uses `python3 apps/research-auditor/app.py`
   - Should be: `python3 -m app.main` or `uv run python -m app.main`
   - **Impact**: CLI package won't work

4. **Container Image Copies Non-Existent Files**
   - `flake.nix` lines 72-75: Copies `audit_env.py`, `pyproject.toml`, `uv.lock`
   - Missing: Actual app code (`app/` directory)
   - **Impact**: Container will have no application code

### Configuration Inconsistencies

5. **Nixpkgs Version Mismatch**
   - `flake.nix` line 5: Uses `nixos-25.05` (future/unstable)
   - `.github/workflows/ship-registry.yml` line 23: Uses `nixos-23.11` (stable)
   - **Impact**: Different environments may have different package versions

6. **Python Interpreter Path Mismatch**
   - `devcontainer.json` line 30: Sets `python.defaultInterpreterPath: "/usr/local/bin/python"`
   - But Nix provides Python at `${pkgs.python312Full}/bin/python`
   - **Impact**: VS Code may use wrong Python interpreter

7. **Missing flake.lock in Container**
   - `flake.nix` copies `pyproject.toml` and `uv.lock` but not `flake.lock`
   - **Impact**: Container can't reproduce Nix environment exactly

8. **Test File Reference Missing**
   - `flake.nix` line 98: References `${./apps/research-auditor/audit_env.py}` for tests
   - File doesn't exist, test check will fail
   - **Impact**: Nix checks can't run

### Structural Issues

9. **Empty Modules Directory**
   - `/modules` directory exists but is empty
   - `.cursorrules` mentions reusable logic should live in `/modules`
   - **Impact**: Structure doesn't match documentation

10. **Duplicate Dependency Declarations**
    - `python-dotenv` appears in both `pyproject.toml` (line 10) and `requirements.txt` (lines 12, 22)
    - **Impact**: Maintenance burden, potential version drift

11. **Railway Watch Patterns Reference Non-Existent Path**
    - `railway.toml` line 3: `watchPatterns: ["apps/research-auditor/**", "packages/shared/**"]`
    - `packages/shared/**` doesn't exist in repo structure
    - **Impact**: Railway may watch wrong paths

12. **Missing Type Checking Configuration**
    - No `pyrightconfig.json` or `mypy.ini` despite `.cursorrules` emphasizing type hints
    - **Impact**: No enforcement of type safety standards

---

## 2. STATE-OF-THE-ART IMPROVEMENTS

### Build System & Reproducibility

13. **Use flake-utils for Better System Support**
    - Current: Basic `eachDefaultSystem`
    - **Improvement**: Add explicit system list, better cross-compilation support
    - **Benefit**: Better macOS/Windows compatibility

14. **Add Development Dependencies Section**
    - `pyproject.toml` missing `[project.optional-dependencies]` for dev tools
    - **Improvement**: Add `dev = ["pytest", "ruff", "mypy", "black"]`
    - **Benefit**: Clear separation of runtime vs dev dependencies

15. **Lock File Management**
    - Missing `.nix-flake-lock` or explicit lock strategy
    - **Improvement**: Document when to update `flake.lock` vs `uv.lock`
    - **Benefit**: Clearer contribution guidelines

16. **Container Build Optimization**
    - Current: Copies entire repo, builds large image
    - **Improvement**: Multi-stage builds, layer caching, minimal base image
    - **Benefit**: Smaller images, faster builds, better security

### Development Experience

17. **Pre-commit Hooks**
    - Missing: No pre-commit configuration
    - **Improvement**: Add `.pre-commit-config.yaml` with:
      - `ruff` for linting
      - `black` for formatting
      - `mypy` for type checking
      - `nix flake check` for Nix validation
    - **Benefit**: Catch issues before commit

18. **Development Scripts**
    - Missing: Standardized dev commands
    - **Improvement**: Add `justfile` or `Makefile` with:
      - `make dev` - setup environment
      - `make test` - run tests
      - `make lint` - run linters
      - `make format` - format code
    - **Benefit**: Consistent developer workflow

19. **Type Checking Configuration**
    - Missing: Type checker config files
    - **Improvement**: Add `pyrightconfig.json`:
      ```json
      {
        "include": ["apps/**", "modules/**"],
        "exclude": ["**/__pycache__", ".venv"],
        "typeCheckingMode": "strict"
      }
      ```
    - **Benefit**: Enforced type safety

20. **Environment Variable Validation**
    - Current: Silent failures, no validation
    - **Improvement**: Use `pydantic-settings` for env var validation
    - **Benefit**: Fail fast with clear error messages

### CI/CD & Automation

21. **GitHub Actions Improvements**
    - Current: Single workflow, hardcoded branch
    - **Improvements**:
      - Add matrix builds for multiple Python versions
      - Add dependency update automation (Dependabot)
      - Add security scanning (CodeQL, Trivy)
      - Add test runs on PR
    - **Benefit**: Better quality gates

22. **Nix CI Integration**
    - Current: Manual Nix install in workflow
    - **Improvement**: Use `cachix` for binary cache
    - **Benefit**: Faster CI builds

23. **Container Registry Strategy**
    - Current: Single tag `latest`
    - **Improvement**: Tag with git SHA, semantic versions
    - **Benefit**: Better traceability, rollback capability

### Architecture & Modularity

24. **Monorepo Tooling**
    - Missing: Monorepo-aware tooling
    - **Improvement**: Consider `nx`, `turborepo`, or `bazel` for:
      - Dependency graph management
      - Incremental builds
      - Task orchestration
    - **Benefit**: Better scalability as monorepo grows

25. **Shared Module Structure**
    - Current: Empty `/modules` directory
    - **Improvement**: Define module structure:
      ```
      modules/
        shared/
          db/          # Shared database utilities
          auth/        # Shared auth logic
          config/      # Shared configuration
      ```
    - **Benefit**: Clear reuse patterns

26. **Application Structure Standardization**
    - Current: Inconsistent entry points
    - **Improvement**: Standardize all apps:
      ```
      apps/<app-name>/
        app/           # Application code
        tests/         # Tests
        scripts/       # Utility scripts
        pyproject.toml # App-specific deps (if needed)
      ```
    - **Benefit**: Predictable structure

### Observability & Monitoring

27. **Structured Logging**
    - Current: Print statements
    - **Improvement**: Use `structlog` or `loguru` for structured logs
    - **Benefit**: Better debugging, log aggregation

28. **Health Check Endpoints**
    - Missing: No health check for containers
    - **Improvement**: Add `/health` endpoint
    - **Benefit**: Better container orchestration

29. **Metrics & Tracing**
    - Current: Logfire (conditional)
    - **Improvement**: Add OpenTelemetry for:
      - Distributed tracing
      - Metrics collection
      - Standard observability
    - **Benefit**: Production-ready observability

### Security

30. **Dependency Scanning**
    - Current: `pip-audit`, `safety` in requirements.txt but not automated
    - **Improvement**: Add to CI pipeline, use `renovate` or `dependabot`
    - **Benefit**: Automated security updates

31. **Secret Management**
    - Current: Environment variables (good)
    - **Improvement**: Document secret rotation strategy
    - **Benefit**: Better security practices

32. **Container Security**
    - Current: No security scanning
    - **Improvement**: Add `trivy` or `grype` to CI
    - **Benefit**: Catch vulnerabilities in images

### Documentation

33. **Architecture Decision Records (ADRs)**
    - Missing: No ADR directory
    - **Improvement**: Add `docs/adr/` for documenting decisions
    - **Benefit**: Knowledge preservation

34. **API Documentation**
    - Missing: No API docs
    - **Improvement**: Add OpenAPI/Swagger specs
    - **Benefit**: Better API discoverability

35. **Development Setup Guide**
    - Current: README is high-level
    - **Improvement**: Add `docs/DEVELOPMENT.md` with:
      - Step-by-step setup
      - Common issues and solutions
      - Contribution guidelines
    - **Benefit**: Lower onboarding friction

---

## 3. PRIORITY RECOMMENDATIONS

### Immediate (Fix Before Deployment)
1. Fix missing entry point files (Bug #1)
2. Fix container build to include app code (Bug #4)
3. Resolve dual dependency management (Bug #2)
4. Fix Nix flake Python path (Bug #3)

### High Priority (Next Sprint)
5. Add pre-commit hooks (Improvement #17)
6. Add type checking config (Improvement #19)
7. Standardize application structure (Improvement #26)
8. Add CI test runs (Improvement #21)

### Medium Priority (Next Month)
9. Add development dependencies (Improvement #14)
10. Implement structured logging (Improvement #27)
11. Add health checks (Improvement #28)
12. Document development setup (Improvement #35)

### Low Priority (Backlog)
13. Monorepo tooling evaluation (Improvement #24)
14. ADR documentation (Improvement #33)
15. Container optimization (Improvement #16)

---

## 4. SUMMARY

**Total Issues Found**: 35
- **Critical Bugs**: 4
- **Configuration Issues**: 8
- **Improvement Opportunities**: 23

**Overall Assessment**: 
- ✅ Good foundation with Nix + uv
- ✅ Clear separation of concerns (flake.nix, pyproject.toml)
- ❌ Several critical bugs preventing deployment
- ❌ Missing modern development tooling
- ⚠️ Inconsistent structure and documentation

**Recommendation**: Fix critical bugs first, then systematically add tooling and documentation to reach state-of-the-art standards.
