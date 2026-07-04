import React, { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { PageHeader } from "@/components/Common";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState(null);
  
  const [confirmDialog, setConfirmDialog] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await adminApi.users();
      setUsers(res.data.users || []);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (id, payload) => {
    setUpdatingId(id);
    try {
      await adminApi.updateUser(id, payload);
      setUsers(users.map(u => u.id === id ? { ...u, ...payload } : u));
      toast.success("User updated successfully");
    } catch (e) {
      toast.error("Failed to update user");
    } finally {
      setUpdatingId(null);
      setConfirmDialog(null);
    }
  };

  const onRoleChange = (id, newRole) => {
    if (newRole === "admin") {
      setConfirmDialog({
        title: "Promote to Admin?",
        desc: "This will grant the user full system access.",
        action: () => handleUpdate(id, { role: newRole })
      });
    } else {
      handleUpdate(id, { role: newRole });
    }
  };

  const onActiveToggle = (id, currentActive) => {
    const newActive = !currentActive;
    if (!newActive) {
      setConfirmDialog({
        title: "Deactivate User?",
        desc: "This user will immediately lose access to the system.",
        action: () => handleUpdate(id, { active: newActive })
      });
    } else {
      handleUpdate(id, { active: newActive });
    }
  };

  return (
    <div data-testid="admin-users-page">
      <PageHeader
        overline="Administration"
        title="User management"
        description="All accounts provisioned in the SentinelAI tenant."
      />
      
      {confirmDialog && (
        <AlertDialog open={!!confirmDialog} onOpenChange={(open) => !open && setConfirmDialog(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{confirmDialog.title}</AlertDialogTitle>
              <AlertDialogDescription>{confirmDialog.desc}</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={confirmDialog.action} className="bg-destructive text-white hover:bg-destructive/90">
                Confirm
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {loading ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="border border-border bg-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr className="text-[10px] tracking-overline uppercase text-muted-foreground">
                <th className="text-left font-semibold px-4 py-3">Email</th>
                <th className="text-left font-semibold px-4 py-3">Name</th>
                <th className="text-left font-semibold px-4 py-3">Role</th>
                <th className="text-left font-semibold px-4 py-3">Status</th>
                <th className="text-left font-semibold px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isUpdating = updatingId === u.id;
                return (
                  <tr key={u.id} className="border-t border-border hover:bg-muted/40" data-testid={`user-row-${u.id}`}>
                    <td className="px-4 py-3 font-mono text-xs">{u.email}</td>
                    <td className="px-4 py-3 font-medium">{u.full_name}</td>
                    <td className="px-4 py-3">
                      <Select 
                        value={u.role} 
                        onValueChange={(val) => onRoleChange(u.id, val)}
                        disabled={isUpdating}
                      >
                        <SelectTrigger className="w-[120px] h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="admin">Admin</SelectItem>
                          <SelectItem value="auditor">Auditor</SelectItem>
                          <SelectItem value="viewer">Viewer</SelectItem>
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-4 py-3 flex items-center gap-2">
                      <Switch 
                        checked={u.active} 
                        onCheckedChange={() => onActiveToggle(u.id, u.active)} 
                        disabled={isUpdating}
                      />
                      <span className={`text-[10px] tracking-overline uppercase font-bold px-2 py-0.5 ${u.active ? "text-success" : "text-destructive"}`}>
                        {u.active ? "Active" : "Disabled"}
                      </span>
                      {isUpdating && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground font-mono">
                      {u.created_at ? new Date(u.created_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
