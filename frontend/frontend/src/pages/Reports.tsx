import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./../components/ui/table";
import { Badge } from "./../components/ui/badge";
import { Button } from "./../components/ui/button";
import { FileText, Download, Loader2 } from "lucide-react";
import { AuditService } from "./../services/api";

export function Reports() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AuditService.getHistory()
      .then(setReports)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
         <h1 className="text-3xl font-bold tracking-tight text-slate-900">Audit Archive</h1>
         <Button variant="outline" onClick={() => window.location.reload()}>Refresh</Button>
      </div>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-slate-500" /> Historical Records
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
                {reports.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell className="font-medium">#{run.id}</TableCell>
                    <TableCell>{new Date(run.timestamp).toLocaleDateString()}</TableCell>
                    <TableCell className="text-slate-500">High Risk (HR)</TableCell>
                    <TableCell className="font-bold">{run.compliance_score}</TableCell>
                    <TableCell>
                      <Badge variant={run.status === "COMPLIANT" ? "default" : "destructive"} className={run.status === "COMPLIANT" ? "bg-emerald-600 hover:bg-emerald-700" : ""}>
                        {run.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="text-blue-600 hover:text-blue-700">
                        <Download className="h-4 w-4 mr-2" /> PDF
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                 {reports.length === 0 && (
                    <TableRow>
                        <TableCell colSpan={6} className="text-center h-32 text-slate-500">
                            No records found. Run a new audit to see data here.
                        </TableCell>
                    </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}