import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "./../components/ui/card";
import { Badge } from "./../components/ui/badge";
import { Progress } from "./../components/ui/progress";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area, CartesianGrid, Legend,
} from 'recharts';
import {
  ShieldCheck, ShieldAlert, Activity, FileText, Scale, AlertTriangle,
  ArrowUpRight, Clock, CheckCircle2, XCircle, Layers,
} from "lucide-react";
import { DashboardService } from "./../services/api";
import { useAuth } from "@clerk/clerk-react";

// ── Color palette ───────────────────────────────────────────────────────
const RISK_COLORS: Record<string, string> = {
  Prohibited: "#dc2626",
  High: "#f97316",
  Limited: "#eab308",
  Minimal: "#22c55e",
  Pending: "#94a3b8",
};

const STATUS_COLORS = {
  met: "#22c55e",
  unmet: "#ef4444",
  pending: "#94a3b8",
  gap: "#f97316",
  review: "#eab308",
  planned: "#3b82f6",
};

// ── Types ───────────────────────────────────────────────────────────────
interface DashboardData {
  summary: {
    total_assessments: number;
    active_assessments: number;
    completed_assessments: number;
    high_risk_count: number;
    compliance_rate: number;
    total_obligations: number;
  };
  risk_distribution: { name: string; value: number }[];
  obligation_breakdown: {
    code: string; title: string;
    met: number; unmet: number; pending: number;
    gap: number; review: number; planned: number;
  }[];
  recent_projects: {
    id: number; name: string; description: string;
    risk_level: string; status: string; state: string;
    updated_at: string | null;
    obligation_count: number; met_count: number; progress: number;
  }[];
  top_gaps: { code: string; title: string; count: number }[];
  activity_timeline: { date: string; messages: number }[];
}

const EMPTY: DashboardData = {
  summary: { total_assessments: 0, active_assessments: 0, completed_assessments: 0, high_risk_count: 0, compliance_rate: 0, total_obligations: 0 },
  risk_distribution: [], obligation_breakdown: [], recent_projects: [], top_gaps: [], activity_timeline: [],
};

// ── Main component ──────────────────────────────────────────────────────
export function Dashboard() {
  const { getToken } = useAuth();
  const [data, setData] = useState<DashboardData>(EMPTY);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await DashboardService.getStats(getToken);
        setData(res);
      } catch (e) {
        console.error("Failed to load dashboard data:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const s = data.summary;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
          <p className="text-sm text-slate-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  // ── Empty state ─────────────────────────────────────────────────────
  if (s.total_assessments === 0) {
    return (
      <div className="space-y-8 animate-in fade-in duration-500">
        <DashboardHeader />
        <div className="flex flex-col items-center justify-center h-[50vh] text-center">
          <Scale className="h-16 w-16 text-slate-300 mb-4" />
          <h2 className="text-xl font-semibold text-slate-700">No assessments yet</h2>
          <p className="text-slate-500 mt-2 max-w-md">
            Start your first compliance assessment to see real-time metrics,
            risk distribution, and obligation tracking here.
          </p>
          <Link
            to="/governance"
            className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Scale size={16} /> Start Assessment
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <DashboardHeader />

      {/* ── ROW 1: KPI Cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total Assessments"
          value={s.total_assessments}
          subtitle={`${s.active_assessments} active`}
          icon={Layers}
          color="text-blue-600"
          bgColor="bg-blue-50"
        />
        <KpiCard
          title="Compliance Rate"
          value={`${s.compliance_rate}%`}
          subtitle={`${s.total_obligations} obligations tracked`}
          icon={s.compliance_rate >= 70 ? ShieldCheck : ShieldAlert}
          color={s.compliance_rate >= 70 ? "text-emerald-600" : "text-amber-600"}
          bgColor={s.compliance_rate >= 70 ? "bg-emerald-50" : "bg-amber-50"}
        />
        <KpiCard
          title="High-Risk Projects"
          value={s.high_risk_count}
          subtitle={s.high_risk_count > 0 ? "Require strict oversight" : "None detected"}
          icon={AlertTriangle}
          color={s.high_risk_count > 0 ? "text-red-600" : "text-slate-500"}
          bgColor={s.high_risk_count > 0 ? "bg-red-50" : "bg-slate-50"}
        />
        <KpiCard
          title="Completed"
          value={s.completed_assessments}
          subtitle={`of ${s.total_assessments} assessments`}
          icon={CheckCircle2}
          color="text-emerald-600"
          bgColor="bg-emerald-50"
        />
      </div>

      {/* ── ROW 2: Charts ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Risk Distribution — donut chart */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <ShieldAlert size={16} className="text-slate-400" /> Risk Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.risk_distribution.length > 0 ? (
              <div className="h-[220px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.risk_distribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                      dataKey="value"
                      nameKey="name"
                      stroke="none"
                    >
                      {data.risk_distribution.map((entry) => (
                        <Cell key={entry.name} fill={RISK_COLORS[entry.name] || "#94a3b8"} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                      formatter={(value: any, name: any) => [`${value} project${value !== 1 ? 's' : ''}`, name]}
                    />
                    <Legend
                      verticalAlign="bottom"
                      iconType="circle"
                      iconSize={8}
                      formatter={(value) => <span className="text-xs text-slate-600">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyChart />
            )}
          </CardContent>
        </Card>

        {/* Activity Timeline — area chart */}
        <Card className="shadow-sm lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Activity size={16} className="text-slate-400" /> Activity (Last 14 Days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.activity_timeline.some(d => d.messages > 0) ? (
              <div className="h-[220px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.activity_timeline}>
                    <defs>
                      <linearGradient id="msgGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="date" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                      formatter={(value: any) => [`${value} messages`, 'Activity']}
                    />
                    <Area
                      type="monotone"
                      dataKey="messages"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fill="url(#msgGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyChart />
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── ROW 3: Obligations + Gaps ────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Obligation Status Breakdown — stacked bar */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <FileText size={16} className="text-slate-400" /> Obligation Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.obligation_breakdown.length > 0 ? (
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data.obligation_breakdown.map(o => ({
                      name: o.code.replace("ART_", "Art. "),
                      Met: o.met,
                      "Under Review": o.review,
                      Planned: o.planned,
                      Gap: o.gap,
                      Pending: o.pending,
                      Unmet: o.unmet,
                    }))}
                    layout="vertical"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                    <XAxis type="number" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" fontSize={11} tickLine={false} axisLine={false} width={60} />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }} />
                    <Bar dataKey="Met" stackId="a" fill={STATUS_COLORS.met} radius={[0, 0, 0, 0]} barSize={18} />
                    <Bar dataKey="Under Review" stackId="a" fill={STATUS_COLORS.review} />
                    <Bar dataKey="Planned" stackId="a" fill={STATUS_COLORS.planned} />
                    <Bar dataKey="Gap" stackId="a" fill={STATUS_COLORS.gap} />
                    <Bar dataKey="Pending" stackId="a" fill={STATUS_COLORS.pending} />
                    <Bar dataKey="Unmet" stackId="a" fill={STATUS_COLORS.unmet} radius={[0, 4, 4, 0]} />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '11px' }} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyChart />
            )}
          </CardContent>
        </Card>

        {/* Top Compliance Gaps */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <XCircle size={16} className="text-slate-400" /> Top Compliance Gaps
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.top_gaps.length > 0 ? (
              <div className="space-y-4">
                {data.top_gaps.map((gap) => {
                  const maxCount = data.top_gaps[0]?.count || 1;
                  const pct = Math.round(gap.count / maxCount * 100);
                  return (
                    <div key={gap.code} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-slate-700">{gap.title}</span>
                        <Badge variant="secondary" className="text-xs">{gap.count} project{gap.count !== 1 ? 's' : ''}</Badge>
                      </div>
                      <Progress value={pct} className="h-2" />
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-[200px] text-slate-400">
                <CheckCircle2 size={32} className="mb-2 text-emerald-400" />
                <p className="text-sm">No compliance gaps detected</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── ROW 4: Recent Assessments Table ──────────────────────── */}
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Clock size={16} className="text-slate-400" /> Recent Assessments
            </CardTitle>
            <Link
              to="/governance"
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 font-medium"
            >
              View all <ArrowUpRight size={12} />
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-slate-500">
                  <th className="text-left font-medium py-3 pr-4">Project</th>
                  <th className="text-left font-medium py-3 px-4">Risk Level</th>
                  <th className="text-left font-medium py-3 px-4">State</th>
                  <th className="text-left font-medium py-3 px-4">Progress</th>
                  <th className="text-right font-medium py-3 pl-4">Updated</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_projects.map((p) => (
                  <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 pr-4">
                      <Link to={`/governance?project=${p.id}`} className="hover:text-blue-600 transition-colors">
                        <p className="font-medium text-slate-800">{p.name}</p>
                        {p.description && (
                          <p className="text-xs text-slate-400 mt-0.5 truncate max-w-[200px]">{p.description}</p>
                        )}
                      </Link>
                    </td>
                    <td className="py-3 px-4">
                      <RiskBadge level={p.risk_level} />
                    </td>
                    <td className="py-3 px-4">
                      <StateBadge state={p.state} />
                    </td>
                    <td className="py-3 px-4 min-w-[140px]">
                      <div className="flex items-center gap-2">
                        <Progress value={p.progress} className="h-1.5 flex-1" />
                        <span className="text-xs text-slate-500 w-12 text-right">
                          {p.met_count}/{p.obligation_count}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 pl-4 text-right text-xs text-slate-400">
                      {p.updated_at ? formatRelative(p.updated_at) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────

function DashboardHeader() {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-1">EU AI Act compliance overview across all your assessments.</p>
      </div>
      <Link
        to="/governance"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
      >
        <Scale size={16} /> New Assessment
      </Link>
    </div>
  );
}

function KpiCard({ title, value, subtitle, icon: Icon, color, bgColor }: {
  title: string; value: string | number; subtitle: string;
  icon: any; color: string; bgColor: string;
}) {
  return (
    <Card className="shadow-sm hover:shadow-md transition-shadow">
      <CardContent className="pt-5 pb-4 px-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
            <p className="text-xs text-slate-400 mt-1">{subtitle}</p>
          </div>
          <div className={`h-10 w-10 rounded-lg ${bgColor} flex items-center justify-center`}>
            <Icon className={`h-5 w-5 ${color}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function RiskBadge({ level }: { level: string }) {
  const upper = (level || "Unknown").toUpperCase();
  const styles: Record<string, string> = {
    UNACCEPTABLE: "bg-red-100 text-red-800 border-red-200",
    HIGH: "bg-orange-100 text-orange-800 border-orange-200",
    LIMITED: "bg-yellow-100 text-yellow-800 border-yellow-200",
    MINIMAL: "bg-emerald-100 text-emerald-800 border-emerald-200",
  };
  const label: Record<string, string> = {
    UNACCEPTABLE: "Prohibited",
    HIGH: "High Risk",
    LIMITED: "Limited",
    MINIMAL: "Minimal",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${styles[upper] || "bg-slate-100 text-slate-600 border-slate-200"}`}>
      {label[upper] || level || "Pending"}
    </span>
  );
}

function StateBadge({ state }: { state: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    INIT: { label: "Not Started", cls: "text-slate-500" },
    INTAKE: { label: "Intake", cls: "text-blue-600" },
    DISCOVERY: { label: "Discovery", cls: "text-blue-600" },
    WORKFLOW: { label: "Workflow", cls: "text-indigo-600" },
    CHECKPOINT: { label: "Evaluation", cls: "text-amber-600" },
    ASSESSMENT: { label: "Complete", cls: "text-emerald-600" },
    TERMINATED: { label: "Terminated", cls: "text-red-600" },
  };
  const m = map[state] || { label: state, cls: "text-slate-500" };
  return <span className={`text-xs font-medium ${m.cls}`}>{m.label}</span>;
}

function EmptyChart() {
  return (
    <div className="flex h-[220px] items-center justify-center text-slate-400 text-sm">
      No data yet
    </div>
  );
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}
