import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ShieldCheck, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function Register() {
  const { register, login } = useAuth();
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    role: "auditor",
  });
  const [submitting, setSubmitting] = useState(false);
  const nav = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await register(form);
      await login(form.email, form.password);
      toast.success("Account created.");
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-6 py-10" data-testid="register-page">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-primary flex items-center justify-center">
            <ShieldCheck className="w-6 h-6 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <div className="font-heading font-black text-xl leading-none">SentinelAI</div>
            <div className="text-[10px] tracking-overline uppercase text-muted-foreground mt-1">
              Create account
            </div>
          </div>
        </div>

        <h1 className="font-heading text-4xl font-bold tracking-tight mb-2">Register</h1>
        <p className="text-sm text-muted-foreground mb-8">
          Provision a SentinelAI account.
        </p>

        <form onSubmit={onSubmit} className="space-y-4" data-testid="register-form">
          <div className="space-y-2">
            <Label className="text-xs tracking-overline uppercase font-semibold">Full Name</Label>
            <Input
              required minLength={1}
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              data-testid="register-name-input"
              className="rounded-sm h-11"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs tracking-overline uppercase font-semibold">Email</Label>
            <Input
              type="email" required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              data-testid="register-email-input"
              className="rounded-sm h-11"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs tracking-overline uppercase font-semibold">Password</Label>
            <Input
              type="password" required minLength={6}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              data-testid="register-password-input"
              className="rounded-sm h-11"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs tracking-overline uppercase font-semibold">Role</Label>
            <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
              <SelectTrigger data-testid="register-role-select" className="rounded-sm h-11">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="viewer">Viewer · Read-only</SelectItem>
                <SelectItem value="auditor">Auditor · Run audits</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button
            type="submit"
            disabled={submitting}
            data-testid="register-submit-btn"
            className="w-full h-11 rounded-sm font-semibold bg-primary text-white hover:bg-primary/90"
          >
            {submitting ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <ArrowRight className="w-4 h-4 mr-2" />
            )}
            Create account
          </Button>
        </form>

        <div className="mt-8 pt-6 border-t border-border text-xs text-muted-foreground flex items-center justify-between">
          <span>Already have an account?</span>
          <Link to="/login" data-testid="goto-login-link" className="font-semibold text-primary hover:underline">
            Sign in →
          </Link>
        </div>
      </div>
    </div>
  );
}
