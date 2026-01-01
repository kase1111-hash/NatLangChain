# NatLangChain Load Testing Suite

Comprehensive load testing for validating NatLangChain TPS (Transactions Per Second) and performance under stress.

## Quick Start

```bash
# Install k6 (choose one)
brew install k6          # macOS
snap install k6          # Linux
choco install k6         # Windows

# Start the API server
python -m src.api

# Run smoke test
./tests/load/run-tests.sh smoke

# Run TPS benchmark
./tests/load/run-tests.sh tps
```

## Test Types

| Test | Duration | Purpose |
|------|----------|---------|
| **Smoke** | 30 seconds | Quick sanity check |
| **TPS Benchmark** | 8-10 minutes | Measure transactions per second |
| **Stress** | 30+ minutes | Find breaking points |
| **Soak** | 2 hours | Detect memory leaks, degradation |

## Tools

### k6 (Recommended)

Modern load testing tool with JavaScript scripting.

```bash
# Run specific test
k6 run tests/load/k6/smoke.js
k6 run tests/load/k6/tps-benchmark.js
k6 run tests/load/k6/stress.js
k6 run tests/load/k6/soak.js

# With custom settings
k6 run --env K6_BASE_URL=http://api.example.com \
       --env K6_API_KEY=your-key \
       tests/load/k6/tps-benchmark.js

# Output to JSON
k6 run --out json=results.json tests/load/k6/tps-benchmark.js
```

### Locust (Python)

Python-based load testing with web UI.

```bash
# Install
pip install -r tests/load/requirements.txt

# Web UI mode
locust -f tests/load/locust/locustfile.py --host=http://localhost:5000

# Headless mode
locust -f tests/load/locust/locustfile.py \
       --host=http://localhost:5000 \
       --headless -u 100 -r 10 -t 5m

# TPS benchmark
locust -f tests/load/locust/tps_benchmark.py \
       --host=http://localhost:5000 \
       --headless -u 200 -r 50 -t 7m
```

## TPS Benchmark Details

The TPS benchmark measures transactions per second with comparison targets:

| Target | TPS | Description |
|--------|-----|-------------|
| Baseline | 100 | Minimum acceptable |
| Target | 500 | Expected performance |
| Stretch | 1,000 | Optimized performance |
| Solana | 65,000 | Reference (different architecture) |

### Benchmark Stages

1. **Warm-up** (30s): Ramp to 50 TPS
2. **Scale** (1m): Increase to 100 TPS
3. **Load** (1m): Push to 200 TPS
4. **Peak** (2m): Target 500 TPS
5. **Stress** (2m): Push to 1000 TPS
6. **Cool-down** (1.5m): Gradual decrease

### Success Criteria

- **Throughput**: ≥95% of target TPS
- **Latency**: P95 < 1 second
- **Errors**: < 5% failure rate

## Stress Test Details

The stress test identifies system limits:

1. **Normal load** (50 VUs): Establish baseline
2. **High load** (100 VUs): Test scaling
3. **Stress** (200 VUs): Find degradation
4. **Breaking point** (300 VUs): Identify limits
5. **Recovery**: Verify system recovers

### Metrics Tracked

- Error rate by operation type
- Latency percentiles over time
- Maximum sustainable VUs
- Recovery time after overload

## Soak Test Details

The 2-hour soak test detects:

- Memory leaks
- Connection pool exhaustion
- Database connection issues
- Performance degradation over time

### Analysis

Compare metrics across time windows:
- First 30 minutes vs last 30 minutes
- Look for increasing latency trends
- Monitor error rate changes

## Results

Results are saved to `tests/load/results/`:

```
results/
├── smoke-summary.json
├── tps-benchmark-summary.json
├── stress-summary.json
├── soak-summary.json
└── locust-results.json
```

### Sample TPS Report

```
================================================================================
                        NatLangChain TPS Benchmark Report
================================================================================

THROUGHPUT RESULTS
------------------
  Actual TPS:     487.32
  Target TPS:     500
  Achievement:    97.5%

COMPARISON
----------
  vs Target (500 TPS):   97.5% achieved
  vs Stretch (1000 TPS): 48.7% achieved
  vs Solana (65000 TPS):  0.75% of Solana

LATENCY
-------
  P95: 245.67ms
  P99: 512.34ms

RELIABILITY
-----------
  Success Rate:   99.2%
  Error Rate:     0.8%

================================================================================
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `K6_BASE_URL` | `http://localhost:5000` | API base URL |
| `K6_API_KEY` | `test-api-key` | API authentication key |
| `K6_TEST_RUN` | `default` | Test run identifier |

## CI/CD Integration

Add to GitHub Actions:

```yaml
jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
               --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
               | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update && sudo apt-get install k6

      - name: Start API
        run: python -m src.api &

      - name: Run load tests
        run: |
          sleep 5  # Wait for API
          k6 run tests/load/k6/smoke.js
          k6 run tests/load/k6/tps-benchmark.js

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: load-test-results
          path: tests/load/results/
```

## Troubleshooting

### "API not accessible"

```bash
# Check if API is running
curl http://localhost:5000/health

# Start the API
python -m src.api
```

### Low TPS numbers

1. Check if LLM validation is disabled for benchmarks
2. Ensure `validate: false` in test entries
3. Check network latency between test runner and API
4. Monitor API server resources (CPU, memory)

### High error rates

1. Check rate limiting configuration
2. Verify API key is correct
3. Monitor server logs for errors
4. Check database/Redis connectivity

### k6 not found

```bash
# macOS
brew install k6

# Linux (Ubuntu/Debian)
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6

# Docker
docker run -i grafana/k6 run - <tests/load/k6/smoke.js
```
