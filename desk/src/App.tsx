import { BrowserRouter } from 'react-router-dom'
import './App.css'
import { FrappeProvider } from 'frappe-react-sdk'
import "react-toastify/dist/ReactToastify.css";
import { ToastContainer } from 'react-toastify'
import RootNavigation from './Navigation/RootNavigation';
function App() {

  return (
    <FrappeProvider socketPort={import.meta.env.VITE_SOCKET_PORT ?? ""}>
      <BrowserRouter>
        <ToastContainer pauseOnFocusLoss={false} />
        <RootNavigation />
      </BrowserRouter>
    </FrappeProvider>
  )
}
export default App
