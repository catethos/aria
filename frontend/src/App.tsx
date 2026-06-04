import Dashboard from "./pages/Dashboard";
import EvidenceGraphPage from "./pages/EvidenceGraph";
import "./App.css";

function App() {
  if (window.location.pathname === "/evidence") {
    return <EvidenceGraphPage />;
  }
  return <Dashboard />;
}

export default App;
