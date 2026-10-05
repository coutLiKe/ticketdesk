import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { WakingNotice } from "./ui";

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <>
      <header className="topbar">
        <span className="brand">TicketDesk</span>
        <nav>
          <NavLink to="/tickets">Tickets</NavLink>
          <NavLink to="/assets">Assets</NavLink>
          {user?.role === "admin" && <NavLink to="/users">Users</NavLink>}
        </nav>
        <span className="spacer" />
        <span className="who">
          {user?.full_name} <span className="badge role">{user?.role}</span>
        </span>
        <button className="link" onClick={logout}>
          Log out
        </button>
      </header>
      <main className="container">
        <WakingNotice />
        <Outlet />
      </main>
    </>
  );
}
