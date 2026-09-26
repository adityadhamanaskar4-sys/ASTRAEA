import Sidebar from './Sidebar';

export default function ConsoleShell({ children }) {
  return (
    <div className="shell">
      <Sidebar />
      <main className="main scrollbar">{children}</main>
    </div>
  );
}
