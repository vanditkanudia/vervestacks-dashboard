import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL;

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle common errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API functions
export const authAPI = {
  login: async (credentials) => {
    const response = await api.post('/auth/login', credentials);
    return response.data;
  },
  
  register: async (userData) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },
};

// Countries API functions
export const countriesAPI = {
  getAll: async () => {
    const response = await api.get('/countries');
    return response.data;
  },
  
  getWithModels: async () => {
    const response = await api.get('/countries/with-models');
    return response.data;
  },
  
  getByIso: async (isoCode) => {
    const response = await api.get(`/countries/${isoCode}`);
    return response.data;
  },
  
  getByRegion: async (region) => {
    const response = await api.get(`/countries/region/${region}`);
    return response.data;
  },
};

// Capacity API functions
export const capacityAPI = {
  getCapacityByFuel: async (isoCode, year) => {
    const response = await api.get(`/capacity/capacity-by-fuel/${isoCode}/${year}`);
    return response.data;
  },
  
  getCapacityUtilization: async (isoCode, year = 2022) => {
    const response = await api.get(`/overview/capacity-utilization/${isoCode}?year=${year}`);
    return response.data;
  },

  // Fuel Colors API
  async getFuelColors() {
    const response = await api.get('/capacity/fuel-colors');
    return response.data;
  }
};

// Energy Metrics API functions
export const energyMetricsAPI = {
  getEnergyMetrics: async (isoCode) => {
    const response = await api.get(`/overview/energy-metrics/${isoCode}`);
    return response.data;
  },
  getExistingStockMetrics: async (isoCode) => {
    const response = await api.get(`/overview/existing-stock/${isoCode}`);
    return response.data;
  },
  getAr6ScenarioDrivers: async (isoCode) => {
    const response = await api.get(`/overview/ar6-scenario/${isoCode}`);
    return response.data;
  },
};

// Health check
export const healthCheck = async () => {
  const response = await axios.get(`${API_BASE_URL.replace('/api', '')}/health`);
  return response.data;
};

// Renewable Potential API
export const renewablePotentialAPI = {
  getSolarZones: async (isoCode) => {
    const response = await axios.get(`${API_BASE_URL}/renewable-potential/solar-zones/${isoCode}`);
    return response.data;
  },
  getWindZones: async (isoCode, windType = 'onshore') => {
    const response = await axios.get(`${API_BASE_URL}/renewable-potential/wind-zones/${isoCode}?wind_type=${windType}`);
    return response.data;
  },
  
  healthCheck: async () => {
    const response = await axios.get(`${API_BASE_URL}/renewable-potential/health`);
    return response.data;
  }
};

// Transmission API
export const transmissionAPI = {
  getTransmissionData: async (isoCode, clusters = null) => {
    const url = clusters 
      ? `${API_BASE_URL}/transmission/data/${isoCode}?clusters=${clusters}`
      : `${API_BASE_URL}/transmission/data/${isoCode}`;
    const response = await axios.get(url);
    return response.data;
  },
  
  getTransmissionNetworkData: async (isoCode) => {
    const response = await axios.get(`${API_BASE_URL}/transmission/network/${isoCode}`);
    return response.data;
  },
  
  getTransmissionGenerationData: async (isoCode) => {
    const response = await axios.get(`${API_BASE_URL}/transmission/generation/${isoCode}`);
    return response.data;
  },
  
  healthCheck: async () => {
    const response = await axios.get(`${API_BASE_URL}/transmission/health`);
    return response.data;
  }
};

// Generation Profile (Hourly by fuel)
export const generationProfileAPI = {
  getSolarHourly: async (isoCode, year, capacityGw) => {
    const response = await api.get(`/generation-profile/solar-hourly`, {
      params: { isoCode, year, capacityGw },
      timeout: 120000
    });
    return response.data;
  },
  getWindHourly: async (isoCode, year, capacityGw) => {
    const response = await api.get(`/generation-profile/wind-hourly`, {
      params: { isoCode, year, capacityGw },
      timeout: 120000
    });
    return response.data;
  },
  getWindOffHourly: async (isoCode, year, capacityGw) => {
    const response = await api.get(`/generation-profile/windoff-hourly`, {
      params: { isoCode, year, capacityGw },
      timeout: 120000
    });
    return response.data;
  }
};

export default api;
