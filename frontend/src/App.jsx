// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Home from './pages/Home';
import Search from './pages/Search';
import Entity from './pages/Entity';
import Query from './pages/Query';
import Visualize from './pages/Visualize';

function App() {
  return (
    <BrowserRouter>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/search/:query" element={<Search />} />
        <Route path="/entity/:id" element={<Entity />} />
        <Route path="/query" element={<Query />} />
        <Route path="/visualize" element={<Visualize />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;