#!/bin/bash
#
# NatLangChain Load Test Runner
#
# Usage:
#   ./run-tests.sh smoke          # Quick smoke test
#   ./run-tests.sh tps            # TPS benchmark
#   ./run-tests.sh stress         # Stress test
#   ./run-tests.sh soak           # 2-hour soak test
#   ./run-tests.sh all            # Run all tests (except soak)
#   ./run-tests.sh locust         # Run Locust tests
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
BASE_URL="${K6_BASE_URL:-http://localhost:5000}"
API_KEY="${K6_API_KEY:-test-api-key}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Check for k6
check_k6() {
    if ! command -v k6 &> /dev/null; then
        echo -e "${YELLOW}k6 is not installed. Install with:${NC}"
        echo "  brew install k6  # macOS"
        echo "  snap install k6  # Linux"
        echo "  choco install k6 # Windows"
        echo "  Or download from: https://k6.io/docs/getting-started/installation/"
        return 1
    fi
    return 0
}

# Check for locust
check_locust() {
    if ! command -v locust &> /dev/null; then
        echo -e "${YELLOW}locust is not installed. Install with:${NC}"
        echo "  pip install -r tests/load/requirements.txt"
        return 1
    fi
    return 0
}

# Check API is accessible
check_api() {
    echo "Checking API at ${BASE_URL}..."
    if curl -sf "${BASE_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}API is accessible${NC}"
        return 0
    else
        echo -e "${RED}API is not accessible at ${BASE_URL}${NC}"
        echo "Make sure the NatLangChain server is running:"
        echo "  python -m src.api"
        return 1
    fi
}

# Run smoke test
run_smoke() {
    echo -e "\n${GREEN}Running Smoke Test...${NC}"
    check_k6 || return 1
    check_api || return 1

    k6 run \
        --env K6_BASE_URL="${BASE_URL}" \
        --env K6_API_KEY="${API_KEY}" \
        --out json="${RESULTS_DIR}/smoke-$(date +%Y%m%d-%H%M%S).json" \
        "${SCRIPT_DIR}/k6/smoke.js"
}

# Run TPS benchmark
run_tps() {
    echo -e "\n${GREEN}Running TPS Benchmark...${NC}"
    check_k6 || return 1
    check_api || return 1

    k6 run \
        --env K6_BASE_URL="${BASE_URL}" \
        --env K6_API_KEY="${API_KEY}" \
        --out json="${RESULTS_DIR}/tps-$(date +%Y%m%d-%H%M%S).json" \
        "${SCRIPT_DIR}/k6/tps-benchmark.js"
}

# Run stress test
run_stress() {
    echo -e "\n${GREEN}Running Stress Test...${NC}"
    check_k6 || return 1
    check_api || return 1

    k6 run \
        --env K6_BASE_URL="${BASE_URL}" \
        --env K6_API_KEY="${API_KEY}" \
        --out json="${RESULTS_DIR}/stress-$(date +%Y%m%d-%H%M%S).json" \
        "${SCRIPT_DIR}/k6/stress.js"
}

# Run soak test
run_soak() {
    echo -e "\n${YELLOW}Running Soak Test (2 hours)...${NC}"
    echo "This test will run for approximately 2 hours."
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Soak test cancelled."
        return 0
    fi

    check_k6 || return 1
    check_api || return 1

    k6 run \
        --env K6_BASE_URL="${BASE_URL}" \
        --env K6_API_KEY="${API_KEY}" \
        --out json="${RESULTS_DIR}/soak-$(date +%Y%m%d-%H%M%S).json" \
        "${SCRIPT_DIR}/k6/soak.js"
}

# Run Locust tests
run_locust() {
    echo -e "\n${GREEN}Running Locust Tests...${NC}"
    check_locust || return 1
    check_api || return 1

    echo "Choose Locust test mode:"
    echo "  1) Web UI (interactive)"
    echo "  2) Headless (5 minutes, 100 users)"
    echo "  3) TPS Benchmark"
    read -p "Select [1-3]: " -n 1 -r
    echo

    case $REPLY in
        1)
            echo "Starting Locust Web UI at http://localhost:8089"
            locust -f "${SCRIPT_DIR}/locust/locustfile.py" --host="${BASE_URL}"
            ;;
        2)
            locust -f "${SCRIPT_DIR}/locust/locustfile.py" \
                --host="${BASE_URL}" \
                --headless \
                -u 100 -r 10 -t 5m \
                --csv="${RESULTS_DIR}/locust-$(date +%Y%m%d-%H%M%S)"
            ;;
        3)
            locust -f "${SCRIPT_DIR}/locust/tps_benchmark.py" \
                --host="${BASE_URL}" \
                --headless \
                -u 200 -r 50 -t 7m \
                --csv="${RESULTS_DIR}/tps-locust-$(date +%Y%m%d-%H%M%S)"
            ;;
        *)
            echo "Invalid option"
            return 1
            ;;
    esac
}

# Run all tests (except soak)
run_all() {
    echo -e "\n${GREEN}Running All Tests...${NC}"
    run_smoke
    run_tps
    run_stress
    echo -e "\n${GREEN}All tests completed!${NC}"
    echo "Results saved to: ${RESULTS_DIR}"
}

# Show usage
show_usage() {
    echo "NatLangChain Load Test Runner"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  smoke    Quick smoke test (30 seconds)"
    echo "  tps      TPS benchmark (8-10 minutes)"
    echo "  stress   Stress test (30+ minutes)"
    echo "  soak     Soak/endurance test (2 hours)"
    echo "  locust   Run Locust tests (interactive)"
    echo "  all      Run smoke, tps, and stress tests"
    echo ""
    echo "Environment Variables:"
    echo "  K6_BASE_URL   API base URL (default: http://localhost:5000)"
    echo "  K6_API_KEY    API key for authentication"
    echo ""
    echo "Examples:"
    echo "  $0 smoke"
    echo "  K6_BASE_URL=http://api.example.com $0 tps"
}

# Main
case "${1:-}" in
    smoke)
        run_smoke
        ;;
    tps)
        run_tps
        ;;
    stress)
        run_stress
        ;;
    soak)
        run_soak
        ;;
    locust)
        run_locust
        ;;
    all)
        run_all
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
