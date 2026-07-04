import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { Toaster } from "sonner";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import UploadPage from "@/pages/Upload";
import Audits from "@/pages/Audits";
import AuditDetail from "@/pages/AuditDetail";
import AgentRoster from "@/pages/AgentRoster";
import AdminUsers from "@/pages/AdminUsers";
import AdminLogs from "@/pages/AdminLogs";

const ROLE_RANK = { admin: 3, auditor: 2, viewer: 1 };

function Protected({ children, role }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (role && ROLE_RANK[user.role] < ROLE_RANK[role]) return <Navigate to="/dashboard" replace />;
  return <Layout>{children}</Layout>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/upload" element={<Protected role="auditor"><UploadPage /></Protected>} />
      <Route path="/audits" element={<Protected><Audits /></Protected>} />
      <Route path="/audits/:id" element={<Protected><AuditDetail /></Protected>} />
      <Route path="/agents" element={<Protected><AgentRoster /></Protected>} />
      <Route path="/admin/users" element={<Protected role="admin"><AdminUsers /></Protected>} />
      <Route path="/admin/logs" element={<Protected role="admin"><AdminLogs /></Protected>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="top-right" richColors closeButton />
      </AuthProvider>
    </BrowserRouter>
  );
}
