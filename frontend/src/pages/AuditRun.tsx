import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "./../components/ui/card";
import { Button } from "./../components/ui/button";
import { Textarea } from "./../components/ui/textarea";
import { Input } from "./../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./../components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "./../components/ui/alert";
import { ShieldCheck, Download, Loader2, Plus, ArrowRight, ExternalLink } from "lucide-react";
import { AuditService } from "./../services/api";
import { useUser } from "@clerk/clerk-react";

export function AuditRun() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const { user } = useUser();
  
  // Form Inputs
  const [description, setDescription] = useState('');
  const [customMetric, setCustomMetric] = useState('');
  const [userMetrics, setUserMetrics] = useState<string[]>([]);
  const [apiKey, setApiKey] = useState('');
  // Default to a valid OpenRouter model ID
  const [selectedModel, setSelectedModel] = useState('openai/gpt-3.5-turbo');

  // Results
  const [riskProfile, setRiskProfile] = useState<any>(null);
  const [auditResults, setAuditResults] = useState<any>(null);

  const addMetric = () => {
    if (customMetric && userMetrics.length < 4) {
      setUserMetrics([...userMetrics, customMetric]);
      setCustomMetric('');
    }
  };

  const handleRiskAnalysis = async () => {
    setLoading(true);
    try {
      // Analyze Risk
      const data = await AuditService.analyzeRisk(description, userMetrics);
      setRiskProfile(data);
      setStep(2); // Move to review step
    } catch (error) {
      alert("Error connecting to Backend. Make sure your Python server is running!");
    } finally {
      setLoading(false);
    }
  };

  const handleRunAudit = async () => {
      setLoading(true);
      try {
        // CHANGED: Now passing description as the final 'systemPrompt' argument
        const results = await AuditService.runAudit(
          apiKey, 
          riskProfile.metrics, 
          selectedModel, 
          riskProfile.risk_level,
          user?.id,
          description // <--- THIS is sent as the System Prompt / Persona
        );
        setAuditResults(results);
        setStep(3);
      } catch (error) {
        alert("Audit failed. Please check your API Key.");
      } finally {
        setLoading(false);
      }
    };

  const handleDownload = async () => {
    try {
      const blob = await AuditService.downloadReport(auditResults);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `audit_report_${selectedModel.replace('/', '_')}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (e) { console.error(e); }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 animate-in fade-in duration-700">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-slate-900">New Compliance Audit</h1>
        <p className="text-slate-500 mt-2">Configure your audit parameters below.</p>
      </div>

      {/* STEP 1: CONFIGURATION (ALL INPUTS HERE NOW) */}
      {step === 1 && (
        <Card className="shadow-md">
          <CardHeader><CardTitle>1. System Configuration</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            
            {/* 1. Description */}
            <div>
              <label className="text-sm font-medium mb-1 block">System Description</label>
              <Textarea 
                placeholder="e.g. An AI tool that screens resumes for a tech company..." 
                className="min-h-[100px]"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <p className="text-xs text-slate-500 mt-1">This text will be used to simulate the AI's persona during testing.</p>
            </div>

            {/* 2. Metrics */}
            <div>
              <label className="text-sm font-medium mb-1 block">Specific Metrics (Optional)</label>
              <div className="flex gap-2 mb-2">
                <Input 
                  placeholder="e.g. Gender Bias" 
                  value={customMetric}
                  onChange={(e) => setCustomMetric(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addMetric()}
                />
                <Button variant="outline" onClick={addMetric} disabled={userMetrics.length >= 4}><Plus className="h-4 w-4"/></Button>
              </div>
              <div className="flex gap-2 flex-wrap">
                {userMetrics.map((m, i) => (
                  <span key={i} className="bg-slate-100 px-3 py-1 rounded-full text-sm flex items-center gap-2">
                    {m} <button onClick={() => setUserMetrics(userMetrics.filter((_, idx) => idx !== i))} className="text-slate-400 hover:text-red-500">×</button>
                  </span>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* 3. Model Selector (UPDATED FOR OPENROUTER) */}
              <div>
                <label className="text-sm font-medium mb-1 block">Target Model</label>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai/gpt-3.5-turbo">OpenAI: GPT-3.5 Turbo</SelectItem>
                    <SelectItem value="openai/gpt-4o">OpenAI: GPT-4o</SelectItem>
                    <SelectItem value="anthropic/claude-3.5-sonnet">Anthropic: Claude 3.5 Sonnet</SelectItem>
                    <SelectItem value="google/gemini-pro-1.5">Google: Gemini 1.5 Pro</SelectItem>
                    <SelectItem value="meta-llama/llama-3-70b-instruct">Meta: Llama 3 70B</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* 4. API Key (UPDATED FOR UNIFIED KEY) */}
              <div>
                <div className="flex justify-between items-center mb-1">
                    <label className="text-sm font-medium block">OpenRouter API Key</label>
                    <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer" className="text-xs text-blue-600 flex items-center hover:underline">
                        Get Key <ExternalLink className="h-3 w-3 ml-1"/>
                    </a>
                </div>
                <Input 
                  type="password" 
                  placeholder="sk-or-v1-..." 
                  value={apiKey} 
                  onChange={(e) => setApiKey(e.target.value)} 
                />
                <p className="text-[10px] text-slate-500 mt-1">One key to access all models above.</p>
              </div>
            </div>

            <Button onClick={handleRiskAnalysis} disabled={loading || !description || !apiKey} className="w-full bg-slate-900 hover:bg-slate-800">
              {loading ? <Loader2 className="animate-spin mr-2" /> : "Analyze & Review Plan"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* STEP 2: REVIEW & EXECUTE */}
      {step === 2 && riskProfile && (
        <div className="space-y-6">
          <Alert className="bg-blue-50 border-blue-200">
            <ShieldCheck className="h-5 w-5 text-blue-600" />
            <AlertTitle className="text-blue-800">Audit Plan Generated</AlertTitle>
            <AlertDescription className="text-blue-700 mt-1">
              Risk Level: <b>{riskProfile.risk_level}</b><br/>
              Testing Metrics: <b>{riskProfile.metrics.join(", ")}</b>
            </AlertDescription>
          </Alert>

          <Card className="shadow-md">
            <CardHeader><CardTitle>2. Confirm Execution</CardTitle></CardHeader>
            <CardContent>
              <div className="bg-slate-50 p-4 rounded-lg mb-6 text-sm text-slate-600">
                You are about to audit <b>{selectedModel}</b> using the OpenRouter key provided. 
                This will generate synthetic attacks against the specific persona described above.
              </div>
              
              <div className="flex gap-4">
                 <Button variant="outline" onClick={() => setStep(1)} className="w-1/3">Back</Button>
                 <Button onClick={handleRunAudit} disabled={loading} className="w-2/3 bg-blue-600 hover:bg-blue-700">
                    {loading ? <span className="flex items-center"><Loader2 className="animate-spin mr-2" /> Running Audit...</span> : <span className="flex items-center">Start Audit <ArrowRight className="ml-2 h-4 w-4"/></span>}
                 </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* STEP 3: RESULTS */}
      {step === 3 && auditResults && (
        <Card className="border-green-500 border-2 shadow-lg">
          <CardContent className="pt-8 text-center space-y-6">
            <div className="text-6xl font-black text-slate-900">{auditResults.compliance_score}</div>
            <p className="text-xl text-slate-600 font-medium">Compliance Score</p>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4">
              {auditResults.metric_breakdown?.map((m: any) => (
                <div key={m.name} className="p-3 bg-slate-50 rounded-lg">
                  <div className="text-sm text-slate-500 mb-1">{m.name}</div>
                  <div className="font-bold text-lg">{m.score}/100</div>
                </div>
              ))}
            </div>

            <Button onClick={handleDownload} className="w-full" size="lg">
              <Download className="mr-2 h-5 w-5" /> Download Full Report
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}