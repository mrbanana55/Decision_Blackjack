import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { SimulationProvider } from './context/SimulationContext';
import { ConfigurationPage } from './pages/ConfigurationPage';
import { FastBatchPage } from './pages/FastBatchPage';
import { VisualizerPage } from './pages/VisualizerPage';
import { CompletionPage } from './pages/CompletionPage';

export default function App() {
  return (
    <SimulationProvider>
      <BrowserRouter>
        <div className="min-h-screen discord-canvas-mesh text-white flex flex-col font-sans">
          <Routes>
            <Route path="/" element={<ConfigurationPage />} />
            <Route path="/batch/:sessionId" element={<FastBatchPage />} />
            <Route path="/simulate/:sessionId" element={<VisualizerPage />} />
            <Route path="/complete/:sessionId" element={<CompletionPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </SimulationProvider>
  );
}
