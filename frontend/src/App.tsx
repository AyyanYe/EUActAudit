import { useState } from "react";
import { ClerkProvider, SignedIn, SignedOut, RedirectToSignIn, UserButton } from "@clerk/clerk-react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { AuditRun } from "./pages/AuditRun";
import { Reports } from "./pages/Reports";
import { GovernanceChat } from "./pages/GovernanceChat";
import { PrivacyPolicy } from "./pages/PrivacyPolicy";
import { TermsOfUse } from "./pages/TermsOfUse";
import { LayoutDashboard, ShieldAlert, FileText, Scale, Lock, FileCheck, Menu } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "./components/ui/sheet";
import { Button } from "./components/ui/button";

// Replace with your actual Clerk Key
const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error("Missing Publishable Key");
}

interface SidebarContentProps {
  onClose?: () => void;
}

function SidebarContent({ onClose }: SidebarContentProps) {
  return (
    <div className="flex flex-col h-full bg-slate-900 text-white">
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-2 font-bold text-xl tracking-tight">
          <ShieldAlert className="text-blue-400" /> EUActAudit
        </div>
      </div>
      
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        <Link 
          to="/" 
          onClick={onClose}
          className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium"
        >
          <LayoutDashboard size={18} /> Dashboard
        </Link>

        {/* --- NEW MVP FEATURE --- */}
        <Link 
          to="/governance" 
          onClick={onClose}
          className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium text-blue-300"
        >
          <Scale size={18} /> Compliance Chat
        </Link>
        {/* ----------------------- */}

        <Link 
          to="/audit" 
          onClick={onClose}
          className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium"
        >
          <ShieldAlert size={18} /> Technical Audit
        </Link>
        <Link 
          to="/reports" 
          onClick={onClose}
          className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium"
        >
          <FileText size={18} /> History & Reports
        </Link>
        <div className="pt-2 mt-2 border-t border-slate-800">
          <Link 
            to="/privacy" 
            onClick={onClose}
            className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium text-slate-400"
          >
            <Lock size={18} /> Privacy Policy
          </Link>
          <Link 
            to="/terms" 
            onClick={onClose}
            className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium text-slate-400"
          >
            <FileCheck size={18} /> Terms of Use
          </Link>
        </div>
      </nav>

      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-3 px-4 py-2 rounded-lg bg-slate-800">
          {/* Clerk User Button (Avatar + Logout) */}
          <UserButton showName/> 
        </div>
      </div>
    </div>
  );
}

function MainLayout() {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans flex-col md:flex-row w-full">
      {/* Desktop Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex-col fixed h-full shadow-xl z-55 md:flex hidden">
        <SidebarContent />
      </aside>

      {/* Mobile Header / Navigation */}
      <header className="md:hidden flex items-center justify-between p-4 bg-slate-900 text-white sticky top-0 z-50 shadow-md w-full">
        <div className="flex items-center gap-2 font-bold text-lg tracking-tight">
          <ShieldAlert className="text-blue-400" size={20} /> EUActAudit
        </div>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="text-white hover:bg-slate-800">
              <Menu size={24} />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-64 border-0 bg-slate-900 text-white">
            <SidebarContent onClose={() => setOpen(false)} />
          </SheetContent>
        </Sheet>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 md:ml-64 p-4 md:p-8 overflow-y-auto w-full min-h-[calc(100vh-64px)] md:min-h-screen">
        <div className="max-w-7xl mx-auto w-full">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/governance" element={<GovernanceChat />} />
            <Route path="/audit" element={<AuditRun />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/terms" element={<TermsOfUse />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function App() {
  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      <Router>
        <SignedIn>
          <MainLayout />
        </SignedIn>

        {/* Redirect if not logged in */}
        <SignedOut>
          <RedirectToSignIn />
        </SignedOut>
      </Router>
    </ClerkProvider>
  );
}

export default App;