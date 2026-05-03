export declare const AuditService: {
    analyzeRisk: (description: string, userMetrics?: string[]) => Promise<unknown>;
    runAudit: (apiKey: string, risks: string[], modelName: string, riskLevel: string, userId: string | undefined, systemPrompt: string) => Promise<unknown>;
    getHistory: (userId?: string) => Promise<unknown>;
    downloadReport: (results: Record<string, unknown>) => Promise<unknown>;
};
export declare const GovernanceService: {
    startInterview: (name: string, description: string, getToken?: () => Promise<string | null>) => Promise<unknown>;
    sendMessage: (projectId: number, message: string, workflowId?: number | null, getToken?: () => Promise<string | null>) => Promise<unknown>;
    listProjects: (getToken?: () => Promise<string | null>) => Promise<unknown>;
    getProject: (projectId: number, getToken?: () => Promise<string | null>) => Promise<unknown>;
    generateReport: (projectId: number, getToken?: () => Promise<string | null>) => Promise<unknown>;
};
export declare const DashboardService: {
    getStats: (getToken?: () => Promise<string | null>) => Promise<unknown>;
};
