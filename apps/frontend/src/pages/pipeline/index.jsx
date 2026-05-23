import { Routes, Route, NavLink } from 'react-router-dom';
import PipelineDashboard from './PipelineDashboard';
import FileBrowser from './FileBrowser';
import RunHistory from './RunHistory';
import RunDetail from './RunDetail';

export default function Pipeline() {
  return (
    <div className="pipeline-page">
      <nav className="pipeline-tabs">
        <NavLink to="/pipeline" end>Dashboard</NavLink>
        <NavLink to="/pipeline/files">Files</NavLink>
        <NavLink to="/pipeline/runs">Runs</NavLink>
      </nav>
      <div className="pipeline-content">
        <Routes>
          <Route index element={<PipelineDashboard />} />
          <Route path="files" element={<FileBrowser />} />
          <Route path="runs" element={<RunHistory />} />
          <Route path="runs/:runId" element={<RunDetail />} />
        </Routes>
      </div>
    </div>
  );
}
