import React, { useState } from "react";
import { useNavigate, Link, Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShieldCheck, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function Login() {
  const { login, user } = useAuth();
  const [email, setEmail] = useState("admin@sentinel.ai");
  const [password, setPassword] = useState("Admin@2026");
  const [submitting, setSubmitting] = useState(false);
  const nav = useNavigate();

  if (user) return <Navigate to="/dashboard" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(email, password);
      toast.success("Authenticated");
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="login-page">
      {/* Left: branding panel */}
      <div className="hidden lg:flex w-1/2 bg-[#0A0A0A] text-white flex-col justify-between p-12 relative overflow-hidden">
        <div className="grid-bg absolute inset-0 opacity-50" />
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 bg-primary flex items-center justify-center">
            <ShieldCheck className="w-6 h-6" strokeWidth={2.5} />
          </div>
          <div>
            <div className="font-heading font-black text-xl leading-none">SentinelAI</div>
            <div className="text-[10px] tracking-overline uppercase text-white/50 mt-1">
              Multi-Agent Audit Framework
            </div>
          </div>
        </div>

        <div className="relative z-10 max-w-md">
          <div className="text-xs tracking-overline uppercase text-primary font-semibold mb-3">
            Enterprise Audit Intelligence
          </div>
          <h2 className="font-heading text-5xl font-black tracking-tight leading-[0.95]">
            Eight specialized agents.<br />
            One unified verdict.
          </h2>
          <p className="text-white/60 mt-6 text-sm leading-relaxed">
            Autonomous financial intelligence platform built for Big Four audit teams,
            Fortune 500 CFOs, and fraud investigation units. Powered by Google Gemini.
          </p>

          <div className="mt-12 grid grid-cols-2 gap-x-8 gap-y-5 text-xs">
            {[
              ["8", "Specialized Agents"],
              ["SOX", "GAAP / IFRS"],
              ["100K+", "Rows Per Audit"],
              ["JWT", "Zero-Trust Auth"],
            ].map(([v, k]) => (
              <div key={k}>
                <div className="font-heading text-3xl font-bold text-white">{v}</div>
                <div className="text-white/50 tracking-overline uppercase mt-1">{k}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 text-[10px] tracking-overline uppercase text-white/30">
          © 2026 SentinelAI · Kaggle ADK Capstone
        </div>
      </div>

      {/* Right: login form */}
      <div className="flex-1 flex items-center justify-center px-6 py-10 bg-white">
        <div className="w-full max-w-md">
          <div className="text-xs tracking-overline uppercase text-primary font-semibold mb-2">
            Secure Login
          </div>
          <h1 className="font-heading text-4xl font-bold tracking-tight mb-2">
            Welcome back.
          </h1>
          <p className="text-sm text-muted-foreground mb-8">
            Authenticate to access the SentinelAI command center.
          </p>

          <form onSubmit={onSubmit} className="space-y-5" data-testid="login-form">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-xs tracking-overline uppercase font-semibold">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email-input"
                className="rounded-sm h-11"
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-xs tracking-overline uppercase font-semibold">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="login-password-input"
                className="rounded-sm h-11"
                autoComplete="current-password"
              />
            </div>

            <Button
              type="submit"
              disabled={submitting}
              data-testid="login-submit-btn"
              className="w-full h-11 rounded-sm font-semibold bg-primary text-white hover:bg-primary/90"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <ArrowRight className="w-4 h-4 mr-2" />
              )}
              Authenticate
            </Button>
          </form>

          <div className="mt-8 pt-6 border-t border-border text-xs text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Don't have an account?</span>
              <Link
                to="/register"
                data-testid="goto-register-link"
                className="font-semibold text-primary hover:underline"
              >
                Register →
              </Link>
            </div>
            <div className="mt-4 p-3 bg-muted text-[11px] font-mono leading-relaxed">
              <div className="text-[10px] tracking-overline uppercase font-semibold text-muted-foreground mb-1">
                Demo Accounts
              </div>
              admin@sentinel.ai / Admin@2026<br />
              auditor@sentinel.ai / Auditor@2026<br />
              viewer@sentinel.ai / Viewer@2026
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
