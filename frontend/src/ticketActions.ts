import type { TicketStatus } from "./api";

export interface StatusAction {
  to: TicketStatus;
  text: string;
}

// Mirrors the server's state machine so the UI only offers moves the API will accept.
// The server re-checks every move; this is for convenience, not security.
export function nextActions(status: TicketStatus, staff: boolean): StatusAction[] {
  switch (status) {
    case "open":
      return staff ? [{ to: "in_progress", text: "Start work" }] : [];
    case "in_progress":
      return staff ? [{ to: "resolved", text: "Mark resolved" }] : [];
    case "resolved":
      // Requesters may confirm the fix or reopen; staff may do the same.
      return [
        { to: "closed", text: "Close ticket" },
        { to: "in_progress", text: "Reopen" },
      ];
    default:
      return [];
  }
}
