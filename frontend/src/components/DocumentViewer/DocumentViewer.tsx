import { useState, useEffect, useRef, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { Card, Button, Badge } from '../common';

// Set worker path for pdf.js
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

/**
 * Parsed field from document extraction.
 */
export interface ParsedField {
  id: string;
  fieldName: string;
  value: string | null;
  confidence: number;
  source: 'regex' | 'table' | 'fuzzy' | 'ocr' | 'not_found';
  boundingBox?: BoundingBox;
  pageNumber?: number;
}

/**
 * Bounding box coordinates (normalized 0-1).
 */
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Document data structure.
 */
export interface DocumentData {
  documentId: number;
  fileName: string;
  fileUrl: string;
  totalPages: number;
  parsedFields: ParsedField[];
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

/**
 * Field correction submitted by user.
 */
export interface FieldCorrection {
  fieldId: string;
  originalValue: string | null;
  correctedValue: string;
}

interface DocumentViewerProps {
  document: DocumentData;
  onSubmitCorrections?: (corrections: FieldCorrection[]) => Promise<void>;
  onFieldClick?: (field: ParsedField) => void;
  readOnly?: boolean;
  confidenceThreshold?: number;
}

/**
 * DocumentViewer component for displaying PDFs with editable parsed field overlays.
 */
function DocumentViewer({
  document,
  onSubmitCorrections,
  onFieldClick,
  readOnly = false,
  confidenceThreshold = 0.75,
}: DocumentViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [currentPage, setCurrentPage] = useState(1);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [scale, setScale] = useState(1.5);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editedFields, setEditedFields] = useState<Map<string, string>>(new Map());
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [pageSize, setPageSize] = useState({ width: 0, height: 0 });

  /**
   * Load PDF document.
   */
  useEffect(() => {
    const loadPdf = async () => {
      if (!document.fileUrl) {
        setError('No document URL provided');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        
        const loadingTask = pdfjsLib.getDocument(document.fileUrl);
        const pdf = await loadingTask.promise;
        setPdfDoc(pdf);
        setIsLoading(false);
      } catch (err) {
        console.error('Error loading PDF:', err);
        setError('Failed to load PDF document');
        setIsLoading(false);
      }
    };

    loadPdf();

    return () => {
      if (pdfDoc) {
        pdfDoc.destroy();
      }
    };
  }, [document.fileUrl]);

  /**
   * Render current page.
   */
  useEffect(() => {
    const renderPage = async () => {
      if (!pdfDoc || !canvasRef.current) return;

      try {
        const page = await pdfDoc.getPage(currentPage);
        const viewport = page.getViewport({ scale });
        
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        
        if (!context) return;

        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        setPageSize({ width: viewport.width, height: viewport.height });

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        };

        await page.render(renderContext).promise;
      } catch (err) {
        console.error('Error rendering page:', err);
        setError('Failed to render page');
      }
    };

    renderPage();
  }, [pdfDoc, currentPage, scale]);

  /**
   * Handle field value change.
   */
  const handleFieldChange = useCallback((fieldId: string, value: string) => {
    setEditedFields((prev) => {
      const newMap = new Map(prev);
      newMap.set(fieldId, value);
      return newMap;
    });
  }, []);

  /**
   * Reset field to original value.
   */
  const handleResetField = useCallback((field: ParsedField) => {
    setEditedFields((prev) => {
      const newMap = new Map(prev);
      newMap.delete(field.id);
      return newMap;
    });
  }, []);

  /**
   * Handle field selection.
   */
  const handleFieldSelect = useCallback((field: ParsedField) => {
    setSelectedField(field.id);
    onFieldClick?.(field);
  }, [onFieldClick]);

  /**
   * Submit all corrections.
   */
  const handleSubmitCorrections = useCallback(async () => {
    if (!onSubmitCorrections || editedFields.size === 0) return;

    const corrections: FieldCorrection[] = [];
    
    editedFields.forEach((correctedValue, fieldId) => {
      const originalField = document.parsedFields.find((f) => f.id === fieldId);
      if (originalField) {
        corrections.push({
          fieldId,
          originalValue: originalField.value,
          correctedValue,
        });
      }
    });

    try {
      setIsSubmitting(true);
      await onSubmitCorrections(corrections);
      setSubmitSuccess(true);
      setTimeout(() => setSubmitSuccess(false), 3000);
    } catch (err) {
      console.error('Error submitting corrections:', err);
      setError('Failed to submit corrections');
    } finally {
      setIsSubmitting(false);
    }
  }, [onSubmitCorrections, editedFields, document.parsedFields]);

  /**
   * Navigate to previous page.
   */
  const goToPrevPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  }, []);

  /**
   * Navigate to next page.
   */
  const goToNextPage = useCallback(() => {
    if (pdfDoc) {
      setCurrentPage((prev) => Math.min(pdfDoc.numPages, prev + 1));
    }
  }, [pdfDoc]);

  /**
   * Zoom controls.
   */
  const zoomIn = useCallback(() => setScale((s) => Math.min(3, s + 0.25)), []);
  const zoomOut = useCallback(() => setScale((s) => Math.max(0.5, s - 0.25)), []);

  /**
   * Get fields for current page.
   */
  const currentPageFields = document.parsedFields.filter(
    (field) => field.pageNumber === currentPage || !field.pageNumber
  );

  /**
   * Check if field is low confidence.
   */
  const isLowConfidence = (confidence: number) => confidence < confidenceThreshold;

  /**
   * Get display value for field (edited or original).
   */
  const getFieldDisplayValue = (field: ParsedField) => {
    return editedFields.get(field.id) ?? field.value ?? '';
  };

  /**
   * Check if field has been edited.
   */
  const isFieldEdited = (fieldId: string) => editedFields.has(fieldId);

  /**
   * Get confidence color.
   */
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600';
    if (confidence >= 0.75) return 'text-yellow-600';
    return 'text-red-600';
  };

  /**
   * Format field name for display.
   */
  const formatFieldName = (name: string) => {
    return name
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .trim()
      .split(' ')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="loading-state">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-500 border-t-transparent mx-auto mb-4" />
          <p className="text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="flex items-center justify-center h-96 bg-red-50 rounded-lg"
        data-testid="error-state"
      >
        <div className="text-center">
          <span className="text-4xl">⚠️</span>
          <p className="text-red-700 mt-2 font-medium">{error}</p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-6" data-testid="document-viewer">
      {/* PDF Viewer Panel */}
      <div className="flex-1">
        <Card>
          {/* Toolbar */}
          <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={goToPrevPage}
                disabled={currentPage <= 1}
                data-testid="prev-page-button"
              >
                ← Prev
              </Button>
              <span className="text-sm text-gray-600" data-testid="page-indicator">
                Page {currentPage} of {pdfDoc?.numPages || document.totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={goToNextPage}
                disabled={currentPage >= (pdfDoc?.numPages || 1)}
                data-testid="next-page-button"
              >
                Next →
              </Button>
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={zoomOut}
                disabled={scale <= 0.5}
                data-testid="zoom-out-button"
              >
                −
              </Button>
              <span className="text-sm text-gray-600 min-w-[4rem] text-center">
                {Math.round(scale * 100)}%
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={zoomIn}
                disabled={scale >= 3}
                data-testid="zoom-in-button"
              >
                +
              </Button>
            </div>
          </div>

          {/* Canvas Container with Field Overlays */}
          <div 
            ref={containerRef}
            className="relative overflow-auto bg-gray-100 rounded-lg"
            style={{ maxHeight: '70vh' }}
          >
            <div className="relative inline-block">
              <canvas
                ref={canvasRef}
                className="block"
                data-testid="pdf-canvas"
              />
              
              {/* Field Overlays */}
              {currentPageFields.map((field) => 
                field.boundingBox && (
                  <div
                    key={field.id}
                    className={`
                      absolute cursor-pointer transition-all duration-200
                      ${isLowConfidence(field.confidence) 
                        ? 'ring-2 ring-red-400 bg-red-100/50' 
                        : 'ring-1 ring-blue-300 bg-blue-100/30'
                      }
                      ${selectedField === field.id ? 'ring-2 ring-primary-500' : ''}
                      hover:ring-2 hover:ring-primary-400
                    `}
                    style={{
                      left: `${field.boundingBox.x * pageSize.width}px`,
                      top: `${field.boundingBox.y * pageSize.height}px`,
                      width: `${field.boundingBox.width * pageSize.width}px`,
                      height: `${field.boundingBox.height * pageSize.height}px`,
                    }}
                    onClick={() => handleFieldSelect(field)}
                    data-testid={`field-overlay-${field.id}`}
                    title={`${formatFieldName(field.fieldName)}: ${field.value || 'Not detected'}`}
                  />
                )
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Fields Panel */}
      <div className="w-96 shrink-0">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Extracted Fields</h3>
            <Badge variant={document.status === 'completed' ? 'success' : 'warning'}>
              {document.status}
            </Badge>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mb-4 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-green-100 ring-1 ring-green-400" />
              <span>High</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-yellow-100 ring-1 ring-yellow-400" />
              <span>Medium</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-red-100 ring-1 ring-red-400" />
              <span>Low</span>
            </div>
          </div>

          {/* Fields List */}
          <div className="space-y-3 max-h-[50vh] overflow-y-auto" data-testid="fields-list">
            {document.parsedFields.map((field) => (
              <div
                key={field.id}
                className={`
                  p-3 rounded-lg border transition-all duration-200
                  ${selectedField === field.id 
                    ? 'border-primary-500 bg-primary-50' 
                    : 'border-gray-200 hover:border-gray-300'
                  }
                  ${isLowConfidence(field.confidence) ? 'bg-red-50' : ''}
                `}
                onClick={() => handleFieldSelect(field)}
                data-testid={`field-item-${field.id}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">
                    {formatFieldName(field.fieldName)}
                  </label>
                  <div className="flex items-center gap-2">
                    {isFieldEdited(field.id) && (
                      <Badge variant="info" data-testid={`edited-badge-${field.id}`}>
                        Edited
                      </Badge>
                    )}
                    <span 
                      className={`text-xs font-medium ${getConfidenceColor(field.confidence)}`}
                      data-testid={`confidence-${field.id}`}
                    >
                      {Math.round(field.confidence * 100)}%
                    </span>
                  </div>
                </div>

                {readOnly ? (
                  <p className="text-sm text-gray-900">
                    {getFieldDisplayValue(field) || '-'}
                  </p>
                ) : (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={getFieldDisplayValue(field)}
                      onChange={(e) => handleFieldChange(field.id, e.target.value)}
                      className={`
                        flex-1 px-3 py-1.5 text-sm rounded border transition-colors
                        ${isLowConfidence(field.confidence)
                          ? 'border-red-300 bg-red-50 focus:ring-red-500 focus:border-red-500'
                          : 'border-gray-300 focus:ring-primary-500 focus:border-primary-500'
                        }
                        focus:outline-none focus:ring-1
                      `}
                      placeholder="Enter value..."
                      data-testid={`field-input-${field.id}`}
                    />
                    {isFieldEdited(field.id) && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleResetField(field);
                        }}
                        className="text-gray-400 hover:text-gray-600 px-2"
                        title="Reset to original"
                        data-testid={`reset-button-${field.id}`}
                      >
                        ↩
                      </button>
                    )}
                  </div>
                )}

                {isLowConfidence(field.confidence) && (
                  <p 
                    className="text-xs text-red-600 mt-1 flex items-center gap-1"
                    data-testid={`low-confidence-warning-${field.id}`}
                  >
                    ⚠️ Low confidence - please verify
                  </p>
                )}

                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <span>Source: {field.source}</span>
                  {field.pageNumber && <span>• Page {field.pageNumber}</span>}
                </div>
              </div>
            ))}

            {document.parsedFields.length === 0 && (
              <p className="text-center text-gray-500 py-8">
                No fields extracted yet
              </p>
            )}
          </div>

          {/* Submit Button */}
          {!readOnly && editedFields.size > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              {submitSuccess && (
                <div 
                  className="mb-3 p-2 bg-green-50 text-green-700 text-sm rounded flex items-center gap-2"
                  data-testid="submit-success"
                >
                  ✅ Corrections submitted successfully
                </div>
              )}
              
              <Button
                onClick={handleSubmitCorrections}
                isLoading={isSubmitting}
                className="w-full"
                data-testid="submit-corrections-button"
              >
                Submit {editedFields.size} Correction{editedFields.size !== 1 ? 's' : ''}
              </Button>
            </div>
          )}
        </Card>

        {/* Summary Stats */}
        <Card className="mt-4">
          <h4 className="font-medium text-gray-900 mb-3">Extraction Summary</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="p-2 bg-gray-50 rounded">
              <p className="text-gray-500">Total Fields</p>
              <p className="font-semibold" data-testid="total-fields">
                {document.parsedFields.length}
              </p>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <p className="text-gray-500">Low Confidence</p>
              <p className="font-semibold text-red-600" data-testid="low-confidence-count">
                {document.parsedFields.filter((f) => isLowConfidence(f.confidence)).length}
              </p>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <p className="text-gray-500">Avg Confidence</p>
              <p className="font-semibold" data-testid="avg-confidence">
                {document.parsedFields.length > 0
                  ? Math.round(
                      (document.parsedFields.reduce((sum, f) => sum + f.confidence, 0) /
                        document.parsedFields.length) *
                        100
                    )
                  : 0}%
              </p>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <p className="text-gray-500">Corrections</p>
              <p className="font-semibold text-primary-600" data-testid="corrections-count">
                {editedFields.size}
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default DocumentViewer;

