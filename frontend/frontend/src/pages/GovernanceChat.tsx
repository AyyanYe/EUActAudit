import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "./../components/ui/card";
import { Button } from "./../components/ui/button";
import { Input } from "./../components/ui/input";
import { Badge } from "./../components/ui/badge";
import { ScrollArea } from "./../components/ui/scroll-area";
import { AlertTriangle, CheckCircle, Shield, FileText, Send, User, Bot } from "lucide-react";
import { GovernanceService } from "./../services/api";

export function GovernanceChat() {
  // State
  const [started, setStarted] = useState(false);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  
  // Data State
  const [messages, setMessages] = useState<{sender: 'user' | 'bot', text: string}[]>([]);
  const [riskLevel, setRiskLevel] = useState("Unknown");
  const [facts, setFacts] = useState<Record<string, string>>({});
  const [obligations, setObligations] = useState<string[]>([]);

  // Startup Form State
  const [projectName, setProjectName] = useState("");
  const [projectDesc, setProjectDesc] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // 1. Start the Interview
  const handleStart = async () => {
    if (!projectName) return;
    setLoading(true);
    try {
      const data = await GovernanceService.startInterview(projectName, projectDesc);
      setProjectId(data.project_id);
      setMessages([{ sender: 'bot', text: data.message }]);
      setStarted(true);
    } catch (e) {
      alert("Backend not connected! Check your terminal.");
    } finally {
      setLoading(false);
    }
  };

  // 2. Send Message Loop
  const handleSend = async () => {
    if (!input.trim() || !projectId) return;
    
    const userMsg = input;
    setInput("");
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setLoading(true);

    try {
      const data = await GovernanceService.sendMessage(projectId, userMsg);
      
      // Update Chat
      setMessages(prev => [...prev, { sender: 'bot', text: data.response }]);
      
      // Update Live Dashboard
      setRiskLevel(data.risk_level);
      setFacts(data.facts);
      setObligations(data.obligations);
      
    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { sender: 'bot', text: "⚠️ Error connecting to Logic Engine." }]);
    } finally {
      setLoading(false);
    }
  };

  // --- RENDER: START SCREEN ---
  if (!started) {
    return (
      <div className="max-w-md mx-auto mt-20 space-y-6 animate-in fade-in">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900">EU AI Act Compliance</h1>
          <p className="text-slate-500">Automated Governance & Risk Classification</p>
        </div>
        <Card>
          <CardHeader><CardTitle>New Assessment</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Project Name</label>
              <Input placeholder="e.g. HR Resume Screener" value={projectName} onChange={e => setProjectName(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium">Short Description</label>
              <Input placeholder="What does the AI do?" value={projectDesc} onChange={e => setProjectDesc(e.target.value)} />
            </div>
            <Button onClick={handleStart} className="w-full" disabled={loading}>
              {loading ? "Initializing..." : "Start Assessment"}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // --- RENDER: MAIN DASHBOARD ---
  return (
    <div className="flex h-[calc(100vh-100px)] gap-6 p-4 max-w-7xl mx-auto animate-in fade-in">
      
      {/* LEFT: CHAT INTERFACE */}
      <Card className="w-2/3 flex flex-col shadow-lg border-slate-200">
        <CardHeader className="border-b bg-slate-50 py-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Bot className="h-5 w-5 text-blue-600"/> 
            AI Compliance Consultant
          </CardTitle>
        </CardHeader>
        
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="space-y-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg p-3 text-sm ${
                  m.sender === 'user' 
                    ? 'bg-blue-600 text-white rounded-br-none' 
                    : 'bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200 shadow-sm'
                }`}>
                  {/* Markdown-style rendering for Bot */}
                  {m.sender === 'bot' ? (
                    <div className="whitespace-pre-wrap">{m.text}</div>
                  ) : (
                    m.text
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-50 text-slate-400 rounded-lg p-3 text-xs italic animate-pulse">
                  Analyzing regulations...
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="p-4 border-t bg-white">
          <div className="flex gap-2">
            <Input 
              placeholder="Type your answer..." 
              value={input} 
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              disabled={loading}
            />
            <Button onClick={handleSend} disabled={loading} size="icon">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* RIGHT: LIVE GOVERNANCE STATE */}
      <div className="w-1/3 space-y-6">
        
        {/* 1. RISK LEVEL CARD */}
        <Card className={`border-l-4 shadow-md ${
          riskLevel === "HIGH" ? "border-l-red-500" : 
          riskLevel === "LIMITED" ? "border-l-yellow-500" : 
          "border-l-green-500"
        }`}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">Current Risk Classification</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              {riskLevel === "HIGH" ? <AlertTriangle className="h-8 w-8 text-red-500"/> : <Shield className="h-8 w-8 text-green-600"/>}
              <div>
                <div className="text-2xl font-black text-slate-900">{riskLevel} RISK</div>
                <div className="text-xs text-slate-500">EU AI Act (2025)</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 2. EXTRACTED FACTS */}
        <Card className="shadow-sm">
          <CardHeader className="py-3 bg-slate-50 border-b"><CardTitle className="text-sm">Identified Facts</CardTitle></CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[200px]">
              {Object.keys(facts).length === 0 ? (
                <div className="p-4 text-center text-slate-400 text-sm italic">No facts extracted yet...</div>
              ) : (
                <div className="divide-y">
                  {Object.entries(facts).map(([key, val]) => (
                    <div key={key} className="p-3 flex justify-between items-center text-sm hover:bg-slate-50">
                      <span className="font-medium text-slate-600 capitalize">{key.replace("_", " ")}</span>
                      <Badge variant="outline" className="capitalize bg-white">{val}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* 3. OBLIGATIONS */}
        <Card className="shadow-sm flex-1">
          <CardHeader className="py-3 bg-slate-50 border-b"><CardTitle className="text-sm">Compliance Obligations</CardTitle></CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[250px]">
               {obligations.length === 0 ? (
                <div className="p-4 text-center text-slate-400 text-sm italic">No obligations triggered yet...</div>
              ) : (
                <div className="p-2 space-y-2">
                  {obligations.map((ob, i) => (
                    <div key={i} className="flex gap-3 p-2 rounded border border-slate-100 bg-white items-start">
                      <FileText className="h-4 w-4 text-blue-500 mt-1 shrink-0" />
                      <div>
                        <div className="font-bold text-xs text-slate-700">{ob}</div>
                        <div className="text-[10px] text-slate-500">Required by Law</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}