/**
 * Stress Test
 *
 * Pushes the system beyond normal capacity to find breaking points.
 * Identifies maximum sustainable load and failure modes.
 *
 * Run: k6 run tests/load/k6/stress.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { config, getHeaders, generateEntry, generateSearchQuery } from './config.js';

// Custom metrics
const errorsByType = new Counter('errors_by_type');
const successRate = new Rate('overall_success_rate');
const recoveryTime = new Trend('recovery_time');

export const options = {
    scenarios: {
        // Stress ramp - push to breaking point
        stress_ramp: {
            executor: 'ramping-vus',
            startVUs: 10,
            stages: [
                { duration: '2m', target: 50 },    // Ramp to normal load
                { duration: '5m', target: 50 },   // Stay at normal
                { duration: '2m', target: 100 },  // Ramp to high load
                { duration: '5m', target: 100 },  // Stay at high
                { duration: '2m', target: 200 },  // Ramp to stress
                { duration: '5m', target: 200 },  // Stay at stress
                { duration: '2m', target: 300 },  // Push to breaking
                { duration: '5m', target: 300 },  // Hold at breaking
                { duration: '5m', target: 50 },   // Recovery phase
                { duration: '2m', target: 0 },    // Ramp down
            ],
        },
    },
    thresholds: {
        // More lenient thresholds for stress test
        'http_req_duration': ['p(95)<5000'],     // Allow up to 5s at P95
        'http_req_failed': ['rate<0.20'],        // Allow up to 20% errors at peak
        'overall_success_rate': ['rate>0.80'],   // At least 80% overall success
    },
};

export function setup() {
    const res = http.get(`${config.baseUrl}/health`);
    if (res.status !== 200) {
        throw new Error('API not accessible');
    }
    console.log('Starting stress test - will push system to breaking point');
    return { startTime: Date.now() };
}

export default function () {
    // Mix of operations to stress different components
    const operation = Math.random();

    if (operation < 0.4) {
        // 40% - Entry creation (write heavy)
        group('Write Operations', () => {
            const entry = generateEntry();
            const res = http.post(
                `${config.baseUrl}/entry`,
                JSON.stringify(entry),
                { headers: getHeaders() }
            );

            const success = check(res, {
                'entry created': (r) => r.status === 201 || r.status === 200,
            });
            successRate.add(success);

            if (!success) {
                errorsByType.add(1, { type: 'entry_creation', status: res.status });
            }
        });
    } else if (operation < 0.7) {
        // 30% - Read operations
        group('Read Operations', () => {
            const res = http.get(`${config.baseUrl}/chain`);
            const success = check(res, {
                'chain retrieved': (r) => r.status === 200,
            });
            successRate.add(success);

            if (!success) {
                errorsByType.add(1, { type: 'chain_read', status: res.status });
            }
        });
    } else if (operation < 0.9) {
        // 20% - Search operations
        group('Search Operations', () => {
            const query = generateSearchQuery();
            const res = http.get(`${config.baseUrl}/entries/search?q=${encodeURIComponent(query)}`);
            const success = check(res, {
                'search completed': (r) => r.status === 200,
            });
            successRate.add(success);

            if (!success) {
                errorsByType.add(1, { type: 'search', status: res.status });
            }
        });
    } else {
        // 10% - Validation operations
        group('Validation Operations', () => {
            const res = http.get(`${config.baseUrl}/validate/chain`);
            const success = check(res, {
                'validation completed': (r) => r.status === 200,
            });
            successRate.add(success);

            if (!success) {
                errorsByType.add(1, { type: 'validation', status: res.status });
            }
        });
    }

    sleep(0.1);
}

export function handleSummary(data) {
    const summary = {
        timestamp: new Date().toISOString(),
        test: 'stress-test',
        results: {
            total_requests: data.metrics.http_reqs?.values?.count || 0,
            success_rate: ((1 - (data.metrics.http_req_failed?.values?.rate || 0)) * 100).toFixed(2) + '%',
            peak_vus: data.metrics.vus_max?.values?.max || 0,
            max_latency: data.metrics.http_req_duration?.values?.max?.toFixed(2) || 'N/A',
            p95_latency: data.metrics.http_req_duration?.values?.['p(95)']?.toFixed(2) || 'N/A',
            p99_latency: data.metrics.http_req_duration?.values?.['p(99)']?.toFixed(2) || 'N/A',
        },
        breaking_point_analysis: {
            note: 'Review p99 latency and error rate at different VU levels',
            recommendation: 'Maximum sustainable VUs = peak_vus * (1 - error_rate)',
        },
    };

    console.log('\n' + '='.repeat(60));
    console.log('STRESS TEST RESULTS');
    console.log('='.repeat(60));
    console.log(`Total Requests: ${summary.results.total_requests}`);
    console.log(`Success Rate: ${summary.results.success_rate}`);
    console.log(`Peak VUs: ${summary.results.peak_vus}`);
    console.log(`P95 Latency: ${summary.results.p95_latency}ms`);
    console.log(`P99 Latency: ${summary.results.p99_latency}ms`);
    console.log(`Max Latency: ${summary.results.max_latency}ms`);
    console.log('='.repeat(60));

    return {
        'results/stress-summary.json': JSON.stringify(summary, null, 2),
    };
}
