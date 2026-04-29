export declare const AuditService: {
    analyzeRisk: (description: string, userMetrics?: string[]) => Promise<any>;
    runAudit: (apiKey: string, risks: string[], modelName: string, riskLevel: string, userId: string | undefined, systemPrompt: string) => Promise<any>;
    getHistory: (userId?: string) => Promise<any>;
    downloadReport: (results: Record<string, unknown>) => Promise<any>;
};
export declare const GovernanceService: {
    startInterview: (name: string, description: string, getToken?: () => Promise<string | null>) => Promise<any>;
    sendMessage: (projectId: number, message: string, workflowId?: number | null, getToken?: () => Promise<string | null>) => Promise<any>;
    listProjects: (getToken?: () => Promise<string | null>) => Promise<any>;
    getProject: (projectId: number, getToken?: () => Promise<string | null>) => Promise<any>;
    generateReport: (projectId: number, getToken?: () => Promise<string | null>) => Promise<any>;
};
export declare const DashboardService: {
    getStats: (getToken?: () => Promise<string | null>) => Promise<any>;
};
