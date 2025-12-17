import { UploadCloud } from 'lucide-react'
import { useState, ChangeEvent } from 'react'
import axios from 'axios'

interface UploadProps {
    onUploadSuccess?: (path: string) => void;
}

export default function Upload({ onUploadSuccess }: UploadProps) {
    const [uploading, setUploading] = useState(false)
    const [message, setMessage] = useState('')

    const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setUploading(true)
        setMessage('')

        const formData = new FormData()
        formData.append('file', file)

        try {
            const response = await axios.post('http://localhost:8000/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setMessage(`Success: ${response.data.filename}`)
            onUploadSuccess && onUploadSuccess(response.data.path)
        } catch (err) {
            console.error(err)
            setMessage('Upload failed')
        } finally {
            setUploading(false)
        }
    }

    return (
        <div className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center hover:border-indigo-500 transition-colors bg-slate-800/50 group cursor-pointer relative">
            <input type="file" accept=".apk" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
            <div className="flex flex-col items-center justify-center space-y-4">
                <div className="p-4 bg-slate-700 rounded-full group-hover:bg-indigo-500/20 group-hover:text-indigo-400 transition-all">
                    <UploadCloud size={32} />
                </div>
                <div>
                    <p className="font-medium text-slate-200">Click to upload APK</p>
                    <p className="text-sm text-slate-400">or drag and drop here</p>
                </div>
                {uploading && <p className="text-indigo-400 animate-pulse">Uploading...</p>}
                {message && <p className="text-emerald-400">{message}</p>}
            </div>
        </div>
    )
}
