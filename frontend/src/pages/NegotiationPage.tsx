import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Badge, Loader } from '../components/common';
import apiClient from '../services/api';

/**
 * Available communication channels.
 */
export type Channel = 'email' | 'whatsapp';

/**
 * Available letter tones.
 */
export type Tone = 'formal' | 'friendly' | 'assertive';

/**
 * Delivery status states.
 */
export type DeliveryStatus = 'idle' | 'generating' | 'ready' | 'sending' | 'sent' | 'failed';

/**
 * Document from API.
 */
interface ApiDocument {
  id: number;
  filename: string;
  content_type: string | null;
  file_size: number | null;
  status: string;
  user_id: number;
  created_at: string | null;
}

/**
 * API response for documents list.
 */
interface DocumentsResponse {
  documents: ApiDocument[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Document summary for selection.
 */
export interface DocumentSummary {
  id: number;
  fileName: string;
  uploadDate: string;
  auditScore?: number;
  potentialSavings?: number;
}

/**
 * Generated letter response.
 */
export interface GeneratedLetter {
  letterId: string;
  content: string;
  tone: Tone;
  generatedAt: string;
  wordCount: number;
}

/**
 * Negotiation execution response.
 */
export interface NegotiationResult {
  success: boolean;
  deliveryStatus: 'sent' | 'failed' | 'pending';
  messageId?: string;
  timestamp: string;
  retryCount: number;
  errorMessage?: string;
}

/**
 * Channel configuration.
 */
const CHANNELS: { value: Channel; label: string; icon: string; description: string }[] = [
  {
    value: 'email',
    label: 'Email',
    icon: '📧',
    description: 'Send a formal email to the provider',
  },
  {
    value: 'whatsapp',
    label: 'WhatsApp',
    icon: '💬',
    description: 'Send via WhatsApp Business',
  },
];

/**
 * Tone configuration.
 */
const TONES: { value: Tone; label: string; icon: string; description: string }[] = [
  {
    value: 'formal',
    label: 'Formal',
    icon: '👔',
    description: 'Professional and business-like',
  },
  {
    value: 'friendly',
    label: 'Friendly',
    icon: '😊',
    description: 'Warm and conversational',
  },
  {
    value: 'assertive',
    label: 'Assertive',
    icon: '💪',
    description: 'Direct and demanding action',
  },
];

/**
 * Selection card component for channel/tone.
 */
function SelectionCard<T extends string>({
  value,
  label,
  icon,
  description,
  isSelected,
  onSelect,
  disabled,
  testId,
}: {
  value: T;
  label: string;
  icon: string;
  description: string;
  isSelected: boolean;
  onSelect: (value: T) => void;
  disabled?: boolean;
  testId?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      disabled={disabled}
      className={`
        p-4 rounded-lg border-2 text-left transition-all duration-200 w-full
        ${isSelected
          ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      data-testid={testId}
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">{icon}</span>
        <div>
          <p className="font-medium text-gray-900">{label}</p>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
      </div>
    </button>
  );
}

/**
 * Delivery status indicator component.
 */
function DeliveryStatusIndicator({ status, result }: { status: DeliveryStatus; result?: NegotiationResult }) {
  const statusConfig: Record<DeliveryStatus, { icon: string; text: string; variant: 'default' | 'info' | 'success' | 'warning' | 'danger' }> = {
    idle: { icon: '⏸️', text: 'Ready to generate', variant: 'default' },
    generating: { icon: '⚙️', text: 'Generating letter...', variant: 'info' },
    ready: { icon: '✅', text: 'Letter ready to send', variant: 'success' },
    sending: { icon: '📤', text: 'Sending...', variant: 'info' },
    sent: { icon: '✅', text: 'Successfully sent', variant: 'success' },
    failed: { icon: '❌', text: 'Delivery failed', variant: 'danger' },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-3" data-testid="delivery-status">
      <Badge variant={config.variant}>
        {config.icon} {config.text}
      </Badge>
      {result?.messageId && (
        <span className="text-xs text-gray-500">
          ID: {result.messageId}
        </span>
      )}
      {result?.errorMessage && status === 'failed' && (
        <span className="text-xs text-red-600" data-testid="error-message">
          {result.errorMessage}
        </span>
      )}
    </div>
  );
}

/**
 * NegotiationPage component for generating and sending dispute letters.
 */
function NegotiationPage() {
  const { documentId: paramDocId } = useParams<{ documentId?: string }>();
  const navigate = useNavigate();

  // State
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(
    paramDocId ? parseInt(paramDocId, 10) : null
  );
  const [selectedChannel, setSelectedChannel] = useState<Channel>('email');
  const [selectedTone, setSelectedTone] = useState<Tone>('formal');
  const [generatedLetter, setGeneratedLetter] = useState<GeneratedLetter | null>(null);
  const [deliveryStatus, setDeliveryStatus] = useState<DeliveryStatus>('idle');
  const [negotiationResult, setNegotiationResult] = useState<NegotiationResult | null>(null);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Contact info state
  const [recipientEmail, setRecipientEmail] = useState('');
  const [recipientPhone, setRecipientPhone] = useState('');

  /**
   * Fetch available documents on mount.
   */
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setIsLoadingDocuments(true);
        const response = await apiClient.get<DocumentsResponse>('/documents/');
        
        // Transform API response to DocumentSummary format
        const docs: DocumentSummary[] = response.data.documents.map((doc) => ({
          id: doc.id,
          fileName: doc.filename,
          uploadDate: doc.created_at || new Date().toISOString(),
          auditScore: undefined,
          potentialSavings: undefined,
        }));
        
        setDocuments(docs);

        // If document ID from URL, verify it exists
        if (paramDocId) {
          const docId = parseInt(paramDocId, 10);
          if (!docs.find((d) => d.id === docId)) {
            setError('Document not found');
          }
        }
      } catch (err) {
        console.error('Error fetching documents:', err);
        setError('Failed to load documents');
      } finally {
        setIsLoadingDocuments(false);
      }
    };

    fetchDocuments();
  }, [paramDocId]);

  /**
   * Reset letter when selections change.
   */
  useEffect(() => {
    setGeneratedLetter(null);
    setDeliveryStatus('idle');
    setNegotiationResult(null);
  }, [selectedDocumentId, selectedChannel, selectedTone]);

  /**
   * Generate negotiation letter.
   */
  const handleGenerateLetter = useCallback(async () => {
    if (!selectedDocumentId) return;

    try {
      setDeliveryStatus('generating');
      setError(null);

      const response = await apiClient.post<GeneratedLetter>('/negotiations/generate', {
        documentId: selectedDocumentId,
        tone: selectedTone,
      });

      setGeneratedLetter(response.data);
      setDeliveryStatus('ready');
    } catch (err: any) {
      console.error('Error generating letter:', err);
      setError(err.response?.data?.detail || 'Failed to generate letter');
      setDeliveryStatus('idle');
    }
  }, [selectedDocumentId, selectedTone]);

  /**
   * Send negotiation via selected channel.
   */
  const handleSendNegotiation = useCallback(async () => {
    if (!selectedDocumentId || !generatedLetter) return;

    const recipient = selectedChannel === 'email' ? recipientEmail : recipientPhone;
    if (!recipient) {
      setError(`Please enter ${selectedChannel === 'email' ? 'an email address' : 'a phone number'}`);
      return;
    }

    try {
      setDeliveryStatus('sending');
      setError(null);

      const response = await apiClient.post<NegotiationResult>('/negotiations/execute', {
        documentId: selectedDocumentId,
        channel: selectedChannel,
        tone: selectedTone,
        recipient: recipient,
        letterId: generatedLetter.letterId,
      });

      setNegotiationResult(response.data);
      setDeliveryStatus(response.data.success ? 'sent' : 'failed');
    } catch (err: any) {
      console.error('Error sending negotiation:', err);
      setNegotiationResult({
        success: false,
        deliveryStatus: 'failed',
        timestamp: new Date().toISOString(),
        retryCount: 0,
        errorMessage: err.response?.data?.detail || 'Failed to send',
      });
      setDeliveryStatus('failed');
    }
  }, [selectedDocumentId, selectedChannel, selectedTone, generatedLetter, recipientEmail, recipientPhone]);

  /**
   * Retry sending after failure.
   */
  const handleRetry = useCallback(() => {
    setDeliveryStatus('ready');
    setNegotiationResult(null);
    setError(null);
  }, []);

  /**
   * Delete a document.
   */
  const handleDeleteDocument = useCallback(async (docId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (confirmDeleteId !== docId) {
      setConfirmDeleteId(docId);
      return;
    }

    setDeletingId(docId);
    try {
      await apiClient.delete(`/documents/${docId}`);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      if (selectedDocumentId === docId) {
        setSelectedDocumentId(null);
        setGeneratedLetter(null);
      }
      setConfirmDeleteId(null);
    } catch (err: any) {
      console.error('Failed to delete:', err);
      setError(err.response?.data?.detail || 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  }, [confirmDeleteId, selectedDocumentId]);

  /**
   * Get selected document.
   */
  const selectedDocument = documents.find((d) => d.id === selectedDocumentId);

  if (isLoadingDocuments) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="loading-state">
        <div className="text-center">
          <Loader size="lg" />
          <p className="text-gray-600 mt-4">Loading documents...</p>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="negotiation-page">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Negotiate Bill</h1>
        <p className="text-gray-600 mt-2">
          Generate and send a dispute letter to negotiate your medical bill.
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div 
          className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between"
          data-testid="error-banner"
        >
          <div className="flex items-center gap-2">
            <span className="text-red-500">⚠️</span>
            <span className="text-red-700">{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-600"
          >
            ✕
          </button>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left Panel - Configuration */}
        <div className="space-y-6">
          {/* Document Selection */}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              1. Select Document
            </h2>
            
            {documents.length === 0 ? (
              <div className="text-center py-8">
                <span className="text-4xl">📄</span>
                <p className="text-gray-600 mt-2">No documents available</p>
                <Button
                  variant="secondary"
                  className="mt-4"
                  onClick={() => navigate('/upload')}
                >
                  Upload a Bill
                </Button>
              </div>
            ) : (
              <div className="space-y-2" data-testid="document-list">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className={`
                      group relative p-3 rounded-lg border-2 transition-all
                      ${selectedDocumentId === doc.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                      }
                      ${deliveryStatus === 'sending' ? 'opacity-50' : ''}
                    `}
                    data-testid={`document-option-${doc.id}`}
                  >
                    <button
                      type="button"
                      onClick={() => setSelectedDocumentId(doc.id)}
                      disabled={deliveryStatus === 'sending'}
                      className="w-full text-left"
                    >
                      <div className="flex items-center justify-between pr-8">
                        <div>
                          <p className="font-medium text-gray-900">{doc.fileName}</p>
                          <p className="text-sm text-gray-500">
                            Uploaded {new Date(doc.uploadDate).toLocaleDateString()}
                          </p>
                        </div>
                        {doc.potentialSavings && doc.potentialSavings > 0 && (
                          <Badge variant="success" size="sm">
                            Save ${doc.potentialSavings.toFixed(2)}
                          </Badge>
                        )}
                      </div>
                    </button>
                    
                    {/* Delete Button */}
                    <div className="absolute right-2 top-1/2 -translate-y-1/2">
                      {confirmDeleteId === doc.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => handleDeleteDocument(doc.id, e)}
                            disabled={deletingId === doc.id}
                            className="text-xs px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
                          >
                            {deletingId === doc.id ? '...' : 'Yes'}
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null); }}
                            className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={(e) => handleDeleteDocument(doc.id, e)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 
                                     opacity-0 group-hover:opacity-100 transition-all"
                          title="Delete document"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Channel Selection */}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              2. Select Channel
            </h2>
            <div className="grid grid-cols-2 gap-3" data-testid="channel-options">
              {CHANNELS.map((channel) => (
                <SelectionCard
                  key={channel.value}
                  {...channel}
                  isSelected={selectedChannel === channel.value}
                  onSelect={setSelectedChannel}
                  disabled={deliveryStatus === 'sending'}
                  testId={`channel-${channel.value}`}
                />
              ))}
            </div>

            {/* Recipient Input */}
            <div className="mt-4">
              {selectedChannel === 'email' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Provider Email Address
                  </label>
                  <input
                    type="email"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    placeholder="billing@healthcare-provider.com"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    disabled={deliveryStatus === 'sending'}
                    data-testid="email-input"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Provider Phone Number
                  </label>
                  <input
                    type="tel"
                    value={recipientPhone}
                    onChange={(e) => setRecipientPhone(e.target.value)}
                    placeholder="+1 (555) 123-4567"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    disabled={deliveryStatus === 'sending'}
                    data-testid="phone-input"
                  />
                </div>
              )}
            </div>
          </Card>

          {/* Tone Selection */}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              3. Select Tone
            </h2>
            <div className="space-y-3" data-testid="tone-options">
              {TONES.map((tone) => (
                <SelectionCard
                  key={tone.value}
                  {...tone}
                  isSelected={selectedTone === tone.value}
                  onSelect={setSelectedTone}
                  disabled={deliveryStatus === 'sending'}
                  testId={`tone-${tone.value}`}
                />
              ))}
            </div>
          </Card>

          {/* Generate Button */}
          <Button
            onClick={handleGenerateLetter}
            disabled={!selectedDocumentId || deliveryStatus === 'generating' || deliveryStatus === 'sending'}
            isLoading={deliveryStatus === 'generating'}
            className="w-full"
            data-testid="generate-button"
          >
            ✨ Generate Letter
          </Button>
        </div>

        {/* Right Panel - Letter Preview & Actions */}
        <div className="space-y-6">
          {/* Status Card */}
          <Card>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Status</h2>
              <DeliveryStatusIndicator status={deliveryStatus} result={negotiationResult || undefined} />
            </div>

            {negotiationResult && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Sent at:</span>
                    <p className="font-medium">
                      {new Date(negotiationResult.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Retry count:</span>
                    <p className="font-medium">{negotiationResult.retryCount}</p>
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* Letter Preview */}
          <Card className="flex-1">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Letter Preview</h2>
              {generatedLetter && (
                <span className="text-sm text-gray-500">
                  {generatedLetter.wordCount} words
                </span>
              )}
            </div>

            {!generatedLetter ? (
              <div 
                className="flex flex-col items-center justify-center h-64 bg-gray-50 rounded-lg"
                data-testid="empty-preview"
              >
                <span className="text-4xl mb-3">📝</span>
                <p className="text-gray-500 text-center">
                  Select options and click "Generate Letter"<br />
                  to preview your dispute letter
                </p>
              </div>
            ) : (
              <div data-testid="letter-preview">
                <div className="flex items-center gap-2 mb-3">
                  <Badge variant="info">{selectedTone}</Badge>
                  <span className="text-xs text-gray-500">
                    Generated {new Date(generatedLetter.generatedAt).toLocaleTimeString()}
                  </span>
                </div>
                <div 
                  className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto font-mono text-sm whitespace-pre-wrap"
                  data-testid="letter-content"
                >
                  {generatedLetter.content}
                </div>
              </div>
            )}
          </Card>

          {/* Action Buttons */}
          {generatedLetter && (
            <div className="flex gap-3">
              {deliveryStatus === 'failed' ? (
                <>
                  <Button
                    variant="secondary"
                    onClick={handleRetry}
                    className="flex-1"
                    data-testid="retry-button"
                  >
                    🔄 Try Again
                  </Button>
                  <Button
                    onClick={handleSendNegotiation}
                    className="flex-1"
                    data-testid="send-button"
                  >
                    📤 Retry Send
                  </Button>
                </>
              ) : deliveryStatus === 'sent' ? (
                <div className="w-full text-center">
                  <div 
                    className="p-4 bg-green-50 border border-green-200 rounded-lg"
                    data-testid="success-message"
                  >
                    <span className="text-2xl">🎉</span>
                    <p className="text-green-700 font-medium mt-2">
                      Letter sent successfully!
                    </p>
                    <p className="text-green-600 text-sm mt-1">
                      Check your {selectedChannel === 'email' ? 'email' : 'WhatsApp'} for confirmation.
                    </p>
                  </div>
                  <Button
                    variant="secondary"
                    className="mt-4"
                    onClick={() => navigate('/dashboard')}
                  >
                    Back to Dashboard
                  </Button>
                </div>
              ) : (
                <>
                  <Button
                    variant="secondary"
                    onClick={handleGenerateLetter}
                    disabled={deliveryStatus === 'generating' || deliveryStatus === 'sending'}
                    className="flex-1"
                    data-testid="regenerate-button"
                  >
                    🔄 Regenerate
                  </Button>
                  <Button
                    onClick={handleSendNegotiation}
                    disabled={deliveryStatus === 'sending'}
                    isLoading={deliveryStatus === 'sending'}
                    className="flex-1"
                    data-testid="send-button"
                  >
                    📤 Send via {selectedChannel === 'email' ? 'Email' : 'WhatsApp'}
                  </Button>
                </>
              )}
            </div>
          )}

          {/* Selected Document Info */}
          {selectedDocument && (
            <Card>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Selected Document</h3>
              <p className="font-medium text-gray-900">{selectedDocument.fileName}</p>
              <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                {selectedDocument.auditScore !== undefined && (
                  <span>Score: {selectedDocument.auditScore}/100</span>
                )}
                {selectedDocument.potentialSavings !== undefined && (
                  <span className="text-green-600">
                    Potential savings: ${selectedDocument.potentialSavings.toFixed(2)}
                  </span>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => navigate(`/audit/${selectedDocument.id}`)}
              >
                View Audit Details
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

export default NegotiationPage;
