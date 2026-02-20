# 🚀 Developer Cheat Sheet: Tight Feedback Loop

Quick reference for rapid development, testing, and debugging.

## 📋 Table of Contents
1. [Development Loop](#development-loop)
2. [Container Testing](#container-testing)
3. [Debugging & Inspection](#debugging--inspection)
4. [Logs & Monitoring](#logs--monitoring)
5. [Business Logic Testing](#business-logic-testing)
6. [Common Workflows](#common-workflows)

---

## 🔄 Development Loop

### **Quick Iteration (No Container)**

```bash
# 1. Enter development environment
nix develop

# 2. Navigate to app
cd apps/research-auditor

# 3. Install/update dependencies
uv sync

# 4. Run the app directly
uv run python -m app.entrypoints.http

# 5. In another terminal, test
curl http://localhost:8080/health

# 6. Make changes to code
# (edit files in app/)

# 7. Stop (Ctrl+C) and rerun
uv run python -m app.entrypoints.http
```

**When to use:** Fast iteration on business logic, no container overhead.

---

### **Test with Hot Reload**

```bash
# Run with auto-reload (if using uvicorn/FastAPI)
uv run uvicorn app.entrypoints.http:app --reload --host 0.0.0.0 --port 8080

# Changes to .py files automatically reload the server
# No need to stop/restart!
```

**When to use:** Making frequent code changes, want instant feedback.

---

## 🐳 Container Testing

### **Build Container**

```bash
# From repo root
nix build .#container

# Result: creates 'result' symlink to container tarball
# Takes: 2-5 minutes first time, seconds if cached
```

---

### **Load & Run Container**

```bash
# Load into Docker
docker load < result

# Run container
docker run -d -p 8080:8080 --name test-app research-auditor:latest

# Or run interactively (see logs in real-time)
docker run -it -p 8080:8080 --name test-app research-auditor:latest
```

---

### **Container Lifecycle Commands**

```bash
# Check if running
docker ps

# Check all containers (including stopped)
docker ps -a

# Stop container
docker stop test-app

# Start stopped container
docker start test-app

# Restart container
docker restart test-app

# Remove container
docker rm test-app

# Remove container (force, even if running)
docker rm -f test-app

# Quick cleanup and restart
docker rm -f test-app && docker run -d -p 8080:8080 --name test-app research-auditor:latest
```

---

### **Container Resource Monitoring**

```bash
# Real-time resource usage
docker stats test-app

# Shows:
# - CPU %
# - Memory usage
# - Network I/O
# - Disk I/O
# Press Ctrl+C to exit
```

---

## 🔍 Debugging & Inspection

### **Examine Container Contents**

```bash
# List all files in container
docker run --rm research-auditor:latest ls -la /app

# Check Python version
docker run --rm research-auditor:latest python --version

# Check installed packages
docker run --rm research-auditor:latest sh -c "cd /app && uv pip list"

# Check environment variables
docker run --rm research-auditor:latest env

# Inspect container metadata
docker inspect research-auditor:latest | jq

# Check what CMD is set
docker inspect research-auditor:latest | jq '.[0].Config.Cmd'

# Check exposed ports
docker inspect research-auditor:latest | jq '.[0].Config.ExposedPorts'
```

---

### **Interactive Shell Inside Container**

```bash
# Enter running container
docker exec -it test-app bash

# Now you're inside the container:
$ cd /app
$ ls -la
$ cat app/entrypoints/http.py
$ python -c "import app; print(app.__file__)"
$ exit
```

---

### **Debug Container Startup Issues**

```bash
# Run container with shell (bypass CMD)
docker run -it --entrypoint bash research-auditor:latest

# Now manually run the startup command to see errors
$ cd /app
$ uv sync --frozen
$ uv run --frozen python -m app.entrypoints.http
```

---

## 📊 Logs & Monitoring

### **View Logs**

```bash
# Show all logs
docker logs test-app

# Follow logs (live tail)
docker logs -f test-app

# Show last 50 lines
docker logs --tail 50 test-app

# Show logs with timestamps
docker logs -t test-app

# Follow logs for last 20 lines
docker logs -f --tail 20 test-app
```

---

### **Search Logs**

```bash
# Search for errors
docker logs test-app 2>&1 | grep -i error

# Search for specific endpoint
docker logs test-app 2>&1 | grep "/audit"

# Count requests
docker logs test-app 2>&1 | grep "GET\|POST" | wc -l

# Show only last hour (if timestamps enabled)
docker logs -t test-app | grep "$(date -u +%Y-%m-%dT%H)"
```

---

## 🧪 Business Logic Testing

### **Test Endpoints**

```bash
# Health check
curl http://localhost:8080/health

# With pretty JSON output
curl -s http://localhost:8080/health | jq

# POST request with data
curl -X POST http://localhost:8080/audit \
  -H "Content-Type: application/json" \
  -d '{
    "target": "example.com",
    "depth": 5
  }' | jq

# Save response to file
curl -s http://localhost:8080/audit \
  -H "Content-Type: application/json" \
  -d '{"target": "example.com"}' > response.json

# Test with authentication (if needed)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8080/protected-endpoint

# Verbose output (see headers, timing)
curl -v http://localhost:8080/health
```

---

### **Python REPL for Quick Tests**

```bash
# Enter development environment
cd apps/research-auditor
uv run python

# In Python REPL:
>>> from app.core import agents
>>> agent = agents.create_research_agent()
>>> agent
<Agent ...>

# Test specific functions
>>> from app.utils import helpers
>>> result = helpers.process_data({"test": "data"})
>>> result

# Exit: Ctrl+D or exit()
```

---

### **Run Tests**

```bash
# Run all tests
cd apps/research-auditor
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_agents.py

# Run specific test function
uv run pytest tests/unit/test_agents.py::test_create_agent

# Run with verbose output
uv run pytest -v

# Run with print statements visible
uv run pytest -s

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run and stop at first failure
uv run pytest -x

# Run only failed tests from last run
uv run pytest --lf
```

---

### **Add Tracing/Debug Logging**

Add to your code:

```python
# app/entrypoints/http.py

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.post("/audit")
async def audit(request: AuditRequest):
    logger.debug(f"Received request: {request}")
    
    result = process_audit(request)
    
    logger.debug(f"Result: {result}")
    return result
```

Then in logs you'll see:
```bash
docker logs -f test-app
# DEBUG:app.entrypoints.http:Received request: ...
# DEBUG:app.entrypoints.http:Result: ...
```

---

### **Interactive Debugging with pdb**

Add breakpoint in code:

```python
# app/core/agents.py

def create_agent():
    # ... some code ...
    
    breakpoint()  # ← Execution pauses here
    
    # ... more code ...
```

Run with Docker attached:
```bash
docker run -it -p 8080:8080 research-auditor:latest

# When breakpoint hits, you get pdb prompt:
(Pdb) print(variable_name)
(Pdb) next  # Execute next line
(Pdb) continue  # Resume execution
(Pdb) list  # Show code context
```

---

## 🎯 Common Workflows

### **Workflow 1: Quick Code Change**

```bash
# 1. Make changes to app/core/agents.py

# 2. Run directly (no container)
cd apps/research-auditor
uv run python -m app.entrypoints.http

# 3. Test in another terminal
curl http://localhost:8080/health

# 4. Stop (Ctrl+C), repeat
```

**Time:** Seconds per iteration

---

### **Workflow 2: Test Container Build**

```bash
# 1. Make changes to code

# 2. Build container
nix build .#container

# 3. Load and run
docker rm -f test-app
docker load < result
docker run -d -p 8080:8080 --name test-app research-auditor:latest

# 4. Test
curl http://localhost:8080/health
docker logs -f test-app

# 5. Cleanup
docker rm -f test-app
```

**Time:** 3-5 minutes per iteration

---

### **Workflow 3: Debug Container Issue**

```bash
# 1. Run container interactively
docker run -it -p 8080:8080 research-auditor:latest

# See errors in real-time

# 2. Or enter running container
docker exec -it test-app bash

# 3. Inspect inside
ls -la /app
cat /app/.venv/lib/python3.12/site-packages/
python -c "import sys; print(sys.path)"

# 4. Check logs
docker logs test-app
```

---

### **Workflow 4: Run Full Test Suite**

```bash
# Run all Nix checks (linting, tests, etc.)
nix flake check

# Or specific check
nix build .#checks.x86_64-linux.test-unit
nix build .#checks.x86_64-linux.lint
```

**Time:** 2-5 minutes

---

## 🔧 Performance Testing

### **Benchmark Response Time**

```bash
# Single request timing
time curl -s http://localhost:8080/health

# Multiple requests
for i in {1..10}; do
  time curl -s http://localhost:8080/audit \
    -H "Content-Type: application/json" \
    -d '{"target": "example.com"}'
done

# Use Apache Bench for load testing
ab -n 100 -c 10 http://localhost:8080/health
# -n 100: Total requests
# -c 10:  Concurrent requests
```

---

### **Memory Profiling**

```bash
# Install memory profiler
uv add memory-profiler

# Add to code:
from memory_profiler import profile

@profile
def my_function():
    # ... code ...

# Run and see memory usage per line
uv run python -m memory_profiler app/core/agents.py
```

---

## 🛠️ Troubleshooting Commands

### **Port Already in Use**

```bash
# Find what's using port 8080
lsof -i :8080

# Kill the process
kill -9 <PID>

# Or use different port
docker run -d -p 8081:8080 --name test-app research-auditor:latest
curl http://localhost:8081/health
```

---

### **Container Won't Start**

```bash
# Check why it exited
docker ps -a
docker logs test-app

# Try running interactively
docker run -it research-auditor:latest

# Override entrypoint to debug
docker run -it --entrypoint bash research-auditor:latest
```

---

### **Can't Import Module**

```bash
# Check if package installed
docker exec test-app sh -c "cd /app && uv pip list | grep package-name"

# Check Python path
docker exec test-app python -c "import sys; print('\n'.join(sys.path))"

# Try importing in container
docker exec -it test-app python
>>> import app
>>> print(app.__file__)
```

---

### **Dependency Issues**

```bash
# Reinstall dependencies
cd apps/research-auditor
rm -rf .venv
uv sync

# Check lock file is up to date
uv lock --check

# Update all dependencies
uv lock --upgrade
uv sync
```

---

## 📝 Quick Reference Card

```bash
# ═══════════════════════════════════════════════════════════════
# ESSENTIAL COMMANDS (Top 10)
# ═══════════════════════════════════════════════════════════════

# 1. Enter dev environment
nix develop

# 2. Run app locally (fast iteration)
cd apps/research-auditor && uv run python -m app.entrypoints.http

# 3. Build container
nix build .#container

# 4. Load and run container
docker load < result && docker run -d -p 8080:8080 --name test-app research-auditor:latest

# 5. Test endpoint
curl http://localhost:8080/health

# 6. View logs
docker logs -f test-app

# 7. Enter container
docker exec -it test-app bash

# 8. Run tests
cd apps/research-auditor && uv run pytest

# 9. Cleanup
docker rm -f test-app

# 10. Full rebuild cycle
nix build .#container && docker rm -f test-app && docker load < result && docker run -d -p 8080:8080 --name test-app research-auditor:latest && docker logs -f test-app

# ═══════════════════════════════════════════════════════════════
```

---

## 🎓 Pro Tips

### **Alias for Common Commands**

Add to `~/.bashrc`:

```bash
# Quick app run
alias app-run='cd apps/research-auditor && uv run python -m app.entrypoints.http'

# Quick test
alias app-test='cd apps/research-auditor && uv run pytest'

# Container rebuild
alias container-rebuild='nix build .#container && docker rm -f test-app && docker load < result && docker run -d -p 8080:8080 --name test-app research-auditor:latest'

# Quick health check
alias health='curl -s http://localhost:8080/health | jq'
```

---

### **Watch for Changes**

```bash
# Auto-run tests on file changes
uv add pytest-watch
cd apps/research-auditor
uv run ptw

# Or use entr
find app tests -name "*.py" | entr -c uv run pytest
```

---

### **Pretty JSON in Logs**

```bash
# If your app outputs JSON logs
docker logs -f test-app | jq -C

# Or save and pretty-print
docker logs test-app > app.log
cat app.log | jq
```

---

## 📖 Additional Resources

- **Nix Manual**: https://nixos.org/manual/nix/stable/
- **Docker CLI Reference**: https://docs.docker.com/engine/reference/commandline/cli/
- **uv Documentation**: https://github.com/astral-sh/uv
- **pytest Documentation**: https://docs.pytest.org/

---

**Save this file as `DEVELOPER_GUIDE.md` in your repo for quick reference!**