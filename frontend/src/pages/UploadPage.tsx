import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button } from '../components/common';
import { formatFileSize } from '../utils/format';
import apiClient from '../services/api';

interface UploadState {
  status: 'idle' | 'uploading' | 'success' | 'error';
  progress: number;
  message: string;
  documentId?: number;
}

const ALLOWED_TYPES = ['application/pdf', 'image/png', 'image/jpeg', 'image/tiff'];
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

/**
 * Bill upload page with drag-and-drop support.
 */
function UploadPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>({
    status: 'idle',
    progress: 0,
    message: '',
  });

  /**
   * Validate and set the selected file.
   */
  const handleFile = useCallback((selectedFile: File) => {
    // Reset state
    setUploadState({ status: 'idle', progress: 0, message: '' });

    // Validate file type
    if (!ALLOWED_TYPES.includes(selectedFile.type)) {
      setUploadState({
        status: 'error',
        progress: 0,
        message: 'Invalid file type. Please upload a PDF or image (PNG, JPEG, TIFF).',
      });
      return;
    }

    // Validate file size
    if (selectedFile.size > MAX_SIZE_BYTES) {
      setUploadState({
        status: 'error',
        progress: 0,
        message: `File too large. Maximum size is ${MAX_SIZE_MB}MB.`,
      });
      return;
    }

    // Validate not empty
    if (selectedFile.size === 0) {
      setUploadState({
        status: 'error',
        progress: 0,
        message: 'Empty file not allowed.',
      });
      return;
    }

    setFile(selectedFile);
  }, []);

  /**
   * Handle drag over event.
   */
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  /**
   * Handle drag leave event.
   */
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  /**
   * Handle file drop event.
   */
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const droppedFiles = e.dataTransfer.files;
      if (droppedFiles.length > 0) {
        handleFile(droppedFiles[0]);
      }
    },
    [handleFile]
  );

  /**
   * Handle file input change.
   */
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFile(files[0]);
      }
    },
    [handleFile]
  );

  /**
   * Open file browser.
   */
  const handleBrowseClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  /**
   * Remove selected file.
   */
  const handleRemoveFile = useCallback(() => {
    setFile(null);
    setUploadState({ status: 'idle', progress: 0, message: '' });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  /**
   * Upload file to server.
   */
  const handleUpload = useCallback(async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploadState({
      status: 'uploading',
      progress: 0,
      message: 'Uploading...',
    });

    try {
      const response = await apiClient.post('/uploads/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadState((prev) => ({
              ...prev,
              progress,
              message: progress < 100 ? 'Uploading...' : 'Processing...',
            }));
          }
        },
      });

      setUploadState({
        status: 'success',
        progress: 100,
        message: 'Upload successful! Redirecting to audit results...',
        documentId: response.data.document_id,
      });

      // Redirect after short delay
      setTimeout(() => {
        navigate(`/audit/${response.data.document_id}`);
      }, 1500);

    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 
        error.message || 
        'Upload failed. Please try again.';

      setUploadState({
        status: 'error',
        progress: 0,
        message: errorMessage,
      });
    }
  }, [file, navigate]);

  /**
   * Get file type icon.
   */
  const getFileIcon = (fileType: string) => {
    if (fileType === 'application/pdf') return '📄';
    if (fileType.startsWith('image/')) return '🖼️';
    return '📎';
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Upload Bill</h1>
        <p className="text-gray-600 mt-2">
          Upload your medical bill for AI-powered analysis and savings identification.
        </p>
      </div>

      <Card>
        {/* Drop Zone */}
        <div
          data-testid="drop-zone"
          className={`
            border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200
            ${isDragging 
              ? 'border-primary-500 bg-primary-50 scale-[1.02]' 
              : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
            }
            ${uploadState.status === 'uploading' ? 'pointer-events-none opacity-50' : ''}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            data-testid="file-input"
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg,.tiff"
            onChange={handleInputChange}
          />

          <div className="text-5xl mb-4">
            {isDragging ? '📥' : '📤'}
          </div>
          
          <p className="text-lg text-gray-700 mb-2">
            Drag and drop your bill here, or{' '}
            <button
              type="button"
              onClick={handleBrowseClick}
              className="text-primary-600 hover:text-primary-700 hover:underline font-medium"
              disabled={uploadState.status === 'uploading'}
            >
              browse files
            </button>
          </p>
          
          <p className="text-sm text-gray-500">
            PDF, PNG, JPEG, TIFF • Maximum {MAX_SIZE_MB}MB
          </p>
        </div>

        {/* Status Messages */}
        {uploadState.status === 'error' && (
          <div 
            data-testid="error-message"
            className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3"
          >
            <span className="text-red-500 text-xl">⚠️</span>
            <div>
              <p className="font-medium text-red-800">Upload Failed</p>
              <p className="text-red-700 text-sm">{uploadState.message}</p>
            </div>
          </div>
        )}

        {uploadState.status === 'success' && (
          <div 
            data-testid="success-message"
            className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start space-x-3"
          >
            <span className="text-green-500 text-xl">✅</span>
            <div>
              <p className="font-medium text-green-800">Success!</p>
              <p className="text-green-700 text-sm">{uploadState.message}</p>
            </div>
          </div>
        )}

        {/* Selected File */}
        {file && uploadState.status !== 'success' && (
          <div className="mt-6">
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{getFileIcon(file.type)}</span>
                  <div>
                    <p className="font-medium text-gray-900" data-testid="file-name">
                      {file.name}
                    </p>
                    <p className="text-sm text-gray-500" data-testid="file-size">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>
                
                {uploadState.status !== 'uploading' && (
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="text-gray-400 hover:text-gray-600 p-1"
                    aria-label="Remove file"
                    data-testid="remove-file-button"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>

              {/* Progress Bar */}
              {uploadState.status === 'uploading' && (
                <div className="mt-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">{uploadState.message}</span>
                    <span className="text-gray-900 font-medium" data-testid="progress-text">
                      {uploadState.progress}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      data-testid="progress-bar"
                      className="bg-primary-600 h-2 rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${uploadState.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex justify-end space-x-3">
          <Button
            variant="secondary"
            onClick={() => navigate('/dashboard')}
            disabled={uploadState.status === 'uploading'}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!file || uploadState.status === 'uploading' || uploadState.status === 'success'}
            isLoading={uploadState.status === 'uploading'}
            data-testid="upload-button"
          >
            {uploadState.status === 'uploading' ? 'Uploading...' : 'Upload & Analyze'}
          </Button>
        </div>
      </Card>

      {/* Tips Section */}
      <div className="mt-8 grid md:grid-cols-3 gap-4">
        {[
          {
            icon: '📋',
            title: 'Clear Scans',
            description: 'Ensure your bill is clearly visible with no blurry areas',
          },
          {
            icon: '📐',
            title: 'Full Page',
            description: 'Include all pages of your bill for complete analysis',
          },
          {
            icon: '🔒',
            title: 'Secure',
            description: 'Your documents are encrypted and securely processed',
          },
        ].map((tip, index) => (
          <div key={index} className="p-4 bg-white rounded-lg border border-gray-100">
            <span className="text-2xl">{tip.icon}</span>
            <h3 className="font-medium text-gray-900 mt-2">{tip.title}</h3>
            <p className="text-sm text-gray-500 mt-1">{tip.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default UploadPage;
