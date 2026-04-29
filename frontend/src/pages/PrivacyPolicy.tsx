import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Shield } from "lucide-react";

export function PrivacyPolicy() {
  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in">
      <div className="flex items-center gap-3">
        <Shield className="h-10 w-10 text-slate-600" />
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Privacy Policy</h1>
          <p className="text-slate-500 text-sm">Last updated: February 2025</p>
        </div>
      </div>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg">1. Introduction</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <p>
            AuditGenius (“we”, “our”, or “us”) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, store, and protect information when you use our AI-powered compliance assessment and audit services.
          </p>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg">2. Information We Collect</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <p>We may collect:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Account information:</strong> Email, name, and authentication data (e.g. via Clerk) when you sign in.</li>
            <li><strong>Conversation and assessment data:</strong> Messages you send in the Compliance Chat, and system-generated risk classifications, facts, and obligations derived from your inputs.</li>
            <li><strong>Technical data:</strong> IP address, browser type, and usage data to operate and improve our services.</li>
          </ul>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg">3. How We Use Your Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <p>We use the information to:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Provide and improve our compliance chat, risk assessment, and report generation.</li>
            <li>Authenticate users and manage accounts.</li>
            <li>Comply with applicable law and protect our rights.</li>
          </ul>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg">4. Data Storage and Security</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <p>
            Assessment and chat data are stored on our servers. We use industry-standard measures to protect your data. We do not sell your personal information to third parties.
          </p>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg">5. Your Rights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <p>
            Depending on your jurisdiction, you may have the right to access, correct, or delete your personal data. To exercise these rights or ask questions about this policy, please contact us using the details provided in our app or website.
          </p>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg">6. Changes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <p>
            We may update this Privacy Policy from time to time. The “Last updated” date at the top will reflect the latest version. Continued use of our services after changes constitutes acceptance of the updated policy.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
