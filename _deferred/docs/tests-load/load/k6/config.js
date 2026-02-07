/**
 * NatLangChain Load Test Configuration
 *
 * Shared configuration for k6 load tests.
 */

// Environment configuration
export const config = {
    // Base URL - override with K6_BASE_URL env var
    baseUrl: __ENV.K6_BASE_URL || 'http://localhost:5000',

    // API Key - override with K6_API_KEY env var
    apiKey: __ENV.K6_API_KEY || 'test-api-key',

    // Thresholds based on SLA requirements
    thresholds: {
        // Response time thresholds
        http_req_duration: ['p(95)<500', 'p(99)<2000'],  // 95th < 500ms, 99th < 2s

        // Error rate threshold
        http_req_failed: ['rate<0.01'],  // Less than 1% errors

        // Throughput (requests per second)
        http_reqs: ['rate>100'],  // At least 100 RPS
    },

    // TPS targets for comparison
    tpsTargets: {
        baseline: 100,      // Minimum acceptable TPS
        target: 500,        // Target TPS
        stretch: 1000,      // Stretch goal TPS
        solanaComparison: 65000,  // Solana's claimed TPS (for reference)
    },
};

// Common headers
export function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'X-API-Key': config.apiKey,
    };
}

// Generate random entry content
export function generateEntry() {
    const intents = [
        'Record a transaction',
        'Log an agreement',
        'Document a decision',
        'Register an event',
        'Capture a statement',
    ];

    const contents = [
        'This is a test entry for load testing purposes.',
        'Recording performance metrics under stress.',
        'Validating throughput capacity of the system.',
        'Testing concurrent entry creation.',
        'Measuring latency under high load.',
    ];

    return {
        content: contents[Math.floor(Math.random() * contents.length)] + ' ' + Date.now(),
        author: `loadtest-user-${Math.floor(Math.random() * 1000)}`,
        intent: intents[Math.floor(Math.random() * intents.length)],
        metadata: {
            test_run: __ENV.K6_TEST_RUN || 'default',
            timestamp: new Date().toISOString(),
        },
        validate: false,  // Skip LLM validation for pure throughput tests
        auto_mine: false,
    };
}

// Generate search query
export function generateSearchQuery() {
    const queries = [
        'transaction record',
        'agreement terms',
        'performance metrics',
        'system validation',
        'throughput test',
    ];
    return queries[Math.floor(Math.random() * queries.length)];
}

export default config;
