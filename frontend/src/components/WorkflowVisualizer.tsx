import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { ChevronDown } from "lucide-react";

interface WorkflowVisualizerProps {
  steps: string[];
}

export function WorkflowVisualizer({ steps }: WorkflowVisualizerProps) {
  if (!steps || steps.length === 0) {
    return (
      <Card className="shadow-sm">
        <CardHeader className="py-3 bg-slate-50 border-b">
          <CardTitle className="text-sm">Live Workflow Map</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="text-center text-slate-400 text-sm italic">
            No steps yet. Describe your AI system and we&apos;ll map the flow.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="py-3 bg-slate-50 border-b">
        <CardTitle className="text-sm">Live Workflow Map</CardTitle>
      </CardHeader>
      <CardContent className="p-3">
        <div className="flex flex-col gap-0">
          {steps.map((label, index) => (
            <div key={`${index}-${label}`} className="flex flex-col items-center gap-0">
              <div className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 shadow-sm">
                <span className="text-slate-500 mr-2">{index + 1}.</span>
                {label}
              </div>
              {index < steps.length - 1 && (
                <div className="flex justify-center py-1 text-slate-300">
                  <ChevronDown className="h-5 w-5" aria-hidden />
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
