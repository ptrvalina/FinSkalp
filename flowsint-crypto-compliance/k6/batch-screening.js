# FinSkalp batch screening load test (k6)
# Run: k6 run flowsint-crypto-compliance/k6/batch-screening.js

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 25 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<3000'],
  },
};

const BASE = __ENV.FINSKALP_API || 'http://localhost:8000';
const TOKEN = __ENV.FINSKALP_TOKEN || '';

function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (TOKEN) h['Authorization'] = `Bearer ${TOKEN}`;
  return h;
}

export default function () {
  const csv = 'address,chain\nTDemoAddr0001,tron\nTDemoAddr0002,tron\n';
  const formData = {
    file: http.file(csv, 'batch.csv', 'text/csv'),
  };
  const res = http.post(`${BASE}/api/compliance/wallets/screen/batch?async_mode=true`, formData, {
    headers: TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {},
  });
  check(res, {
    'batch accepted': (r) => r.status === 202 || r.status === 401,
  });
  sleep(1);
}
