import { useState } from 'react'
import Upload from './components/Upload'
import TestRunner from './components/TestRunner'
import ResultsViewer from './components/ResultsViewer'

function App() {
  const [apkPath, setApkPath] = useState<string | null>(null)
  const [runData, setRunData] = useState(null)

  return (
    <div className="min-h-screen bg-dark text-white font-sans selection:bg-pink-500 selection:text-white">
      <div className="max-w-6xl mx-auto px-4 py-12">
        <header className="mb-12 text-center">
          <h1 className="text-5xl font-extrabold bg-gradient-to-r from-indigo-400 to-pink-500 bg-clip-text text-transparent mb-4">
            Zendroid
          </h1>
          <p className="text-slate-400 text-lg">AI-Powered Mobile Test Automation</p>
        </header>

        <div className="grid gap-8">
          <div className="glass-card p-6 rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-xl shadow-2xl">
            <h2 className="text-xl font-semibold mb-4 text-indigo-300">1. Upload App</h2>
            <Upload onUploadSuccess={(path) => setApkPath(path)} />
          </div>

          <div className={`glass-card p-6 rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-xl shadow-2xl transition-all duration-500 ${!apkPath ? 'opacity-50 pointer-events-none grayscale' : ''}`}>
            <h2 className="text-xl font-semibold mb-4 text-purple-300">2. Run Test</h2>
            <TestRunner apkPath={apkPath} onRunUpdate={setRunData} />
          </div>

          <div className="glass-card p-6 rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-xl shadow-2xl">
            <h2 className="text-xl font-semibold mb-4 text-pink-300">3. Results</h2>
            <ResultsViewer runData={runData} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
