/**
 * TPS Benchmark Test
 *
 * Measures transactions per second (TPS) under various load levels.
 * Compares results against target thresholds and Solana benchmarks.
 *
 * Run: k6 run tests/load/k6/tps-benchmark.js
 * With options: k6 run --env K6_BASE_URL=http://api.example.com tests/load/k6/tps-benchmark.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend, Gauge } from 'k6/metrics';
import { config, getHeaders, generateEntry } from './config.js';

// Custom metrics
const entryCreationRate = new Rate('entry_creation_success');
const entryLatency = new Trend('entry_creation_latency');
const actualTPS = new Gauge('actual_tps');
const entriesCreated = new Counter('entries_created');

export const options = {
    scenarios: {
        // Ramp up to find maximum sustainable TPS
        tps_ramp: {
            executor: 'ramping-arrival-rate',
            startRate: 10,
            timeUnit: '1s',
            preAllocatedVUs: 50,
            maxVUs: 200,
            stages: [
                { target: 50, duration: '30s' },    // Warm up to 50 TPS
                { target: 100, duration: '1m' },   // Scale to 100 TPS
                { target: 200, duration: '1m' },   // Scale to 200 TPS
                { target: 500, duration: '2m' },   // Scale to 500 TPS
                { target: 1000, duration: '2m' },  // Push to 1000 TPS
                { target: 500, duration: '1m' },   // Scale down
                { target: 100, duration: '30s' },  // Cool down
            ],
        },
    },
    thresholds: {
        'entry_creation_success': ['rate>0.95'],      // 95% success rate
        'entry_creation_latency': ['p(95)<1000'],     // 95th percentile < 1s
        'http_req_failed': ['rate<0.05'],             // < 5% errors
        'http_req_duration': ['p(95)<2000'],          // 95th percentile < 2s
    },
};

export function setup() {
    // Verify API is accessible
    const res = http.get(`${config.baseUrl}/health`);
    if (res.status !== 200) {
        throw new Error(`API not accessible: ${res.status}`);
    }

    console.log(`Starting TPS benchmark against ${config.baseUrl}`);
    console.log(`Target TPS: ${config.tpsTargets.target}`);
    console.log(`Stretch TPS: ${config.tpsTargets.stretch}`);

    return {
        startTime: Date.now(),
    };
}

export default function (data) {
    group('Entry Creation TPS', () => {
        const entry = generateEntry();
        const startTime = Date.now();

        const res = http.post(
            `${config.baseUrl}/entry`,
            JSON.stringify(entry),
            { headers: getHeaders() }
        );

        const latency = Date.now() - startTime;
        entryLatency.add(latency);

        const success = check(res, {
            'entry created': (r) => r.status === 201 || r.status === 200,
            'has entry hash': (r) => {
                try {
                    const body = JSON.parse(r.body);
                    return body.entry_hash !== undefined || body.message !== undefined;
                } catch {
                    return false;
                }
            },
        });

        entryCreationRate.add(success);
        if (success) {
            entriesCreated.add(1);
        }
    });

    // Small delay to prevent connection exhaustion
    sleep(0.01);
}

export function teardown(data) {
    const duration = (Date.now() - data.startTime) / 1000;
    console.log(`\nTest completed in ${duration.toFixed(2)} seconds`);
}

export function handleSummary(data) {
    // Calculate actual TPS achieved
    const totalRequests = data.metrics.http_reqs?.values?.count || 0;
    const duration = data.state?.testRunDurationMs / 1000 || 1;
    const tps = totalRequests / duration;

    const summary = {
        timestamp: new Date().toISOString(),
        test: 'tps-benchmark',
        results: {
            total_requests: totalRequests,
            duration_seconds: duration,
            actual_tps: tps.toFixed(2),
            target_tps: config.tpsTargets.target,
            stretch_tps: config.tpsTargets.stretch,
            solana_comparison_tps: config.tpsTargets.solanaComparison,
            performance_vs_target: `${((tps / config.tpsTargets.target) * 100).toFixed(1)}%`,
            performance_vs_solana: `${((tps / config.tpsTargets.solanaComparison) * 100).toFixed(4)}%`,
        },
        metrics: {
            http_req_duration_p95: data.metrics.http_req_duration?.values?.['p(95)'],
            http_req_duration_p99: data.metrics.http_req_duration?.values?.['p(99)'],
            http_req_failed_rate: data.metrics.http_req_failed?.values?.rate,
            entry_creation_success_rate: data.metrics.entry_creation_success?.values?.rate,
            entry_creation_latency_p95: data.metrics.entry_creation_latency?.values?.['p(95)'],
        },
        thresholds: data.thresholds,
    };

    // Console output
    console.log('\n' + '='.repeat(60));
    console.log('TPS BENCHMARK RESULTS');
    console.log('='.repeat(60));
    console.log(`Actual TPS: ${tps.toFixed(2)}`);
    console.log(`Target TPS: ${config.tpsTargets.target} (${summary.results.performance_vs_target} achieved)`);
    console.log(`Stretch TPS: ${config.tpsTargets.stretch}`);
    console.log(`Solana Comparison: ${config.tpsTargets.solanaComparison} TPS (${summary.results.performance_vs_solana})`);
    console.log(`P95 Latency: ${summary.metrics.http_req_duration_p95?.toFixed(2)}ms`);
    console.log(`Error Rate: ${(summary.metrics.http_req_failed_rate * 100)?.toFixed(2)}%`);
    console.log('='.repeat(60));

    return {
        'results/tps-benchmark-summary.json': JSON.stringify(summary, null, 2),
        stdout: generateTextReport(summary),
    };
}

function generateTextReport(summary) {
    return `
================================================================================
                        NatLangChain TPS Benchmark Report
================================================================================

Test Run: ${summary.timestamp}

THROUGHPUT RESULTS
------------------
  Actual TPS:     ${summary.results.actual_tps}
  Target TPS:     ${summary.results.target_tps}
  Achievement:    ${summary.results.performance_vs_target}

COMPARISON
----------
  vs Target (${summary.results.target_tps} TPS):   ${summary.results.performance_vs_target}
  vs Stretch (${summary.results.stretch_tps} TPS): ${((parseFloat(summary.results.actual_tps) / summary.results.stretch_tps) * 100).toFixed(1)}%
  vs Solana (${summary.results.solana_comparison_tps} TPS):  ${summary.results.performance_vs_solana}

LATENCY
-------
  P95: ${summary.metrics.http_req_duration_p95?.toFixed(2) || 'N/A'}ms
  P99: ${summary.metrics.http_req_duration_p99?.toFixed(2) || 'N/A'}ms

RELIABILITY
-----------
  Success Rate:   ${((1 - (summary.metrics.http_req_failed_rate || 0)) * 100).toFixed(2)}%
  Error Rate:     ${((summary.metrics.http_req_failed_rate || 0) * 100).toFixed(2)}%

================================================================================
`;
}
