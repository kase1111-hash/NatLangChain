/**
 * Smoke Test
 *
 * Quick sanity check to verify the system is working.
 * Run: k6 run tests/load/k6/smoke.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { config, getHeaders } from './config.js';

export const options = {
    vus: 1,
    duration: '30s',
    thresholds: {
        http_req_duration: ['p(95)<1000'],
        http_req_failed: ['rate<0.05'],
    },
};

export default function () {
    // Health check
    const healthRes = http.get(`${config.baseUrl}/health`);
    check(healthRes, {
        'health check status 200': (r) => r.status === 200,
        'health check has status': (r) => JSON.parse(r.body).status !== undefined,
    });

    // Get chain
    const chainRes = http.get(`${config.baseUrl}/chain`);
    check(chainRes, {
        'chain status 200': (r) => r.status === 200,
        'chain has blocks': (r) => JSON.parse(r.body).chain !== undefined,
    });

    // Get stats
    const statsRes = http.get(`${config.baseUrl}/stats`);
    check(statsRes, {
        'stats status 200': (r) => r.status === 200,
    });

    // Validate chain
    const validateRes = http.get(`${config.baseUrl}/validate/chain`);
    check(validateRes, {
        'validate status 200': (r) => r.status === 200,
        'chain is valid': (r) => JSON.parse(r.body).valid === true,
    });

    sleep(1);
}

export function handleSummary(data) {
    return {
        'results/smoke-summary.json': JSON.stringify(data, null, 2),
    };
}
