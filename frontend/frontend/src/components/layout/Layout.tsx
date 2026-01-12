import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, ShieldCheck, FileText, Menu, X } from "lucide-react";
import { Button } from "../ui/button";
import { Sheet, SheetContent, SheetTrigger } from "../ui/sheet";
import { cn } from "../../lib/utils";

const menuItems = [
  { icon: LayoutDashboard, label: "Overview", href: "/" },
  { icon: ShieldCheck, label: "Run Audit", href: "/audit" },
  { icon: FileText, label: "Reports", href: "/reports" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [open, setOpen] = useState(false);

  const NavContent = () => (
    <div className="py-4 h-full flex flex-col bg-slate-900 text-white">
       <div className="mb-8 px-6 flex items-center gap-2">
        <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <ShieldCheck className="h-5 w-5 text-white" />
        </div>
        <span className="text-xl font-bold">AuditGenius</span>
      </div>
      <nav className="px-2 space-y-1 flex-1">
        {menuItems.map((item) => (
          <Link
            key={item.href}
            to={item.href}
            onClick={() => setOpen(false)}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
              location.pathname === item.href 
                ? "bg-slate-800 text-blue-400 shadow-sm" 
                : "text-slate-400 hover:text-white hover:bg-slate-800/50"
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="p-4 bg-slate-800/50 m-2 rounded-lg">
        <div className="flex items-center gap-2">
            <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs text-green-400 font-medium">System Online</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex w-64 flex-col fixed inset-y-0 z-50">
        <NavContent />
      </div>

      {/* Main Content */}
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen transition-all duration-300">
        <div className="md:hidden sticky top-0 z-40 bg-white border-b p-4 flex items-center justify-between shadow-sm">
            <span className="font-bold text-lg text-slate-900">AuditGenius</span>
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon"><Menu className="h-6 w-6" /></Button>
              </SheetTrigger>
              <SheetContent side="left" className="p-0 w-64 border-r-0">
                <NavContent />
              </SheetContent>
            </Sheet>
        </div>
        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-7xl mx-auto w-full">
            {children}
        </main>
      </div>
    </div>
  );
}