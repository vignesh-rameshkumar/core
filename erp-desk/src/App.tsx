import { BrowserRouter } from 'react-router-dom'
import './App.css'
import { FrappeProvider } from 'frappe-react-sdk'
import "react-toastify/dist/ReactToastify.css";
import { ToastContainer } from 'react-toastify'
import RootNavigation from './Navigation/RootNavigation';
import { Provider } from 'react-redux';
import { store } from './Store';
function App() {

  return (
    <FrappeProvider socketPort={import.meta.env.VITE_SOCKET_PORT ?? ""}>
      <Provider store={store}>
        <BrowserRouter>
          <ToastContainer pauseOnFocusLoss={false} />
          <RootNavigation />
        </BrowserRouter>
      </Provider>
    </FrappeProvider>
  )
}
export default App
