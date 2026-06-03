// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Search from './pages/Search';
import Entity from './pages/Entity';
import Chat from './pages/chat';
import Pipeline from './pages/pipeline';
import Developer from './pages/Developer';
import Duplicates from './pages/Duplicates';
import { ToastProvider } from './context/ToastContext';
import { BreadcrumbProvider } from './context/BreadcrumbContext';
import { ThemeProvider } from './context/ThemeContext';

function App() {
  return (
    <ThemeProvider>
      <BreadcrumbProvider>
        <ToastProvider>
          <BrowserRouter>
          <div className="app-container">
            <Header />
            <Sidebar />
            <div className="main-wrapper">
              <div className="main-content">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/search" element={<Search />} />
                  <Route path="/search/:query" element={<Search />} />
                  <Route path="/chat" element={<Chat />} />
                  <Route path="/entity/:id" element={<Entity />} />
                  <Route path="/pipeline/*" element={<Pipeline />} />
                  <Route path="/duplicates" element={<Duplicates />} />
                  <Route path="/developer" element={<Developer />} />
                </Routes>
              </div>
              <Footer />
            </div>
          </div>
        </BrowserRouter>
        </ToastProvider>
      </BreadcrumbProvider>
    </ThemeProvider>
  );
}

export default App;
