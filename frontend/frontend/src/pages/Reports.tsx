import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "./../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./../components/ui/table";
import { Badge } from "./../components/ui/badge";
import { Button } from "./../components/ui/button";
import { FileText, Download, Loader2, Scale } from "lucide-react";
import { AuditService, GovernanceService } from "./../services/api";
import { useUser, useAuth } from "@clerk/clerk-react";

export function Reports() {
  const [auditReports, setAuditReports] = useState<Array<{
    id: number;
    timestamp: string;
    risk_level?: string;
    score?: number;
    compliance_score?: number;
    status?: string;
  }>>([]);
  const [governanceProjects, setGovernanceProjects] = useState<Array<{
    id: number;
    name: string;
    description: string;
    risk_level: string;
    interview_state: string;
    message_count: number;
    updated_at: string;
  }>>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"audit" | "governance">("governance");
  const { user } = useUser();
  const { getToken } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        // Load audit history
        if (user) {
          try {
            const auditData = await AuditService.getHistory(user.id);
            setAuditReports(auditData || []);
          } catch (e) {
            console.error("Failed to load audit history:", e);
            setAuditReports([]);
          }
        }

        // Load governance chat projects
        try {
          const governanceData = await GovernanceService.listProjects(getToken);
          console.log("Governance projects loaded:", governanceData);
          setGovernanceProjects(governanceData.projects || []);
        } catch (e) {
          console.error("Failed to load governance projects:", e);
          setGovernanceProjects([]);
        }
      } catch (e) {
        console.error("Error loading data:", e);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [user, getToken]);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">History & Reports</h1>
        <Button variant="outline" onClick={() => window.location.reload()}>Refresh</Button>
      </div>

      {/* Tab Selector */}
      <div className="flex gap-2 border-b border-slate-200">
        <Button
          variant={activeTab === "governance" ? "default" : "ghost"}
          onClick={() => setActiveTab("governance")}
          className={activeTab === "governance" ? "border-b-2 border-blue-600" : ""}
        >
          <Scale className="h-4 w-4 mr-2" /> Governance Chat History
        </Button>
        <Button
          variant={activeTab === "audit" ? "default" : "ghost"}
          onClick={() => setActiveTab("audit")}
          className={activeTab === "audit" ? "border-b-2 border-blue-600" : ""}
        >
          <FileText className="h-4 w-4 mr-2" /> Audit Archive
        </Button>
      </div>

      {/* Governance Chat History Tab */}
      {activeTab === "governance" && (
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-slate-500" /> Compliance Chat Projects
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="animate-spin text-slate-400" /></div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Project ID</TableHead>
                    <TableHead>Project Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Risk Level</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead>Messages</TableHead>
                    <TableHead>Last Updated</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {governanceProjects.map((project) => (
                    <TableRow key={project.id}>
                      <TableCell className="font-medium">#{project.id}</TableCell>
                      <TableCell className="font-semibold">{project.name || "Untitled"}</TableCell>
                      <TableCell className="text-slate-600 max-w-xs truncate">{project.description || "No description"}</TableCell>
                      <TableCell>
                        <Badge
                          variant={project.risk_level === "HIGH" ? "destructive" : project.risk_level === "LIMITED" ? "default" : "outline"}
                          className={
                            project.risk_level === "HIGH" ? "bg-red-600" :
                              project.risk_level === "LIMITED" ? "bg-yellow-500" :
                                project.risk_level === "UNACCEPTABLE" ? "bg-red-800" :
                                  "bg-slate-200"
                          }
                        >
                          {project.risk_level || "Unknown"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {project.interview_state || "INIT"}
                        </Badge>
                      </TableCell>
                      <TableCell>{project.message_count || 0}</TableCell>
                      <TableCell>{project.updated_at ? new Date(project.updated_at).toLocaleDateString() : "N/A"}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-blue-600 hover:text-blue-700"
                          onClick={() => navigate(`/governance?project=${project.id}`)}
                        >
                          <FileText className="h-4 w-4 mr-2" /> View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {governanceProjects.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center h-32 text-slate-500">
                        No governance chat projects found. Start a new compliance assessment to see data here.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* Audit Archive Tab */}
      {activeTab === "audit" && (
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-slate-500" /> Audit Historical Records
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="animate-spin text-slate-400" /></div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run ID</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Risk Category</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Certificate</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditReports.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell className="font-medium">#{run.id}</TableCell>
                      <TableCell>{new Date(run.timestamp).toLocaleDateString()}</TableCell>
                      <TableCell className="text-slate-500">{run.risk_level || "High Risk (HR)"}</TableCell>
                      <TableCell className="font-bold">{run.score || run.compliance_score || "N/A"}</TableCell>
                      <TableCell>
                        <Badge variant={run.status === "COMPLIANT" ? "default" : "destructive"} className={run.status === "COMPLIANT" ? "bg-emerald-600 hover:bg-emerald-700" : ""}>
                          {run.status || "N/A"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" className="text-blue-600 hover:text-blue-700">
                          <Download className="h-4 w-4 mr-2" /> PDF
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {auditReports.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center h-32 text-slate-500">
                        No audit records found. Run a new audit to see data here.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}