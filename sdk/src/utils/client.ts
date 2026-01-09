/**
 * HTTP Client for NatLangChain SDK
 *
 * Provides a robust HTTP client with retry logic, error handling,
 * and automatic header management.
 */

import type { NatLangChainConfig, ApiError } from '../types';

/** HTTP methods supported by the client */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

/** Response wrapper */
export interface HttpResponse<T> {
  data: T;
  status: number;
  headers: Headers;
}

/** SDK-specific error class */
export class NatLangChainError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly apiError?: ApiError
  ) {
    super(message);
    this.name = 'NatLangChainError';
  }
}

/** Network error class */
export class NetworkError extends Error {
  constructor(
    message: string,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'NetworkError';
  }
}

/**
 * HTTP Client class with retry logic and error handling
 */
export class HttpClient {
  private readonly endpoint: string;
  private readonly apiKey?: string;
  private readonly timeout: number;
  private readonly headers: Record<string, string>;
  private readonly retryAttempts: number;
  private readonly retryDelay: number;
  private readonly retryMaxDelay: number;

  constructor(config: NatLangChainConfig) {
    this.endpoint = config.endpoint.replace(/\/$/, ''); // Remove trailing slash
    this.apiKey = config.apiKey;
    this.timeout = config.timeout ?? 30000;
    this.headers = config.headers ?? {};
    this.retryAttempts = config.retry?.attempts ?? 3;
    this.retryDelay = config.retry?.delay ?? 1000;
    this.retryMaxDelay = config.retry?.maxDelay ?? 10000;
  }

  /**
   * Build the full URL for a request
   */
  private buildUrl(path: string, params?: Record<string, string | number>): string {
    const url = new URL(path, this.endpoint);

    if (params) {
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      }
    }

    return url.toString();
  }

  /**
   * Build request headers
   */
  private buildHeaders(additionalHeaders?: Record<string, string>): Headers {
    const headers = new Headers({
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...this.headers,
      ...additionalHeaders,
    });

    if (this.apiKey) {
      headers.set('X-API-Key', this.apiKey);
    }

    return headers;
  }

  /**
   * Sleep for a given duration
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Calculate retry delay with exponential backoff
   */
  private calculateRetryDelay(attempt: number): number {
    const delay = this.retryDelay * Math.pow(2, attempt);
    return Math.min(delay, this.retryMaxDelay);
  }

  /**
   * Check if an error is retryable
   */
  private isRetryable(status: number): boolean {
    // Retry on server errors and rate limiting
    return status >= 500 || status === 429;
  }

  /**
   * Make an HTTP request with retry logic
   */
  async request<T>(
    method: HttpMethod,
    path: string,
    options?: {
      body?: unknown;
      params?: Record<string, string | number>;
      headers?: Record<string, string>;
    }
  ): Promise<HttpResponse<T>> {
    const url = this.buildUrl(path, options?.params);
    const headers = this.buildHeaders(options?.headers);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    const requestInit: RequestInit = {
      method,
      headers,
      signal: controller.signal,
    };

    if (options?.body && method !== 'GET') {
      requestInit.body = JSON.stringify(options.body);
    }

    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= this.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, requestInit);

        clearTimeout(timeoutId);

        // Handle non-2xx responses
        if (!response.ok) {
          let apiError: ApiError | undefined;

          try {
            apiError = await response.json() as ApiError;
          } catch {
            // Response body is not JSON
          }

          // Check if we should retry
          if (this.isRetryable(response.status) && attempt < this.retryAttempts) {
            const delay = this.calculateRetryDelay(attempt);
            await this.sleep(delay);
            continue;
          }

          throw new NatLangChainError(
            apiError?.error ?? `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            apiError
          );
        }

        // Parse successful response
        const contentType = response.headers.get('content-type');

        let data: T;
        if (contentType?.includes('application/json')) {
          data = await response.json() as T;
        } else if (contentType?.includes('text/plain')) {
          data = await response.text() as T;
        } else {
          data = await response.json() as T;
        }

        return {
          data,
          status: response.status,
          headers: response.headers,
        };
      } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof NatLangChainError) {
          throw error;
        }

        // Handle network errors
        if (error instanceof Error) {
          if (error.name === 'AbortError') {
            throw new NetworkError(`Request timeout after ${this.timeout}ms`);
          }

          lastError = error;

          // Retry on network errors
          if (attempt < this.retryAttempts) {
            const delay = this.calculateRetryDelay(attempt);
            await this.sleep(delay);
            continue;
          }
        }

        throw new NetworkError(
          `Network request failed: ${lastError?.message ?? 'Unknown error'}`,
          lastError
        );
      }
    }

    throw new NetworkError(
      `Request failed after ${this.retryAttempts} retries`,
      lastError
    );
  }

  /**
   * GET request
   */
  async get<T>(
    path: string,
    params?: Record<string, string | number>,
    headers?: Record<string, string>
  ): Promise<T> {
    const response = await this.request<T>('GET', path, { params, headers });
    return response.data;
  }

  /**
   * POST request
   */
  async post<T>(
    path: string,
    body?: unknown,
    headers?: Record<string, string>
  ): Promise<T> {
    const response = await this.request<T>('POST', path, { body, headers });
    return response.data;
  }

  /**
   * PUT request
   */
  async put<T>(
    path: string,
    body?: unknown,
    headers?: Record<string, string>
  ): Promise<T> {
    const response = await this.request<T>('PUT', path, { body, headers });
    return response.data;
  }

  /**
   * DELETE request
   */
  async delete<T>(
    path: string,
    headers?: Record<string, string>
  ): Promise<T> {
    const response = await this.request<T>('DELETE', path, { headers });
    return response.data;
  }
}
