import axios from 'axios';

const API_URL = 'https://upgraded-goldfish-7q5pq6q77jxhgwx-8000.app.github.dev';

export const AuditService = {
  // Updated: Accepts userMetrics list
  analyzeRisk: async (description: string, userMetrics: string[] = []) => {
    const response = await axios.post(`${API_URL}/compliance/risk-assessment`, { 
      description,
      user_metrics: userMetrics
    });
    return response.data;
  },

  // Updated: Accepts modelName
  runAudit: async (apiKey: string, risks: string[], modelName: string) => {
    const response = await axios.post(`${API_URL}/audit/run-bias-test`, {
      api_key: apiKey,
      selected_risks: risks,
      model_name: modelName
    });
    return response.data;
  },

  getHistory: async () => {
    const response = await axios.get(`${API_URL}/audit/history`);
    return response.data;
  },

  downloadReport: async (results: any) => {
    const response = await axios.post(`${API_URL}/compliance/generate-pdf`, {
        results: results
    }, { responseType: 'blob' });
    return response.data;
  }
};