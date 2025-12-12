import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, Badge, Button } from '../components/common';
import apiClient from '../services/api';

interface Document {
  id: number;
  filename: string;
  content_type: string | null;
  file_size: number | null;
  status: string;
  user_id: number;
  created_at: string | null;
}

interface DocumentsResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Audit history page - shows uploaded documents.
 */
function HistoryPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get<DocumentsResponse>('/documents/');
      setDocuments(response.data.documents);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch documents:', err);
      setError(err.response?.data?.detail || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDelete = async (docId: number) => {
    if (confirmDeleteId !== docId) {
      setConfirmDeleteId(docId);
      return;
    }

    setDeletingId(docId);
    try {
      await apiClient.delete(`/documents/${docId}`);
      setDocuments(documents.filter(d => d.id !== docId));
      setConfirmDeleteId(null);
    } catch (err: any) {
      console.error('Failed to delete document:', err);
      alert(err.response?.data?.detail || 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const cancelDelete = () => {
    setConfirmDeleteId(null);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'uploaded':
        return <Badge variant="info">Uploaded</Badge>;
      case 'processing':
        return <Badge variant="warning">Processing</Badge>;
      case 'completed':
        return <Badge variant="success">Completed</Badge>;
      case 'failed':
        return <Badge variant="danger">Failed</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 text-xl mb-4">⚠️ {error}</div>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">History</h1>
          <p className="text-gray-600 mt-2">
            View your uploaded bills ({documents.length} documents)
          </p>
        </div>
        <Link to="/upload">
          <Button>Upload New Bill</Button>
        </Link>
      </div>

      <Card>
        {documents.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <div className="text-5xl mb-4">📄</div>
            <p className="text-xl mb-2">No documents yet</p>
            <p className="mb-4">Upload your first medical bill to get started!</p>
            <Link to="/upload">
              <Button>Upload Bill</Button>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Document</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Date</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Size</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-4 px-4">
                      <div className="flex items-center space-x-3">
                        <span className="text-xl">
                          {doc.content_type?.includes('pdf') ? '📕' : 
                           doc.content_type?.includes('image') ? '🖼️' : '📄'}
                        </span>
                        <div>
                          <span className="font-medium text-gray-900">{doc.filename}</span>
                          <p className="text-xs text-gray-500">ID: {doc.id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-gray-600">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="py-4 px-4 text-gray-600">
                      {formatFileSize(doc.file_size)}
                    </td>
                    <td className="py-4 px-4">
                      {getStatusBadge(doc.status)}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={`/audit/${doc.id}`}
                          className="text-blue-600 hover:underline font-medium"
                        >
                          View Audit
                        </Link>
                        <span className="text-gray-300">|</span>
                        <Link
                          to={`/negotiate/${doc.id}`}
                          className="text-green-600 hover:underline font-medium"
                        >
                          Negotiate
                        </Link>
                        <span className="text-gray-300">|</span>
                        {confirmDeleteId === doc.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDelete(doc.id)}
                              disabled={deletingId === doc.id}
                              className="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded text-sm font-medium disabled:opacity-50"
                            >
                              {deletingId === doc.id ? 'Deleting...' : 'Confirm'}
                            </button>
                            <button
                              onClick={cancelDelete}
                              className="text-gray-600 hover:text-gray-800 px-2 py-1 rounded text-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="text-red-600 hover:text-red-700 font-medium hover:underline"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

export default HistoryPage;
