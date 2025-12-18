import { useState } from 'react'
import axios from 'axios'
import { Play, Loader2 } from 'lucide-react'

interface TestRunnerProps {
    apkPath: string | null;
    onRunStart: (runId: string) => void;
}

export default function TestRunner({ apkPath, onRunStart }: TestRunnerProps) {
    const [testPrompt, setTestPrompt] = useState('')
    const [loading, setLoading] = useState(false)
    const [started, setStarted] = useState(false)

    const startTest = async () => {
        if (!apkPath) return alert("Please upload APK first")
        if (!testPrompt) return alert("Please enter test instructions")

        setLoading(true)
        try {
            const res = await axios.post('http://localhost:8000/test/start', {
                apk_path: apkPath,
                test_prompt: testPrompt
            })
            
            const runId = res.data.run_id
            onRunStart(runId)
            setStarted(true)
            setLoading(false)
        } catch (e) {
            console.error(e)
            alert("Failed to start test")
            setLoading(false)
        }
    }

    const resetTest = () => {
        setStarted(false)
        setTestPrompt('')
    }

    return (
        <div className="space-y-4">
            <textarea
                className="w-full h-32 bg-slate-900/50 border border-slate-700 rounded-lg p-4 text-slate-200 focus:ring-2 focus:ring-purple-500 focus:outline-none resize-none placeholder-slate-500"
                placeholder="Describe your test (e.g., 'Log in with user@example.com and verify dashboard')"
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                disabled={loading || started}
            ></textarea>
            
            <div className="flex gap-2">
                {!started ? (
                    <button
                        onClick={startTest}
                        disabled={loading || !apkPath}
                        className="flex items-center justify-center gap-2 px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-lg font-medium transition-all w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20"
                    >
                        {loading ? (
                            <>
                                <Loader2 size={18} className="animate-spin" />
                                Starting...
                            </>
                        ) : (
                            <>
                                <Play size={18} /> Start Test Agent
                            </>
                        )}
                    </button>
                ) : (
                    <button
                        onClick={resetTest}
                        className="flex items-center justify-center gap-2 px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-all w-full sm:w-auto"
                    >
                        Start New Test
                    </button>
                )}
            </div>
        </div>
    )
}