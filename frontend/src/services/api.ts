import axios, { AxiosError } from 'axios'
import { useStore } from '@/store/useStore'
import { toast } from '@/components/Toaster'

const api = axios.create({
  baseURL: '/api',
})

// Add a request interceptor to include the JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Add a response interceptor to sync credits and handle common errors
api.interceptors.response.use(
  (response) => {
    // Sync Credits from Body (Standardized Envelope)
    const creditsFromBody = response.data?.data?.credits || response.data?.credits
    if (typeof creditsFromBody === 'number') {
      useStore.getState().setCredits(creditsFromBody)
    }

    // Sync Credits from Header (X-Updated-Credits)
    const creditsFromHeader = response.headers['x-updated-credits']
    if (creditsFromHeader) {
      const newCredits = parseInt(creditsFromHeader, 10)
      const oldCredits = useStore.getState().user?.credits
      if (oldCredits !== undefined && newCredits < oldCredits) {
        toast({ 
          title: `-${oldCredits - newCredits} CREDITS`, 
          description: 'Neural operation cost deducted.', 
          type: 'credit' 
        })
      }
      useStore.getState().setCredits(newCredits)
    }

    return response
  },
  async (error) => {
    // Handle 402 Insufficient Credits
    if (error.response?.status === 402) {
      const msg = error.response?.data?.message || "Insufficient Neural Credits for this operation."
      console.warn('CREDIT_EXHAUSTION:', msg)
    }

    // --- Added Retry & Failure Recovery Logic ---
    const config = error.config;
    // Do not retry if it's explicitly disabled or missing config
    if (config) {
      if (typeof config.retryCount === 'undefined') {
        config.retryCount = 0;
      }
      
      // Retry up to 2 times for 500+ Internal Errors, 502 Bad Gateway, 503 Overload, or Network Drops
      const isRetryableError = !error.response || (error.response.status >= 500);
      if (isRetryableError && config.retryCount < 2) {
        config.retryCount += 1;
        const delay = config.retryCount * 2000; // Exponential backoff (2s, 4s)
        console.warn(`[Network] Retrying request (${config.retryCount}/2) in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return api(config);
      }
    }

    return Promise.reject(error)
  }
)

// Helper: when responseType is 'blob' but server returns a JSON error,
// parse the blob back into a readable error message.
async function readBlobError(err: AxiosError): Promise<string> {
  try {
    const blob = err.response?.data as Blob
    if (blob && blob.type?.includes('application/json')) {
      const text = await blob.text()
      const json = JSON.parse(text)
      return json.error || 'Server error'
    }
  } catch (_) {}
  return (err.response?.data as any)?.error || err.message || 'Unknown error'
}

export const stegoApi = {
  // --- Auth ---
  googleAuth: (data: { google_token: string }) => api.post('/auth/google', data),
  getCurrentUser: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),

  // --- Payment ---
  createRazorpayOrder: (amount_inr: number) => api.post('/razorpay/create-order', { amount_inr }),
  verifyPayment: (data: any) => api.post('/razorpay/verify-payment', data),

  // --- Core ---
  embed: async (formData: FormData) => {
    try {
      return await api.post('/embed', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
      })
    } catch (err: any) {
      const msg = await readBlobError(err)
      throw { ...err, message: msg, response: { ...err.response, data: { error: msg } } }
    }
  },

  getCapacity: (formData: FormData) =>
    api.post('/capacity', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  extract: async (formData: FormData) => {
    try {
      return await api.post('/extract', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
      })
    } catch (err: any) {
      const msg = await readBlobError(err)
      throw { ...err, message: msg, response: { ...err.response, data: { error: msg } } }
    }
  },

  analyze: (formData: FormData) =>
    api.post('/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  batch: async (formData: FormData) => {
    try {
      return await api.post('/batch', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
      })
    } catch (err: any) {
      const msg = await readBlobError(err)
      throw { ...err, message: msg, response: { ...err.response, data: { error: msg } } }
    }
  },

  batchAnalyze: (formData: FormData) =>
    api.post('/batch_analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  contact: (data: any) =>
    api.post('/contact', data, {
      headers: { 'Content-Type': 'application/json' },
    }),

  getMessages: () => api.get('/messages'),
  getAnalysisList: () => api.get('/analysis'),
  getFiles: () => api.get('/files'),
  getCredits: () => api.get('/credits'),
  getActivity: () => api.get('/activity'),
  getGlobalStats: () => api.get('/stats/global'),
  checkHealth: () => api.get('/health'),

  // --- Heatmap ---
  getDifferenceHeatmap: (formData: FormData) =>
    api.post('/heatmap/difference', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getGradCamHeatmap: (formData: FormData) =>
    api.post('/heatmap/gradcam', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

export default api
