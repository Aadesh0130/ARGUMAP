import test from 'node:test';
import assert from 'node:assert/strict';

// Test resolveApiBaseUrl logic matching frontend/src/lib/api.ts
function resolveApiBaseUrl(customUrl) {
  const envUrl = customUrl;

  if (!envUrl || typeof envUrl !== 'string' || !envUrl.trim()) {
    return 'http://localhost:8000/api';
  }

  let cleaned = envUrl.trim();

  // 1. Strip query parameters (?...) and hash fragments (#...)
  cleaned = cleaned.split('?')[0].split('#')[0].trim();

  // 2. Strip trailing slashes
  cleaned = cleaned.replace(/\/+$/, '');

  if (!cleaned) {
    return 'http://localhost:8000/api';
  }

  // 3. Prepend protocol if omitted
  if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://') && !cleaned.startsWith('/')) {
    if (cleaned.startsWith('localhost') || cleaned.startsWith('127.0.0.1')) {
      cleaned = `http://${cleaned}`;
    } else {
      cleaned = `https://${cleaned}`;
    }
  }

  // 4. Deduplicate any repeated /api at the end
  while (cleaned.endsWith('/api/api')) {
    cleaned = cleaned.slice(0, -4);
  }

  // 5. Ensure it ends with /api
  if (!cleaned.endsWith('/api')) {
    cleaned = `${cleaned}/api`;
  }

  return cleaned;
}

function buildApiUrl(endpoint, base) {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${base}${normalizedEndpoint}`;
}

test('fallback to localhost in development when URL is empty or undefined', () => {
  assert.equal(resolveApiBaseUrl(undefined), 'http://localhost:8000/api');
  assert.equal(resolveApiBaseUrl(''), 'http://localhost:8000/api');
  assert.equal(resolveApiBaseUrl('   '), 'http://localhost:8000/api');
});

test('handles production Render URL with and without trailing slash', () => {
  assert.equal(resolveApiBaseUrl('https://argumap-api.onrender.com'), 'https://argumap-api.onrender.com/api');
  assert.equal(resolveApiBaseUrl('https://argumap-api.onrender.com/'), 'https://argumap-api.onrender.com/api');
  assert.equal(resolveApiBaseUrl('https://argumap-api.onrender.com/api'), 'https://argumap-api.onrender.com/api');
  assert.equal(resolveApiBaseUrl('https://argumap-api.onrender.com/api/'), 'https://argumap-api.onrender.com/api');
  assert.equal(resolveApiBaseUrl('https://argumap-api.onrender.com///'), 'https://argumap-api.onrender.com/api');
});

test('strips tracking query parameters and prevents duplicate /api', () => {
  // The exact issue reported: https://argumap-api.onrender.com/api?utm_source=chatgpt.com/api
  assert.equal(
    resolveApiBaseUrl('https://argumap-api.onrender.com/api?utm_source=chatgpt.com/api'),
    'https://argumap-api.onrender.com/api'
  );
  assert.equal(
    resolveApiBaseUrl('https://argumap-api.onrender.com/api?utm_source=chatgpt.com'),
    'https://argumap-api.onrender.com/api'
  );
  assert.equal(
    resolveApiBaseUrl('https://argumap-api.onrender.com?utm_source=chatgpt.com'),
    'https://argumap-api.onrender.com/api'
  );
  assert.equal(
    resolveApiBaseUrl('https://argumap-api.onrender.com/api/api'),
    'https://argumap-api.onrender.com/api'
  );
  assert.equal(
    resolveApiBaseUrl('https://argumap-api.onrender.com/api#section'),
    'https://argumap-api.onrender.com/api'
  );
});

test('constructs API endpoint paths cleanly', () => {
  const base = resolveApiBaseUrl('https://argumap-api.onrender.com/api?utm_source=chatgpt.com/api');
  assert.equal(buildApiUrl('/analyze', base), 'https://argumap-api.onrender.com/api/analyze');
  assert.equal(buildApiUrl('analyze', base), 'https://argumap-api.onrender.com/api/analyze');
  assert.equal(buildApiUrl('/health', base), 'https://argumap-api.onrender.com/api/health');
  assert.equal(buildApiUrl('/speak', base), 'https://argumap-api.onrender.com/api/speak');
  assert.equal(buildApiUrl('/analysis/uuid-456', base), 'https://argumap-api.onrender.com/api/analysis/uuid-456');
});
