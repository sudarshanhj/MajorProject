import http from 'k6/http';
import { check, sleep } from 'k6';
import { FormData } from 'https://jslib.k6.io/formdata/0.0.2/index.js';

export const options = {
    stages: [
        { duration: '5s', target: 200 },   // Fast ramp up
        { duration: '10s', target: 500 },  // Peak 500 users
        { duration: '5s', target: 0 },     // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<3000'], // 95% of responses below 3s
        http_req_failed: ['rate<0.05'],    // Allow 5% error at massive scale
    },
};

const BASE_URL = 'http://127.0.0.1:5005/api';
// Use ENV token, else fallback
const TOKEN = __ENV.JWT_TOKEN || 'YOUR_TEST_JWT_TOKEN_HERE';

export default function () {
    // 1. Test Health Endpoint
    const healthRes = http.get(`${BASE_URL}/health`);
    check(healthRes, { 'Health Check is 200': (r) => r.status === 200 });
    
    // 2. Simulate File Upload (Stateless architecture test)
    // For heavy load testing, embed realistic payloads 
    const payloadBuffer = new ArrayBuffer(500 * 1024); // 500KB fake image payload per user
    const fd = new FormData();
    fd.append('cover', http.file(payloadBuffer, 'cover.png', 'image/png'));
    fd.append('secret', http.file('secret_data_string_for_load_testing_at_500_users', 'secret.txt', 'text/plain'));
    fd.append('method', 'LSB');
    
    const embedRes = http.post(`${BASE_URL}/embed`, fd.body(), {
        headers: { 
            'Content-Type': `multipart/form-data; boundary=${fd.boundary}`,
            'Authorization': `Bearer ${TOKEN}`
        },
    });
    
    check(embedRes, {
        'Embed returned 200': (r) => r.status === 200,
        'Response time < 3s': (r) => r.timings.duration < 3000
    });

    sleep(1);
}
