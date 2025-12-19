#!/bin/bash

echo "================================================================================"
echo "  Running End-to-End Blockchain Negotiation Test 10 Times"
echo "================================================================================"

SUCCESS_COUNT=0
FAIL_COUNT=0

for i in {1..10}; do
  echo ""
  echo "────────────────────────────────────────────────────────────────────────────────"
  echo "  TEST RUN $i of 10"
  echo "────────────────────────────────────────────────────────────────────────────────"

  # Run the test and capture output
  OUTPUT=$(python test_e2e_simple.py 2>&1)
  EXIT_CODE=$?

  # Check if test passed
  if [ $EXIT_CODE -eq 0 ] && echo "$OUTPUT" | grep -q "END-TO-END TEST COMPLETED SUCCESSFULLY"; then
    echo "  ✅ Run $i: PASSED"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

    # Show key metrics
    echo "$OUTPUT" | grep -E "Total Blocks:|Chain Valid:|Blockchain integrity verified:" | sed 's/^/    /'
  else
    echo "  ❌ Run $i: FAILED (Exit code: $EXIT_CODE)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "$OUTPUT" | tail -10
  fi
done

echo ""
echo "================================================================================"
echo "  FINAL RESULTS"
echo "================================================================================"
echo "  Total Runs:    10"
echo "  Passed:        $SUCCESS_COUNT ✅"
echo "  Failed:        $FAIL_COUNT ❌"
echo "  Success Rate:  $((SUCCESS_COUNT * 10))%"
echo "================================================================================"
