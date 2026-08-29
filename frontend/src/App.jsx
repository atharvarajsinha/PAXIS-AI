import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext.jsx';
import { ChatProvider } from './context/ChatContext.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import Landing from './pages/Landing.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import Chat from './pages/Chat.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Profile from './pages/Profile.jsx';

const protect = (element) => <ProtectedRoute>{element}</ProtectedRoute>;

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        {/* ChatProvider sits above the routes so an in-flight reply keeps
            streaming while the learner moves between pages. */}
        <ChatProvider>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/dashboard" element={protect(<Dashboard />)} />
            <Route path="/chat" element={protect(<Chat />)} />
            <Route path="/profile" element={protect(<Profile />)} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ChatProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
