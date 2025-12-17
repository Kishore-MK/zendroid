import { useState, useEffect } from 'react'
import axios from 'axios'
import { Play } from 'lucide-react'

interface TestRunnerProps {
    apkPath: string | null;
    onRunUpdate: (data: any) => void;
}

export default function TestRunner({ apkPath, onRunUpdate }: TestRunnerProps) {
    const [testPrompt, setTestPrompt] = useState('')
    const [loading, setLoading] = useState(false)
    const [runId, setRunId] = useState(null)

    const startTest = async () => {
        if (!apkPath) return alert("Please upload APK first")
        if (!testPrompt) return alert("Please enter test instructions")

        setLoading(true)
        try {
            const res = await axios.post('http://localhost:8000/test', {
                apk_path: apkPath,
                test_prompt: testPrompt
            })
            setRunId(res.data.run_id)
            setLoading(false)
        } catch (e) {
            console.error(e)
            alert("Failed to start test")
            setLoading(false)
        }
    }

    useEffect(() => {
        if (!runId) return
        const interval = setInterval(async () => {
            try {
                const res = await axios.get(`http://localhost:8000/test/${runId}`)
                onRunUpdate(res.data)
            } catch (e) {
                console.error(e)
            }
        }, 2000)
        return () => clearInterval(interval)
    }, [runId, onRunUpdate])

    return (
        <div className="space-y-4">
            <textarea
                className="w-full h-32 bg-slate-900/50 border border-slate-700 rounded-lg p-4 text-slate-200 focus:ring-2 focus:ring-purple-500 focus:outline-none resize-none placeholder-slate-500"
                placeholder="Describe your test (e.g., 'Log in with user@example.com and verify dashboard')"
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                disabled={loading || !!runId}
            ></textarea>
            <button
                onClick={startTest}
                disabled={loading || !!runId || !apkPath}
                className="flex items-center justify-center gap-2 px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-lg font-medium transition-all w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20"
            >
                {loading ? 'Starting...' : runId ? 'Test Running...' : <><Play size={18} /> Start Test Agent</>}
            </button>
        </div>
    )
}
