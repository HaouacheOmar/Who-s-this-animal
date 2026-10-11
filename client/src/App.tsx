import { Route, Routes } from 'react-router-dom'
import { RequireAuth } from '@/lib/auth'
import { Page } from '@/components/Page'
import Landing from '@/pages/Landing'
import { ForgotPassword, Login, ResetPassword, Signup, VerifyEmail } from '@/pages/Auth'
import Layout from '@/pages/app/Layout'
import Home from '@/pages/app/Home'
import ScanResult from '@/pages/app/ScanResult'
import History from '@/pages/app/History'
import Pets from '@/pages/app/Pets'
import PetDetail from '@/pages/app/PetDetail'
import Shops from '@/pages/app/Shops'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<Page><Signup /></Page>} />
      <Route path="/login" element={<Page><Login /></Page>} />
      <Route path="/verify-email/:uid/:token" element={<Page><VerifyEmail /></Page>} />
      <Route path="/forgot-password" element={<Page><ForgotPassword /></Page>} />
      <Route path="/reset-password/:uid/:token" element={<Page><ResetPassword /></Page>} />
      <Route path="/app" element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Home />} />
        <Route path="scans/:id" element={<ScanResult />} />
        <Route path="history" element={<History />} />
        <Route path="pets" element={<Pets />} />
        <Route path="pets/:id" element={<PetDetail />} />
        <Route path="shops" element={<Shops />} />
      </Route>
    </Routes>
  )
}
