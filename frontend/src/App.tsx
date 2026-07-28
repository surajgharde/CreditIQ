import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import NewAnalysis from './pages/NewAnalysis';
import Analysis from './pages/Analysis';
import Dashboard from './pages/Dashboard';
import FraudReport from './pages/FraudReport';
import WarningSystem from './pages/WarningSystem';
import CamSuccess from './pages/CamSuccess';
import History from './pages/History';

import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          
          <Route path="/admin-dashboard" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
          <Route path="/new-analysis" element={<ProtectedRoute><NewAnalysis /></ProtectedRoute>} />
          <Route path="/newanalysis" element={<ProtectedRoute><NewAnalysis /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
          <Route path="/analysis" element={<ProtectedRoute><Analysis /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/fraud-report" element={<ProtectedRoute><FraudReport /></ProtectedRoute>} />
          <Route path="/warning-system" element={<ProtectedRoute><WarningSystem /></ProtectedRoute>} />
          <Route path="/cam-success" element={<ProtectedRoute><CamSuccess /></ProtectedRoute>} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
