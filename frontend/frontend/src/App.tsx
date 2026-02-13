import { ClerkProvider, SignedIn, SignedOut, RedirectToSignIn, UserButton } from "@clerk/clerk-react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { AuditRun } from "./pages/AuditRun";
import { Reports } from "./pages/Reports";
import { GovernanceChat } from "./pages/GovernanceChat";
import { PrivacyPolicy } from "./pages/PrivacyPolicy";
import { TermsOfUse } from "./pages/TermsOfUse";
import { LayoutDashboard, ShieldAlert, FileText, Scale, Lock, FileCheck } from "lucide-react";

// Replace with your actual Clerk Key
const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error("Missing Publishable Key");
}

function App() {
  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      <Router>
        <SignedIn>
          <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans">
            {/* Sidebar */}
            <aside className="w-64 bg-slate-900 text-white flex flex-col fixed h-full shadow-xl z-50">
              <div className="p-6 border-b border-slate-700">
                <div className="flex items-center gap-2 font-bold text-xl tracking-tight">
                  <ShieldAlert className="text-blue-400" /> AuditGenius
                </div>
              </div>
              
              <nav className="flex-1 p-4 space-y-2">
                <Link to="/" className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium">
                  <LayoutDashboard size={18} /> Dashboard
                </Link>

                {/* --- NEW MVP FEATURE --- */}
                <Link to="/governance" className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium text-blue-300">
                  <Scale size={18} /> Compliance Chat
                </Link>
                {/* ----------------------- */}

                <Link to="/audit" className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium">
                  <ShieldAlert size={18} /> Technical Audit
                </Link>
                <Link to="/reports" className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium">
                  <FileText size={18} /> History & Reports
                </Link>
                <div className="pt-2 mt-2 border-t border-slate-700">
                  <Link to="/privacy" className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium text-slate-400">
                    <Lock size={18} /> Privacy Policy
                  </Link>
                  <Link to="/terms" className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-all text-sm font-medium text-slate-400">
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
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 ml-64 p-8 overflow-y-auto">
              <div className="max-w-7xl mx-auto">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/governance" element={<GovernanceChat />} /> {/* <--- NEW ROUTE */}
                  <Route path="/audit" element={<AuditRun />} />
                  <Route path="/reports" element={<Reports />} />
                  <Route path="/privacy" element={<PrivacyPolicy />} />
                  <Route path="/terms" element={<TermsOfUse />} />
                </Routes>
              </div>
            </main>
          </div>
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