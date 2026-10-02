import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Cases from './pages/Cases';
import Evidence from './pages/Evidence';
import Investigation from './pages/Investigation';
import Timeline from './pages/Timeline';
import Integrity from './pages/Integrity';
import Reports from './pages/Reports';
import Cameras from './pages/Cameras';

import Login from './pages/Login';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="cases" element={<Cases />} />
          <Route path="cases/:id" element={<Cases />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="cameras" element={<Cameras />} />
          <Route path="investigation" element={<Investigation />} />
          <Route path="timeline" element={<Timeline />} />
          <Route path="integrity" element={<Integrity />} />
          <Route path="reports" element={<Reports />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
