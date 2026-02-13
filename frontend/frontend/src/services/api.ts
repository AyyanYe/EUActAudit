import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper to get auth headers - accepts getToken function from useAuth hook
const getAuthHeaders = async (getToken?: () => Promise<string | null>): Promise<Record<string, string>> => {
  if (!getToken) {
    console.warn('getToken function not provided');
    return {};
  }

  try {
    // Add timeout to prevent hanging
    const tokenPromise = getToken();
    const timeoutPromise = new Promise<null>((resolve) =>
      setTimeout(() => resolve(null), 5000)
    );

    const token = await Promise.race([tokenPromise, timeoutPromise]);

    if (token) {
      return { Authorization: `Bearer ${token}` };
    } else {
      console.warn('No token received or timeout');
    }
  } catch (e) {
    console.warn('Failed to get auth token:', e);
  }
  return {};
};

export const AuditService = {
  analyzeRisk: async (description: string, userMetrics: string[] = []) => {
    const response = await axios.post(`${API_URL}/compliance/risk-assessment`, {
      description,
      user_metrics: userMetrics
    });
    return response.data;
  },

  // ✅ UPDATED: Now accepts userId AND systemPrompt
  runAudit: async (
    apiKey: string,
    risks: string[],
    modelName: string,
    riskLevel: string,
    userId: string = "anonymous",
    systemPrompt: string // <--- NEW ARGUMENT
  ) => {
    const response = await axios.post(`${API_URL}/audit/run-bias-test`, {
      api_key: apiKey,
      selected_risks: risks,
      model_name: modelName,
      risk_level: riskLevel,
      user_id: userId,
      system_prompt: systemPrompt // <--- Send to backend as the "Persona"
    });
    return response.data;
  },

  // Updated: Now accepts userId to filter history
  getHistory: async (userId: string = "") => {
    const response = await axios.get(`${API_URL}/audit/history`, {
      params: { user_id: userId }
    });
    return response.data;
  },

  downloadReport: async (results: Record<string, unknown>) => {
    const response = await axios.post(`${API_URL}/compliance/generate-pdf`, {
      results: results
    }, { responseType: 'blob' });
    return response.data;
  }
};

export const GovernanceService = {
  // 1. Start a new Profile
  startInterview: async (name: string, description: string, getToken?: () => Promise<string | null>) => {
    const headers = await getAuthHeaders(getToken);
    const response = await axios.post(`${API_URL}/interview/start`, {
      name,
      description
    }, {
      headers,
      timeout: 10000 // 10 second timeout
    });
    return response.data; // Returns { project_id, message, state, confidence }
  },

  // 2. Send Message & Get Updated State
  sendMessage: async (projectId: number, message: string, workflowId?: number | null, getToken?: () => Promise<string | null>) => {
    const headers = await getAuthHeaders(getToken);
    const response = await axios.post(`${API_URL}/interview/chat`, {
      project_id: projectId,
      message: message,
      workflow_id: workflowId || null
    }, { headers, timeout: 10000 });
    return response.data; // Returns { response, risk_level, facts, obligations, state, confidence, state_description }
  },

  // 3. List all projects for the user
  listProjects: async (getToken?: () => Promise<string | null>) => {
    const headers = await getAuthHeaders(getToken);
    const response = await axios.get(`${API_URL}/interview/projects`, { headers });
    return response.data; // Returns { projects: [...] }
  },

  // 4. Get a specific project with full chat history
  getProject: async (projectId: number, getToken?: () => Promise<string | null>) => {
    const headers = await getAuthHeaders(getToken);
    const response = await axios.get(`${API_URL}/interview/projects/${projectId}`, { headers });
    return response.data; // Returns { project, messages, facts, obligations }
  },

  // 5. Generate and download PDF report
  generateReport: async (projectId: number, getToken?: () => Promise<string | null>) => {
    const headers = await getAuthHeaders(getToken);
    const response = await axios.post(
      `${API_URL}/interview/projects/${projectId}/generate-report`,
      {},
      {
        headers,
        responseType: 'blob'
      }
    );

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `compliance_report_${projectId}_${new Date().toISOString().split('T')[0]}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    return response.data;
  }
};