import axios from 'axios';

const API_URL = 'https://upgraded-goldfish-7q5pq6q77jxhgwx-8000.app.github.dev';

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

  downloadReport: async (results: any) => {
    const response = await axios.post(`${API_URL}/compliance/generate-pdf`, {
        results: results
    }, { responseType: 'blob' });
    return response.data;
  }
};