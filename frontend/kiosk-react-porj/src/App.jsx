import { Route, Routes } from 'react-router-dom';
import AssistantShell from './components/AssistantShell/AssistantShell.jsx';
import { AuthProvider } from './doctor/AuthContext.jsx';
import DoctorLayout from './doctor/DoctorLayout.jsx';
import LoginPage from './doctor/LoginPage.jsx';
import ProfilePage from './doctor/ProfilePage.jsx';
import ProtectedRoute from './doctor/ProtectedRoute.jsx';
import SlipPage from './doctor/SlipPage.jsx';
import TokenListPage from './doctor/TokenListPage.jsx';
import VisitPage from './doctor/VisitPage.jsx';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<AssistantShell />} />
        <Route path="/s/:slipId" element={<SlipPage />} />
        <Route path="/dr/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/dr" element={<DoctorLayout />}>
            <Route index element={<TokenListPage scope="current" />} />
            <Route path="history" element={<TokenListPage scope="past" />} />
            <Route path="visit/:visitId" element={<VisitPage />} />
            <Route path="profile" element={<ProfilePage />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  );
}