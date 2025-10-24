import axios from 'axios';

const API_URL = 'http://localhost:5000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const consulAPI = {
  // Nodes
  getNodes: () => api.get('/nodes'),

  // Services
  getServices: (nodeAddr?: string) =>
    api.get('/services', { params: { node_addr: nodeAddr } }),

  createService: (serviceData: any) =>
    api.post('/services/', serviceData),

  deleteService: (serviceId: string) =>
    api.delete(`/services/${serviceId}`),

  // Health
  getHealthStatus: () => api.get('/health/status'),
};

export default api;