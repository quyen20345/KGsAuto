// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Home from './pages/Home';
import Search from './pages/Search';
import Entity from './pages/Entity';
import Merge from './pages/Merge';
import Chat from './pages/chat';
import Pipeline from './pages/pipeline';

function App() {
  return (
    <BrowserRouter>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/search" element={<Search />} />
        <Route path="/search/:query" element={<Search />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/entity/:id" element={<Entity />} />
        <Route path="/merge" element={<Merge />} />
        <Route path="/pipeline/*" element={<Pipeline />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
