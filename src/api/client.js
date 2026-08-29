/**
 * API Client - Block 2 (Assistant 1)
 * Centralized HTTP client for backend communication
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  const config = {
    headers: {
      'Accept': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  // Add auth token if available
  const token = localStorage.getItem('token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
    if (options.body && typeof options.body === 'object') {
      config.body = JSON.stringify(options.body);
    }
  }

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

/**
 * Ticket API endpoints
 */
export const ticketsAPI = {
  /**
   * Submit a new grievance ticket with photo
   */
  submit: async (formData) => {
    return fetchAPI('/api/tickets/submit', {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * Get list of tickets
   */
  list: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return fetchAPI(`/api/tickets/list?${queryString}`);
  },

  /**
   * Get single ticket details
   */
  get: async (id) => {
    return fetchAPI(`/api/tickets/${id}`);
  },
};

/**
 * Triage API endpoints
 */
export const triageAPI = {
  /**
   * Run triage with budget and workforce constraints
   */
  run: async (dailyBudget, dailyWorkforce, wardId = null) => {
    const body = {
      daily_budget: dailyBudget,
      daily_workforce: dailyWorkforce,
    };
    if (wardId) body.ward_id = wardId;

    return fetchAPI('/api/triage/run', {
      method: 'POST',
      body,
    });
  },

  /**
   * Get today's dispatch manifest
   */
  getToday: async () => {
    return fetchAPI('/api/triage/today');
  },

  /**
   * Get dispatch manifest for specific date
   */
  getManifest: async (date) => {
    return fetchAPI(`/api/triage/manifest/${date}`);
  },

  /**
   * Get tickets sorted by priority
   */
  getPriorities: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return fetchAPI(`/api/triage/priorities?${queryString}`);
  },
};

/**
 * Health check
 */
export const healthAPI = {
  check: async () => {
    return fetchAPI('/health');
  },
};

export default {
  tickets: ticketsAPI,
  triage: triageAPI,
  health: healthAPI,
};
