import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "./../components/ui/card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { ShieldAlert, CheckCircle, Activity, FileText } from "lucide-react";
import { AuditService } from "./../services/api";

export function Dashboard() {
  const [stats, setStats] = useState({
    totalAudits: 0,
    avgScore: 0,
    criticalRisks: 0,
    recentActivity: [] as any[],
    chartData: [] as any[]
  });

  useEffect(() => {
    async function loadDashboardData() {
      try {
        const history = await AuditService.getHistory();
        
        if (history.length === 0) return;

        // 1. Calculate Stats from REAL Database History
        const total = history.length;
        const avg = Math.round(history.reduce((acc: number, curr: any) => acc + curr.compliance_score, 0) / total);
        const risks = history.filter((h: any) => h.status === "NON_COMPLIANT").length;
        
        // 2. Get Chart Data from the MOST RECENT run
        const latestRun = history[0];
        // If metric_scores exists (new DB format), use it. Otherwise use placeholder.
        const chartData = latestRun.metric_scores && latestRun.metric_scores.length > 0
          ? latestRun.metric_scores 
          : [{ name: 'Overall', score: latestRun.compliance_score }];

        setStats({
          totalAudits: total,
          avgScore: avg,
          criticalRisks: risks,
          recentActivity: history.slice(0, 5), // Top 5 recent
          chartData: chartData
        });
      } catch (e) {
        console.error("Failed to load dashboard data");
      }
    }
    loadDashboardData();
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-2">Real-time overview of AI compliance metrics.</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard title="Total Audits" value={stats.totalAudits} icon={Activity} color="text-blue-600" />
        <StatsCard title="Avg. Fairness Score" value={`${stats.avgScore}%`} icon={CheckCircle} color={stats.avgScore > 80 ? "text-emerald-600" : "text-yellow-600"} />
        <StatsCard title="Failed Audits" value={stats.criticalRisks} icon={ShieldAlert} color={stats.criticalRisks > 0 ? "text-red-600" : "text-slate-600"} />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Latest Audit Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              {stats.chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.chartData}>
                    <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis domain={[0, 100]} fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{fill: 'transparent'}} />
                    <Bar dataKey="score" fill="#2563eb" radius={[4, 4, 0, 0]} barSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-slate-400">No Data Available</div>
              )}
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {stats.recentActivity.map((run) => (
                <div key={run.id} className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center">
                      <FileText className="h-5 w-5 text-slate-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-900">Audit Run #{run.id}</p>
                      <p className="text-xs text-slate-500">{new Date(run.timestamp).toLocaleDateString()} • {run.model_name}</p>
                    </div>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    run.status === "COMPLIANT" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                  }`}>
                    {run.status}
                  </span>
                </div>
              ))}
               {stats.totalAudits === 0 && <p className="text-slate-500 text-sm">No audits run yet.</p>}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatsCard({ title, value, icon: Icon, color }: any) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-slate-500">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${color}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-slate-900">{value}</div>
      </CardContent>
    </Card>
  )
}