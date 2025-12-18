import { CheckCircle, XCircle, Clock, Activity } from 'lucide-react'
import { useEffect, useState } from 'react'

interface ResultsViewerProps {
    currentData: any;
}

export default function ResultsViewer({ currentData }: ResultsViewerProps) {
    const [screenshot, setScreenshot] = useState<string | null>(null)
    const [status, setStatus] = useState<string>('idle')
    const [currentTask, setCurrentTask] = useState<string>('')
    const [taskProgress, setTaskProgress] = useState<{ current: number, total: number }>({ current: 0, total: 0 })


    useEffect(() => {
        console.log(currentData);
        if (!currentData) return

        // Update screenshot if available
        if (currentData.type === 'screenshot' && currentData.data) {
            console.log('ResultsViewer: Received new screenshot', currentData.data.substring(0, 50) + '...')
            setScreenshot(currentData.data)
        } else if (currentData.data && currentData.type !== 'action_plan') {
            // Fallback for legacy or other message types containing data
            setScreenshot(currentData.data)
        }

        // Update status
        if (currentData.status) {
            setStatus(currentData.status)
        }

        // Update current task
        if (currentData.task) {
            setCurrentTask(currentData.task)
        }

        // Update task progress
        if (currentData.task_number && currentData.total_tasks) {
            setTaskProgress({
                current: currentData.task_number,
                total: currentData.total_tasks
            })
        }
    }, [currentData])

    const getStatusIcon = () => {
        switch (status) {
            case 'passed':
                return <CheckCircle className="text-emerald-500" size={20} />
            case 'failed':
                return <XCircle className="text-rose-500" size={20} />
            case 'running':
                return <Activity className="text-blue-500 animate-pulse" size={20} />
            case 'timeout':
                return <Clock className="text-amber-500" size={20} />
            default:
                return <Activity className="text-slate-500" size={20} />
        }
    }

    const getStatusColor = () => {
        switch (status) {
            case 'passed':
                return 'text-emerald-400'
            case 'failed':
                return 'text-rose-400'
            case 'running':
                return 'text-blue-400'
            case 'timeout':
                return 'text-amber-400'
            default:
                return 'text-slate-400'
        }
    }

    return (
        <div className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden h-[600px] flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between">
                <h3 className="font-semibold text-slate-200">Emulator View</h3>
                <div className="flex items-center gap-3">
                    {getStatusIcon()}
                    <span className={`text-xs font-mono font-semibold ${getStatusColor()}`}>
                        {status.toUpperCase()}
                    </span>
                </div>
            </div>

            {/* Screenshot */}
            <div className="flex-1 flex items-center justify-center bg-slate-950 relative overflow-hidden">
                {screenshot ? (
                    <img
                        src={`data:image/png;base64,${screenshot}`}
                        alt="Emulator Screenshot"
                        className="max-h-full max-w-full object-contain"
                    />
                ) : (
                    <div className="text-slate-500 flex flex-col items-center gap-3">
                        <Activity className="animate-pulse" size={32} />
                        <span>Waiting for screenshot...</span>
                    </div>
                )}

                {/* Task Progress Overlay */}
                {taskProgress.total > 0 && (
                    <div className="absolute top-4 left-4 right-4 bg-black/80 backdrop-blur-md rounded-lg p-3 border border-slate-700">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-semibold text-slate-300">
                                Task {taskProgress.current} of {taskProgress.total}
                            </span>
                            <span className="text-xs text-slate-400">
                                {Math.round((taskProgress.current / taskProgress.total) * 100)}%
                            </span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                            <div
                                className="bg-gradient-to-r from-purple-500 to-pink-500 h-full transition-all duration-300"
                                style={{ width: `${(taskProgress.current / taskProgress.total) * 100}%` }}
                            ></div>
                        </div>
                        {currentTask && (
                            <div className="mt-2 text-xs text-slate-300 line-clamp-2">
                                {currentTask}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}