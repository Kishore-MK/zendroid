import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

interface Message {
    type: string;
    message?: string;
    timestamp: number;
    data?: any;
}

interface ChatInterfaceProps {
    runId: string | null;
    onStatusUpdate: (data: any) => void;
}

export default function ChatInterface({ runId, onStatusUpdate }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [inputValue, setInputValue] = useState('')
    const [ws, setWs] = useState<WebSocket | null>(null)
    const [isConnected, setIsConnected] = useState(false)
    const [isWaitingForInput, setIsWaitingForInput] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    useEffect(() => {
        if (!runId) return

        const websocket = new WebSocket(`ws://localhost:8000/ws/test/${runId}`)

        websocket.onopen = () => {
            console.log('WebSocket connected')
            setIsConnected(true)
            addMessage('system', '🔗 Connected to agent')
        }

        websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                handleWebSocketMessage(data)
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e)
            }
        }

        websocket.onerror = (error) => {
            console.error('WebSocket error:', error)
            addMessage('system', '❌ Connection error')
        }

        websocket.onclose = () => {
            console.log('WebSocket disconnected')
            setIsConnected(false)
            addMessage('system', '🔌 Disconnected from agent')
        }

        setWs(websocket)

        return () => {
            websocket.close()
        }
    }, [runId])

const handleWebSocketMessage = (data: any) => {
    // ALWAYS update parent first
    onStatusUpdate(data)
    
    const msgType = data.type

        // Handle different message types
        switch (msgType) {
            case 'status':
            case 'plan':
            case 'task_start':
            case 'action_plan':
            case 'action_executed':
            case 'task_complete':
                addMessage('agent', data.message || JSON.stringify(data))
                break

            case 'screenshot':
                // Screenshot updates are handled by parent component
                break

            case 'error':
                addMessage('error', data.message || 'Unknown error occurred')
                break

            case 'error_awaiting_input':
                addMessage('error', data.message || 'Error occurred. What should I do?')
                setIsWaitingForInput(true)
                break

            case 'complete':
                addMessage('system', data.message || `Test completed with status: ${data.status}`)
                setIsWaitingForInput(false)
                break

            default:
                console.log('Unknown message type:', msgType, data)
        }
    }

    const addMessage = (type: string, message: string) => {
        setMessages(prev => [...prev, {
            type,
            message,
            timestamp: Date.now()
        }])
    }

    const sendMessage = () => {
        if (!inputValue.trim() || !ws || !isConnected) return

        ws.send(JSON.stringify({
            type: 'user_message',
            message: inputValue
        }))

        addMessage('user', inputValue)
        setInputValue('')
        setIsWaitingForInput(false)
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage()
        }
    }

    if (!runId) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-2">
                <AlertCircle size={32} />
                <p>Start a test to see agent chat</p>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full bg-slate-900 rounded-xl border border-slate-700 overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between">
                <h3 className="font-semibold text-slate-200">Agent Chat</h3>
                <div className="flex items-center gap-2">
                    {isConnected ? (
                        <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
                            Connected
                        </span>
                    ) : (
                        <span className="flex items-center gap-1.5 text-xs text-slate-500">
                            <div className="w-2 h-2 bg-slate-500 rounded-full"></div>
                            Disconnected
                        </span>
                    )}
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[85%] rounded-lg p-3 ${
                                msg.type === 'user'
                                    ? 'bg-purple-600 text-white'
                                    : msg.type === 'error'
                                    ? 'bg-rose-500/20 border border-rose-500/30 text-rose-200'
                                    : msg.type === 'system'
                                    ? 'bg-slate-700/50 text-slate-300 text-sm'
                                    : 'bg-slate-800 text-slate-200 border border-slate-700'
                            }`}
                        >
                            <div className="whitespace-pre-wrap break-words text-sm">
                                {msg.message}
                            </div>
                            <div className="text-xs opacity-60 mt-1">
                                {new Date(msg.timestamp).toLocaleTimeString()}
                            </div>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-slate-700 bg-slate-800/30">
                {isWaitingForInput && (
                    <div className="mb-2 text-xs text-amber-400 flex items-center gap-2">
                        <AlertCircle size={14} />
                        Agent is waiting for your response
                    </div>
                )}
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={isWaitingForInput ? "Type your response..." : "Send a message to the agent..."}
                        disabled={!isConnected}
                        className="flex-1 bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:ring-2 focus:ring-purple-500 focus:outline-none placeholder-slate-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <button
                        onClick={sendMessage}
                        disabled={!inputValue.trim() || !isConnected}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        x<Send size={18} />
                    </button>
                </div>
            </div>
        </div>
    )
}