import { CheckCircle, XCircle, Terminal, Activity } from 'lucide-react'

interface HistoryItem {
    role: string;
    content?: string;
    action?: string;
    reason?: string;
    params?: any;
}

interface RunData {
    status: string;
    screenshot?: string;
    history: HistoryItem[];
}

interface ResultsViewerProps {
    runData: RunData | null;
}

export default function ResultsViewer({ runData }: ResultsViewerProps) {
    if (!runData) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-slate-500 space-y-2 border border-dashed border-slate-700 rounded-xl bg-slate-800/20">
                <Activity size={32} />
                <p>No test results yet. Run a test to see details.</p>
            </div>
        )
    }

    const { status, screenshot, history } = runData

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[600px]">
            {/* Left: Emulator View */}
            <div className="bg-slate-900 rounded-xl border border-slate-700 flex items-center justify-center relative overflow-hidden group">
                {screenshot ? (
                    <img src={`data:image/png;base64,${screenshot}`} alt="Emulator Screenshot" className="max-h-full max-w-full object-contain" />
                ) : (
                    <div className="text-slate-500 flex flex-col items-center gap-2">
                        <Activity className="animate-pulse" />
                        <span>Waiting for screenshot...</span>
                    </div>
                )}
                <div className="absolute top-4 right-4 bg-black/70 px-3 py-1 rounded-full text-xs font-mono backdrop-blur-md">
                    Status: <span className={status === 'passed' ? 'text-emerald-400' : status === 'failed' ? 'text-rose-400' : 'text-amber-400'}>{status.toUpperCase()}</span>
                </div>
            </div>

            {/* Right: Logs / History */}
            <div className="bg-slate-900 rounded-xl border border-slate-700 flex flex-col overflow-hidden">
                <div className="p-4 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between">
                    <h3 className="font-semibold text-slate-200 flex items-center gap-2"><Terminal size={16} /> Execution Log</h3>
                    {status === 'passed' && <CheckCircle className="text-emerald-500" />}
                    {status === 'failed' && <XCircle className="text-rose-500" />}
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-sm relative">
                    {history && history.length > 0 ? history.map((item, idx) => (
                        <div key={idx} className={`p-3 rounded-lg border ${item.role === 'model' ? 'bg-indigo-500/10 border-indigo-500/20' : 'bg-slate-800 border-slate-700'}`}>
                            <div className="flex items-center gap-2 mb-1">
                                <span className={`text-xs font-bold px-2 py-0.5 rounded ${item.role === 'model' ? 'bg-indigo-500 text-white' : 'bg-slate-600 text-slate-300'}`}>
                                    {item.role.toUpperCase()}
                                </span>
                            </div>
                            <div className="text-slate-300 break-words whitespace-pre-wrap">
                                {item.role === 'model' ? (
                                    <>
                                        <div className="font-semibold text-indigo-300">{item.action?.toUpperCase()}</div>
                                        {item.reason && <div className="text-slate-400 text-xs italic mt-1">"{item.reason}"</div>}
                                        {item.params && <pre className="mt-2 text-xs text-slate-500 bg-black/20 p-2 rounded overflow-x-auto">{JSON.stringify(item.params, null, 2)}</pre>}
                                    </>
                                ) : (
                                    item.content
                                )}
                            </div>
                        </div>
                    )) : (
                        <p className="text-slate-500 italic">Logs will appear here...</p>
                    )}
                </div>
            </div>
        </div>
    )
}
