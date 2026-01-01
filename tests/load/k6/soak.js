/**
 * Soak Test (Endurance Test)
 *
 * Runs at moderate load for an extended period to detect:
 * - Memory leaks
 * - Resource exhaustion
 * - Performance degradation over time
 *
 * Run: k6 run tests/load/k6/soak.js
 * Note: This test runs for 2 hours by default
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend, Counter, Gauge } from 'k6/metrics';
import { config, getHeaders, generateEntry } from './config.js';

// Metrics for tracking degradation over time
const latencyOverTime = new Trend('latency_over_time');
const memoryIndicator = new Gauge('memory_pressure_indicator');
const requestsPerMinute = new Counter('requests_per_minute');

export const options = {
    scenarios: {
        soak: {
            executor: 'constant-vus',
            vus: 50,  // Moderate, sustainable load
            duration: '2h',  // 2 hour endurance test
        },
    },
    thresholds: {
        // Strict thresholds - performance should not degrade
        'http_req_duration': ['p(95)<1000', 'p(99)<2000'],
        'http_req_failed': ['rate<0.01'],
        'latency_over_time': ['p(95)<1000'],
    },
};

// Track time windows for degradation analysis
let windowStart = Date.now();
let windowRequests = 0;
const WINDOW_SIZE_MS = 60000; // 1 minute windows

export function setup() {
    const res = http.get(`${config.baseUrl}/health`);
    if (res.status !== 200) {
        throw new Error('API not accessible');
    }
    console.log('Starting 2-hour soak test - monitoring for performance degradation');
    return {
        startTime: Date.now(),
        checkpoints: [],
    };
}

export default function (data) {
    const iterationStart = Date.now();

    // Mixed workload to simulate real usage
    const operation = Math.random();

    if (operation < 0.5) {
        // 50% - Entry creation
        group('Create Entry', () => {
            const entry = generateEntry();
            const res = http.post(
                `${config.baseUrl}/entry`,
                JSON.stringify(entry),
                { headers: getHeaders() }
            );

            check(res, {
                'entry created': (r) => r.status === 201 || r.status === 200,
            });
        });
    } else if (operation < 0.8) {
        // 30% - Read chain
        group('Read Chain', () => {
            const res = http.get(`${config.baseUrl}/chain`);
            check(res, {
                'chain retrieved': (r) => r.status === 200,
            });
        });
    } else {
        // 20% - Health check (lightweight)
        group('Health Check', () => {
            const res = http.get(`${config.baseUrl}/health`);
            check(res, {
                'health ok': (r) => r.status === 200,
            });
        });
    }

    const latency = Date.now() - iterationStart;
    latencyOverTime.add(latency);

    // Track requests per minute window
    windowRequests++;
    if (Date.now() - windowStart >= WINDOW_SIZE_MS) {
        requestsPerMinute.add(windowRequests);
        windowRequests = 0;
        windowStart = Date.now();

        // Log checkpoint every minute
        const elapsed = Math.floor((Date.now() - data.startTime) / 60000);
        console.log(`Checkpoint: ${elapsed} minutes elapsed, ${latency}ms last latency`);
    }

    // Consistent pacing
    sleep(0.5);
}

export function handleSummary(data) {
    const durationMinutes = (data.state?.testRunDurationMs || 0) / 60000;

    const summary = {
        timestamp: new Date().toISOString(),
        test: 'soak-test',
        duration_minutes: durationMinutes.toFixed(2),
        results: {
            total_requests: data.metrics.http_reqs?.values?.count || 0,
            requests_per_minute: ((data.metrics.http_reqs?.values?.count || 0) / durationMinutes).toFixed(2),
            success_rate: ((1 - (data.metrics.http_req_failed?.values?.rate || 0)) * 100).toFixed(2) + '%',
            error_rate: ((data.metrics.http_req_failed?.values?.rate || 0) * 100).toFixed(4) + '%',
        },
        latency: {
            min: data.metrics.http_req_duration?.values?.min?.toFixed(2),
            avg: data.metrics.http_req_duration?.values?.avg?.toFixed(2),
            med: data.metrics.http_req_duration?.values?.med?.toFixed(2),
            p90: data.metrics.http_req_duration?.values?.['p(90)']?.toFixed(2),
            p95: data.metrics.http_req_duration?.values?.['p(95)']?.toFixed(2),
            p99: data.metrics.http_req_duration?.values?.['p(99)']?.toFixed(2),
            max: data.metrics.http_req_duration?.values?.max?.toFixed(2),
        },
        degradation_analysis: {
            note: 'Compare early vs late latency percentiles to detect degradation',
            p95_threshold: '1000ms',
            result: (data.metrics.http_req_duration?.values?.['p(95)'] || 0) < 1000 ? 'PASS' : 'FAIL',
        },
    };

    console.log('\n' + '='.repeat(60));
    console.log('SOAK TEST RESULTS');
    console.log('='.repeat(60));
    console.log(`Duration: ${summary.duration_minutes} minutes`);
    console.log(`Total Requests: ${summary.results.total_requests}`);
    console.log(`Requests/minute: ${summary.results.requests_per_minute}`);
    console.log(`Success Rate: ${summary.results.success_rate}`);
    console.log(`P95 Latency: ${summary.latency.p95}ms`);
    console.log(`P99 Latency: ${summary.latency.p99}ms`);
    console.log(`Degradation Check: ${summary.degradation_analysis.result}`);
    console.log('='.repeat(60));

    return {
        'results/soak-summary.json': JSON.stringify(summary, null, 2),
    };
}
