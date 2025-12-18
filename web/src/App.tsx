import { useState } from 'react'
import Upload from './components/Upload'
import TestRunner from './components/TestRunner'
import ResultsViewer from './components/ResultsViewer'
import ChatInterface from './components/ChatInterface'

function App() {
  const [apkPath, setApkPath] = useState<string | null>(null)
  const [runId, setRunId] = useState<string | null>(null)
  const [currentData, setCurrentData] = useState<any>(null)

  const handleRunStart = (id: string) => {
    setRunId(id)
    setCurrentData(null) // Reset previous data
  }

  const handleStatusUpdate = (data: any) => {
    setCurrentData(data)
  }

  return (
    <div className="min-h-screen bg-dark text-white font-sans selection:bg-pink-500 selection:text-white">
      <div className="max-w-7xl mx-auto px-4 py-12">
        <header className="mb-12 text-center">
          <h1 className="text-5xl font-extrabold bg-gradient-to-r from-indigo-400 to-pink-500 bg-clip-text text-transparent mb-4">
            Zendroid
          </h1>
          <p className="text-slate-400 text-lg">AI-Powered Mobile Test Automation with Real-time Chat</p>
        </header>

        <div className="grid gap-8">
          <div className="glass-card p-6 rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-xl shadow-2xl">
            <h2 className="text-xl font-semibold mb-4 text-indigo-300">1. Upload App</h2>
            <Upload onUploadSuccess={(path) => setApkPath(path)} />
          </div>

          <div className={`glass-card p-6 rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-xl shadow-2xl transition-all duration-500 ${!apkPath ? 'opacity-50 pointer-events-none grayscale' : ''}`}>
            <h2 className="text-xl font-semibold mb-4 text-purple-300">2. Run Test</h2>
            <TestRunner apkPath={apkPath} onRunStart={handleRunStart} />
          </div>

          {runId && (
            <div className="glass-card p-6 rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-xl shadow-2xl">
              <h2 className="text-xl font-semibold mb-4 text-pink-300">3. Live Execution</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left: Emulator View */}
                <ResultsViewer currentData={currentData} />
                
                {/* Right: Chat Interface */}
                <div className="h-[600px]">
                  <ChatInterface 
                    runId={runId} 
                    onStatusUpdate={handleStatusUpdate}
                  />
                </div>
              </div>
            </div>
          )}

          {!runId && (
            <div className="glass-card p-6 rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-xl shadow-2xl">
              <h2 className="text-xl font-semibold mb-4 text-pink-300">3. Live Execution</h2>
              <div className="flex flex-col items-center justify-center h-64 text-slate-500 space-y-2 border border-dashed border-slate-700 rounded-xl bg-slate-800/20">
                <svg className="w-16 h-16 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <p className="text-lg">Start a test to see live execution</p>
                <p className="text-sm text-slate-600">Chat with the agent in real-time</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App