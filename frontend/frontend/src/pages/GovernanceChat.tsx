import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "./../components/ui/card";
import { Button } from "./../components/ui/button";
import { Input } from "./../components/ui/input";
import { Badge } from "./../components/ui/badge";
import { ScrollArea } from "./../components/ui/scroll-area";
import { AlertTriangle, Shield, FileText, Send, Bot, Activity, TrendingUp, History, Download, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { GovernanceService } from "./../services/api";
import { useAuth } from "@clerk/clerk-react";
import { WorkflowVisualizer } from "./../components/WorkflowVisualizer";

export function GovernanceChat() {
  const { getToken } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [started, setStarted] = useState(false);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [projects, setProjects] = useState<Array<{
    id: number;
    name: string;
    description: string;
    risk_level: string;
    message_count: number;
    updated_at: string;
  }>>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);

  // Workflow State (currentWorkflowId passed to chat API)
  const [currentWorkflowId] = useState<number | null>(null); // null = General

  // Data State
  const [messages, setMessages] = useState<{ sender: 'user' | 'bot', text: string }[]>([]);
  const [riskLevel, setRiskLevel] = useState("Unknown");
  const [facts, setFacts] = useState<Record<string, string>>({});
  const [obligations, setObligations] = useState<Array<{
    code: string;
    title: string;
    description: string;
    status: string;
    remediation_context?: string;
  }>>([]);
  const [currentState, setCurrentState] = useState<string>("INIT");
  const [confidence, setConfidence] = useState<string>("LOW");
  const [stateDescription, setStateDescription] = useState<string>("");
  const [workflowSteps, setWorkflowSteps] = useState<string[]>([]);

  // Startup Form State
  const [projectName, setProjectName] = useState("");
  const [projectDesc, setProjectDesc] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLElement | null>(null);

  // Auto-scroll to bottom of chat when messages change or loading state changes
  useEffect(() => {
    const scrollToBottom = () => {
      // Method 1: Find and scroll the Radix ScrollArea viewport directly
      let viewport: HTMLElement | null = viewportRef.current;

      if (!viewport && scrollRef.current) {
        // Try to find the viewport using various selectors
        viewport = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]') as HTMLElement ||
          scrollRef.current.querySelector('div[style*="overflow"]') as HTMLElement ||
          scrollRef.current.querySelector('div[class*="viewport"]') as HTMLElement;

        if (viewport) {
          viewportRef.current = viewport; // Cache it for next time
        }
      }

      if (viewport) {
        // Scroll the viewport to bottom - use both scrollTop and scrollTo for maximum compatibility
        const maxScroll = viewport.scrollHeight - viewport.clientHeight;
        viewport.scrollTop = maxScroll;
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: "smooth"
        });
      }

      // Method 2: Use scrollIntoView on the messages end ref (backup)
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({
          behavior: "smooth",
          block: "end",
          inline: "nearest"
        });
      }
    };

    // Use multiple strategies to ensure scrolling happens
    // Strategy 1: Immediate scroll (for instant feedback)
    scrollToBottom();

    // Strategy 2: Delayed scroll (for content that takes time to render)
    const timeout1 = setTimeout(scrollToBottom, 100);

    // Strategy 3: After animation frame (for layout changes)
    const rafId = requestAnimationFrame(() => {
      setTimeout(scrollToBottom, 150);
    });

    return () => {
      clearTimeout(timeout1);
      cancelAnimationFrame(rafId);
    };
  }, [messages, loading]);

  // Debug: Log messages changes
  useEffect(() => {
    console.log('Messages state updated:', messages);
  }, [messages]);

  // Load projects function - called only when user clicks "View History"
  const loadProjects = async () => {
    setLoadingProjects(true);
    try {
      console.log('Loading projects with token:', !!getToken);
      const data = await GovernanceService.listProjects(getToken);
      console.log('API Response:', data); // CRITICAL: Log full API response
      console.log('Projects loaded:', data.projects?.length || 0, 'projects');
      console.log('Projects data:', data.projects);
      setProjects(data.projects || []);

      if ((data.projects || []).length === 0) {
        console.warn('No projects found. This could mean:');
        console.warn('1. No projects exist in the database');
        console.warn('2. Authentication issue (user_id mismatch)');
        console.warn('3. Database connection issue');
        console.warn('4. All projects are filtered out by user_id check');
      } else {
        console.log('Successfully loaded projects:', data.projects.map((p: { id: number, name: string }) => ({ id: p.id, name: p.name })));
      }
    } catch (e) {
      console.error('Failed to load projects:', e);
      if (e && typeof e === 'object' && 'response' in e) {
        const status = (e as { response?: { status?: number, data?: { detail?: string } } }).response?.status;
        const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Unknown error';
        console.error('Error status:', status);
        console.error('Error detail:', detail);
        if (status === 401) {
          // For backward compatibility, try without auth
          console.warn('401 error, but continuing for backward compatibility');
          setProjects([]);
        } else {
          alert(`Failed to load projects: ${detail}`);
        }
      } else {
        console.error('Non-HTTP error:', e);
        alert("Failed to load projects. Please try again.");
      }
    } finally {
      setLoadingProjects(false);
    }
  };

  // Load projects when user clicks "View History" button
  const handleShowHistory = () => {
    setShowHistory(true);
    if (projects.length === 0 && !loadingProjects) {
      loadProjects();
    }
  };

  // Load existing project
  const loadProject = async (projectId: number) => {
    console.log('loadProject called with projectId:', projectId);
    setLoading(true);
    try {
      console.log('Loading project:', projectId, 'with token:', !!getToken);
      const data = await GovernanceService.getProject(projectId, getToken);
      console.log('Loaded project data:', data);
      console.log('Messages count:', data.messages?.length || 0);

      if (!data || !data.project) {
        throw new Error('Invalid project data received from server');
      }

      setProjectId(projectId);

      // Map messages from API response
      const loadedMessages = (data.messages || []).map((m: { sender: string, message: string, text?: string }) => ({
        sender: m.sender as 'user' | 'bot',
        text: m.message || m.text || ''
      }));

      console.log('Loaded messages:', loadedMessages);

      // If no messages but project is in INIT state, show initial message
      if (loadedMessages.length === 0 && data.project.interview_state === "INIT") {
        loadedMessages.push({
          sender: 'bot' as const,
          text: "I have created your profile. To begin, please describe the AI system you are building or using. What is its main purpose?"
        });
      }

      setMessages(loadedMessages);
      setRiskLevel(data.project.risk_level || "Unknown");
      setFacts(data.facts || {});
      setObligations((data.obligations || []).map((ob: { code?: string; title?: string; description?: string; status?: string; remediation_context?: string } | string) =>
        typeof ob === 'string' ? { code: ob, title: ob, description: '', status: '' } : { code: ob.code || '', title: ob.title ?? ob.code ?? '', description: (ob as { description?: string }).description ?? '', status: (ob as { status?: string }).status ?? '', remediation_context: (ob as { remediation_context?: string }).remediation_context }
      ));
      setCurrentState(data.project.interview_state || "INIT");
      setConfidence(data.project.confidence_level || "LOW");
      setWorkflowSteps(Array.isArray(data.workflow_steps) ? data.workflow_steps : []);

      // CRITICAL: Set these in the correct order to ensure the chat view is shown
      setShowHistory(false); // Hide history view first
      setStarted(true); // Then show the chat interface

      console.log('Project loaded successfully. State: started=true, showHistory=false');
    } catch (e) {
      console.error('Failed to load project:', e);
      console.error('Error details:', e);
      const errorMessage = e instanceof Error ? e.message : 'Unknown error';
      alert(`Failed to load project: ${errorMessage}\n\nCheck the browser console (F12) for more details.`);
    } finally {
      setLoading(false);
    }
  };

  // Check for project ID in URL query params on mount (after loadProject is defined)
  useEffect(() => {
    const projectParam = searchParams.get('project');
    if (projectParam) {
      const projectIdFromUrl = parseInt(projectParam, 10);
      if (!isNaN(projectIdFromUrl) && projectIdFromUrl !== projectId) {
        console.log('Project ID found in URL:', projectIdFromUrl);
        loadProject(projectIdFromUrl);
        // Clear the query parameter after loading
        setSearchParams({});
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  // 1. Start the Interview
  const handleStart = async () => {
    if (!projectName) return;
    if (!getToken) {
      alert("Please wait for authentication to complete.");
      return;
    }

    setLoading(true);

    try {
      console.log('Starting interview with:', { projectName, projectDesc });
      console.log('getToken available:', !!getToken);

      // Try to get token first to verify it works (with timeout)
      if (getToken) {
        try {
          const testToken = await Promise.race([
            getToken(),
            new Promise<null>((resolve) => setTimeout(() => resolve(null), 3000))
          ]);
          console.log('Token retrieved:', !!testToken);
          if (!testToken) {
            console.warn('Token retrieval timed out or returned null');
          }
        } catch (tokenError) {
          console.warn('Token retrieval test failed:', tokenError);
        }
      }

      const data = await GovernanceService.startInterview(projectName, projectDesc, getToken);
      console.log('Interview started successfully:', data);

      if (!data || !data.project_id) {
        throw new Error('Invalid response from server: missing project_id');
      }

      if (!data.message) {
        console.warn('No message in response, using default');
      }

      const initialMessage = data.message || "I have created your profile. To begin, please describe the AI system you are building or using. What is its main purpose?";

      console.log('Setting initial message:', initialMessage);
      setProjectId(data.project_id);
      setMessages([{ sender: 'bot', text: initialMessage }]);
      console.log('Messages state set:', [{ sender: 'bot', text: initialMessage }]);
      setCurrentState(data.state || "INIT");
      setConfidence(data.confidence || "LOW");
      setWorkflowSteps(Array.isArray(data.workflow_steps) ? data.workflow_steps : []);
      setStarted(true);
      setShowHistory(false);
      // Refresh project list if user has history view open
      if (showHistory) {
        await loadProjects();
      }
    } catch (e: unknown) {
      console.error('Error starting interview:', e);
      const error = e as { code?: string, message?: string, response?: { status?: number, statusText?: string, data?: { detail?: string, message?: string } } };
      console.error('Error details:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        code: error?.code
      });

      let errorMsg = "Failed to start interview.";
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        errorMsg = "Request timed out. The backend might be slow or not responding.";
      } else if (error?.response) {
        errorMsg = error.response.data?.detail || error.response.data?.message || `Server error: ${error.response.status}`;
      } else if (error?.message) {
        errorMsg = error.message;
      }

      alert(`Error: ${errorMsg}\n\nTroubleshooting:\n1. Check if backend is running: http://localhost:8000\n2. Check browser console (F12) for details\n3. Try refreshing the page`);
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
      const data = await GovernanceService.sendMessage(projectId, userMsg, currentWorkflowId, getToken);

      // Update Chat
      setMessages(prev => [...prev, { sender: 'bot', text: data.response }]);

      // Update Live Dashboard
      setRiskLevel(data.risk_level);
      setFacts(data.facts);
      setObligations(Array.isArray(data.obligations) ? data.obligations.map((ob: { code?: string; title?: string; description?: string; status?: string; remediation_context?: string } | string) =>
        typeof ob === 'string' ? { code: ob, title: ob, description: '', status: '' } : { code: ob.code || '', title: ob.title ?? ob.code ?? '', description: ob.description ?? '', status: ob.status ?? '', remediation_context: ob.remediation_context }
      ) : []);
      setCurrentState(data.state || currentState);
      setConfidence(data.confidence || confidence);
      setStateDescription(data.state_description || "");
      setWorkflowSteps(Array.isArray(data.workflow_steps) ? data.workflow_steps : []);
      if (data.terminated === true) {
        setCurrentState("TERMINATED");
      }

    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { sender: 'bot', text: "⚠️ Error connecting to Logic Engine." }]);
    } finally {
      setLoading(false);
    }
  };

  // Generate report
  const handleGenerateReport = async () => {
    if (!projectId || !getToken) return;
    setLoading(true);
    try {
      await GovernanceService.generateReport(projectId, getToken);
    } catch (e) {
      console.error('Failed to generate report:', e);
      alert("Failed to generate report. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // --- RENDER: START SCREEN ---
  if (!started || showHistory) {
    return (
      <div className="max-w-6xl mx-auto mt-10 space-y-6 animate-in fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">EU AI Act Compliance</h1>
            <p className="text-slate-500">Automated Governance & Risk Classification</p>
          </div>
          <Button onClick={() => { setShowHistory(false); setStarted(false); }} variant="outline">
            <Plus className="h-4 w-4 mr-2" /> New Assessment
          </Button>
        </div>

        {showHistory ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" /> Chat History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingProjects ? (
                <div className="text-center py-8 text-slate-500">Loading projects...</div>
              ) : projects.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  No previous assessments. Start a new one to begin.
                </div>
              ) : (
                <div className="space-y-2">
                  {projects.map((project) => (
                    <div
                      key={project.id}
                      className="p-4 border rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Project clicked:', project.id, project.name);
                        loadProject(project.id);
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold text-slate-900">{project.name}</h3>
                          <p className="text-sm text-slate-500">{project.description}</p>
                          <div className="flex gap-2 mt-2">
                            <Badge variant={project.risk_level === "HIGH" ? "destructive" : "outline"}>
                              {project.risk_level} Risk
                            </Badge>
                            <Badge variant="outline">{project.message_count} messages</Badge>
                          </div>
                        </div>
                        <div className="text-xs text-slate-400">
                          {new Date(project.updated_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>New Assessment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Project Name</label>
                <Input placeholder="e.g. HR Resume Screener" value={projectName} onChange={e => setProjectName(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-medium">Short Description</label>
                <Input placeholder="What does the AI do?" value={projectDesc} onChange={e => setProjectDesc(e.target.value)} />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleStart} className="flex-1" disabled={loading}>
                  {loading ? "Initializing..." : "Start Assessment"}
                </Button>
                <Button onClick={handleShowHistory} variant="outline">
                  <History className="h-4 w-4 mr-2" /> View History
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  // --- RENDER: MAIN DASHBOARD ---
  return (
    <div className="flex flex-col gap-4 p-4 max-w-7xl mx-auto animate-in fade-in">
      {/* Disclaimer: not legal advice */}
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3 text-amber-900 text-sm">
        <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5 text-amber-600" />
        <div>
          <p className="font-medium">Disclaimer</p>
          <p className="text-amber-800/90 mt-0.5">
            The suggestions and output from this chatbot are <strong>not legal advice</strong>. They are for informational purposes only and should be treated as <strong>speculation or preliminary guidance</strong>. Always consult a qualified legal or compliance professional before making decisions. See <Link to="/terms" className="underline font-medium">Terms of Use</Link> for more.
          </p>
        </div>
      </div>

      <div className="flex h-[calc(100vh-180px)] gap-6">
        {/* LEFT: CHAT INTERFACE */}
        <Card className="w-2/3 flex flex-col shadow-lg border-slate-200">
          <CardHeader className="border-b bg-slate-50 py-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Bot className="h-5 w-5 text-blue-600" />
                AI Compliance Consultant
              </CardTitle>
              <div className="flex gap-2">
                <Button onClick={() => { setShowHistory(true); setStarted(false); }} variant="ghost" size="sm">
                  <History className="h-4 w-4 mr-2" /> History
                </Button>
                {currentState === "ASSESSMENT" && (
                  <Button onClick={handleGenerateReport} variant="outline" size="sm" disabled={loading}>
                    <Download className="h-4 w-4 mr-2" /> Download Report (for human review)
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>

          <ScrollArea
            className="flex-1 p-4"
            ref={(node) => {
              if (node) {
                scrollRef.current = node;
                // Find and cache the viewport element immediately when ScrollArea mounts
                const viewport = node.querySelector('[data-radix-scroll-area-viewport]') as HTMLElement;
                if (viewport) {
                  viewportRef.current = viewport;
                  console.log('Viewport cached for autoscroll');
                }
              }
            }}
          >
            <div className="space-y-4">
              {messages.length === 0 && !loading && (
                <div className="text-center text-slate-400 text-sm italic py-8">
                  No messages yet. Waiting for bot response...
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-lg p-3 text-sm ${m.sender === 'user'
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
              {/* Invisible element at the bottom to scroll to */}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          <div className="p-4 border-t bg-white">
            {currentState === "TERMINATED" && (
              <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                This chat has been closed. Please start a new assessment for a different use case.
              </div>
            )}
            <div className="flex gap-2">
              <Input
                placeholder={currentState === "TERMINATED" ? "Chat closed" : "Type your answer..."}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !(currentState === "TERMINATED") && handleSend()}
                disabled={loading || currentState === "TERMINATED"}
              />
              <Button onClick={handleSend} disabled={loading || currentState === "TERMINATED"} size="icon">
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </Card>

        {/* RIGHT: LIVE GOVERNANCE STATE */}
        <div className="w-1/3 space-y-6">

          {/* 1. RISK LEVEL CARD */}
          <Card className={`border-l-4 shadow-md ${riskLevel === "UNACCEPTABLE" || riskLevel === "HIGH" ? "border-l-red-500" :
            riskLevel === "LIMITED" ? "border-l-yellow-500" :
              "border-l-green-500"
            }`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">Current Risk Classification</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                {riskLevel === "UNACCEPTABLE" || riskLevel === "HIGH" ? <AlertTriangle className="h-8 w-8 text-red-500" /> : <Shield className="h-8 w-8 text-green-600" />}
                <div>
                  <div className="text-2xl font-black text-slate-900">{riskLevel} RISK</div>
                  <div className="text-xs text-slate-500">EU AI Act (2025)</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 1.5. STATE & CONFIDENCE CARD */}
          <Card className="shadow-sm border-l-4 border-l-blue-500">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">Interview State</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Activity className="h-4 w-4 text-blue-500" />
                    <span className="text-xs font-medium text-slate-600">Current Phase</span>
                  </div>
                  <div className="text-sm font-semibold text-slate-900 capitalize">
                    {currentState.replace("_", " ").toLowerCase()}
                  </div>
                  {stateDescription && (
                    <div className="text-xs text-slate-500 mt-1">{stateDescription}</div>
                  )}
                </div>
                <div className="pt-2 border-t border-slate-100">
                  <div className="flex items-center gap-2 mb-1">
                    <TrendingUp className={`h-4 w-4 ${confidence === "HIGH" ? "text-green-500" :
                      confidence === "MEDIUM" ? "text-yellow-500" :
                        "text-orange-500"
                      }`} />
                    <span className="text-xs font-medium text-slate-600">Confidence</span>
                  </div>
                  <div className={`text-sm font-semibold ${confidence === "HIGH" ? "text-green-700" :
                    confidence === "MEDIUM" ? "text-yellow-700" :
                      "text-orange-700"
                    }`}>
                    {confidence}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {confidence === "HIGH"
                      ? "Assessment based on sufficient information"
                      : confidence === "MEDIUM"
                        ? "Classification may change with additional information"
                        : "Classification may change significantly"}
                  </div>
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
                    {Object.entries(facts).map(([key, val]) => {
                      const displayVal = val === "planned_remediation" || val === "planned"
                        ? "Planned"
                        : val === "partial_or_unclear"
                          ? "Under Review"
                          : val;
                      const isPlanned = val === "planned_remediation" || val === "planned";
                      const isUnderReview = val === "partial_or_unclear";
                      return (
                        <div key={key} className="p-3 flex justify-between items-center text-sm hover:bg-slate-50">
                          <span className="font-medium text-slate-600 capitalize">{key.replace("_", " ")}</span>
                          <Badge
                            variant="outline"
                            className={`capitalize ${isPlanned ? "bg-yellow-100 text-yellow-800 border-yellow-300" :
                                isUnderReview ? "bg-amber-50 text-amber-800 border-amber-300" :
                                  "bg-white"
                              }`}
                          >
                            {displayVal}
                          </Badge>
                        </div>
                      );
                    })}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

          {/* 2.5. LIVE WORKFLOW MAP */}
          <WorkflowVisualizer steps={workflowSteps} />

          {/* 3. OBLIGATIONS */}
          <Card className="shadow-sm flex-1">
            <CardHeader className="py-3 bg-slate-50 border-b"><CardTitle className="text-sm">Compliance Obligations</CardTitle></CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[250px]">
                {obligations.length === 0 ? (
                  <div className="p-4 text-center text-slate-400 text-sm italic">No obligations triggered yet...</div>
                ) : (
                  <div className="p-2 space-y-2">
                    {obligations.map((ob, i) => {
                      const status = (ob.status || '').trim().toLowerCase();
                      const statusLabel =
                        status === 'under_review' ? 'Under Review' :
                          status === 'planned_remediation' || status === 'planned' ? 'Planned' :
                            status === 'met' ? 'Met' :
                              status === 'gap_detected' ? 'Gap' :
                                'Pending';
                      const statusClass =
                        status === 'met' ? 'bg-emerald-100 text-emerald-800' :
                          status === 'planned_remediation' || status === 'planned' ? 'bg-amber-100 text-amber-800' :
                            status === 'under_review' ? 'bg-amber-100 text-amber-800' :
                              status === 'gap_detected' ? 'bg-red-100 text-red-800' :
                                'bg-slate-100 text-slate-600';
                      return (
                        <div key={i} className="flex gap-3 p-2 rounded border border-slate-100 bg-white items-start">
                          <FileText className="h-4 w-4 text-blue-500 mt-1 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="font-bold text-xs text-slate-700">{ob.code}</div>
                            <div className="text-[10px] text-slate-500">{ob.title || 'Required by Law'}</div>
                            {ob.remediation_context && (
                              <div className="text-[10px] text-blue-600 mt-0.5 italic truncate" title={ob.remediation_context}>
                                {ob.remediation_context}
                              </div>
                            )}
                            {ob.status && (
                              <span className={`inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${statusClass}`}>
                                {statusLabel}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
