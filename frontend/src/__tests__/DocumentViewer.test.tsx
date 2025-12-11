import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import DocumentViewer, { DocumentData, ParsedField } from '../components/DocumentViewer';

// Mock pdfjs-dist
vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  version: '3.11.174',
  getDocument: vi.fn(() => ({
    promise: Promise.resolve({
      numPages: 3,
      getPage: vi.fn(() =>
        Promise.resolve({
          getViewport: vi.fn(() => ({ width: 800, height: 1000, scale: 1 })),
          render: vi.fn(() => ({ promise: Promise.resolve() })),
        })
      ),
      destroy: vi.fn(),
    }),
  })),
}));

/**
 * Sample parsed fields for testing.
 */
const sampleParsedFields: ParsedField[] = [
  {
    id: 'field-1',
    fieldName: 'total_amount',
    value: '1,234.56',
    confidence: 0.95,
    source: 'regex',
    pageNumber: 1,
    boundingBox: { x: 0.5, y: 0.3, width: 0.2, height: 0.05 },
  },
  {
    id: 'field-2',
    fieldName: 'patient_name',
    value: 'John Doe',
    confidence: 0.88,
    source: 'ocr',
    pageNumber: 1,
    boundingBox: { x: 0.1, y: 0.1, width: 0.3, height: 0.04 },
  },
  {
    id: 'field-3',
    fieldName: 'invoice_number',
    value: 'INV-2024-001',
    confidence: 0.72,
    source: 'regex',
    pageNumber: 1,
    boundingBox: { x: 0.7, y: 0.1, width: 0.2, height: 0.04 },
  },
  {
    id: 'field-4',
    fieldName: 'bill_date',
    value: '2024-01-15',
    confidence: 0.65,
    source: 'fuzzy',
    pageNumber: 1,
  },
  {
    id: 'field-5',
    fieldName: 'provider_name',
    value: null,
    confidence: 0.3,
    source: 'not_found',
    pageNumber: 2,
  },
];

/**
 * Sample document data for testing.
 */
const sampleDocument: DocumentData = {
  documentId: 123,
  fileName: 'medical_bill.pdf',
  fileUrl: 'https://example.com/sample.pdf',
  totalPages: 3,
  parsedFields: sampleParsedFields,
  status: 'completed',
};

describe('DocumentViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    it('renders the document viewer container', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('document-viewer')).toBeInTheDocument();
      });
    });

    it('displays page navigation controls', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('prev-page-button')).toBeInTheDocument();
        expect(screen.getByTestId('next-page-button')).toBeInTheDocument();
        expect(screen.getByTestId('page-indicator')).toBeInTheDocument();
      });
    });

    it('displays zoom controls', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('zoom-in-button')).toBeInTheDocument();
        expect(screen.getByTestId('zoom-out-button')).toBeInTheDocument();
      });
    });

    it('renders the PDF canvas', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('pdf-canvas')).toBeInTheDocument();
      });
    });

    it('displays fields list panel', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('fields-list')).toBeInTheDocument();
      });
    });

    it('shows loading state initially', () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      // Loading state should be visible before PDF loads
      expect(screen.getByTestId('loading-state')).toBeInTheDocument();
    });
  });

  describe('Parsed Fields Display', () => {
    it('displays all parsed fields', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        sampleParsedFields.forEach((field) => {
          expect(screen.getByTestId(`field-item-${field.id}`)).toBeInTheDocument();
        });
      });
    });

    it('shows field values in inputs', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        const totalAmountInput = screen.getByTestId('field-input-field-1');
        expect(totalAmountInput).toHaveValue('1,234.56');
      });
    });

    it('displays confidence percentage for each field', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('confidence-field-1')).toHaveTextContent('95%');
        expect(screen.getByTestId('confidence-field-3')).toHaveTextContent('72%');
      });
    });

    it('displays summary statistics', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('total-fields')).toHaveTextContent('5');
      });
    });
  });

  describe('Low Confidence Highlighting', () => {
    it('highlights fields with confidence below threshold', async () => {
      render(<DocumentViewer document={sampleDocument} confidenceThreshold={0.75} />);
      
      await waitFor(() => {
        // field-3 has 0.72 confidence, field-4 has 0.65, field-5 has 0.3
        expect(screen.getByTestId('low-confidence-warning-field-3')).toBeInTheDocument();
        expect(screen.getByTestId('low-confidence-warning-field-4')).toBeInTheDocument();
        expect(screen.getByTestId('low-confidence-warning-field-5')).toBeInTheDocument();
      });
    });

    it('does not show warning for high confidence fields', async () => {
      render(<DocumentViewer document={sampleDocument} confidenceThreshold={0.75} />);
      
      await waitFor(() => {
        expect(screen.queryByTestId('low-confidence-warning-field-1')).not.toBeInTheDocument();
        expect(screen.queryByTestId('low-confidence-warning-field-2')).not.toBeInTheDocument();
      });
    });

    it('counts low confidence fields correctly', async () => {
      render(<DocumentViewer document={sampleDocument} confidenceThreshold={0.75} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('low-confidence-count')).toHaveTextContent('3');
      });
    });

    it('respects custom confidence threshold', async () => {
      render(<DocumentViewer document={sampleDocument} confidenceThreshold={0.9} />);
      
      await waitFor(() => {
        // With 0.9 threshold, only field-1 (0.95) should be high confidence
        expect(screen.getByTestId('low-confidence-warning-field-2')).toBeInTheDocument();
        expect(screen.getByTestId('low-confidence-warning-field-3')).toBeInTheDocument();
      });
    });
  });

  describe('Field Editing', () => {
    it('allows editing field values', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      const input = screen.getByTestId('field-input-field-1');
      await user.clear(input);
      await user.type(input, '2,500.00');
      
      expect(input).toHaveValue('2,500.00');
    });

    it('shows edited badge when field is modified', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      const input = screen.getByTestId('field-input-field-1');
      await user.clear(input);
      await user.type(input, 'new value');
      
      expect(screen.getByTestId('edited-badge-field-1')).toBeInTheDocument();
    });

    it('shows reset button for edited fields', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      const input = screen.getByTestId('field-input-field-1');
      await user.clear(input);
      await user.type(input, 'changed');
      
      expect(screen.getByTestId('reset-button-field-1')).toBeInTheDocument();
    });

    it('resets field to original value when reset clicked', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      const input = screen.getByTestId('field-input-field-1');
      await user.clear(input);
      await user.type(input, 'modified');
      
      const resetButton = screen.getByTestId('reset-button-field-1');
      await user.click(resetButton);
      
      expect(input).toHaveValue('1,234.56');
    });

    it('disables editing in readOnly mode', async () => {
      render(<DocumentViewer document={sampleDocument} readOnly />);
      
      await waitFor(() => {
        expect(screen.queryByTestId('field-input-field-1')).not.toBeInTheDocument();
      });
    });

    it('updates corrections count when fields are edited', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      const input1 = screen.getByTestId('field-input-field-1');
      await user.clear(input1);
      await user.type(input1, 'edit1');
      
      const input2 = screen.getByTestId('field-input-field-2');
      await user.clear(input2);
      await user.type(input2, 'edit2');
      
      expect(screen.getByTestId('corrections-count')).toHaveTextContent('2');
    });
  });

  describe('Submit Corrections', () => {
    it('shows submit button when fields are edited', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} onSubmitCorrections={vi.fn()} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      // Initially no submit button
      expect(screen.queryByTestId('submit-corrections-button')).not.toBeInTheDocument();
      
      // Edit a field
      const input = screen.getByTestId('field-input-field-1');
      await user.clear(input);
      await user.type(input, 'changed');
      
      expect(screen.getByTestId('submit-corrections-button')).toBeInTheDocument();
    });

    it('calls onSubmitCorrections with correct data', async () => {
      const user = userEvent.setup();
      const mockSubmit = vi.fn().mockResolvedValue(undefined);
      
      render(<DocumentViewer document={sampleDocument} onSubmitCorrections={mockSubmit} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      const input = screen.getByTestId('field-input-field-1');
      await user.clear(input);
      await user.type(input, '5,000.00');
      
      const submitButton = screen.getByTestId('submit-corrections-button');
      await user.click(submitButton);
      
      expect(mockSubmit).toHaveBeenCalledWith([
        {
          fieldId: 'field-1',
          originalValue: '1,234.56',
          correctedValue: '5,000.00',
        },
      ]);
    });

    it('shows success message after submission', async () => {
      const user = userEvent.setup();
      const mockSubmit = vi.fn().mockResolvedValue(undefined);
      
      render(<DocumentViewer document={sampleDocument} onSubmitCorrections={mockSubmit} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      const input = screen.getByTestId('field-input-field-1');
      await user.clear(input);
      await user.type(input, 'corrected');
      
      const submitButton = screen.getByTestId('submit-corrections-button');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByTestId('submit-success')).toBeInTheDocument();
      });
    });

    it('shows correct count in submit button', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} onSubmitCorrections={vi.fn()} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-input-field-1')).toBeInTheDocument();
      });
      
      const input1 = screen.getByTestId('field-input-field-1');
      await user.clear(input1);
      await user.type(input1, 'a');
      
      const input2 = screen.getByTestId('field-input-field-2');
      await user.clear(input2);
      await user.type(input2, 'b');
      
      const input3 = screen.getByTestId('field-input-field-3');
      await user.clear(input3);
      await user.type(input3, 'c');
      
      expect(screen.getByTestId('submit-corrections-button')).toHaveTextContent('Submit 3 Corrections');
    });
  });

  describe('Page Navigation', () => {
    it('disables prev button on first page', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        const prevButton = screen.getByTestId('prev-page-button');
        expect(prevButton).toBeDisabled();
      });
    });

    it('enables next button when not on last page', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        const nextButton = screen.getByTestId('next-page-button');
        expect(nextButton).not.toBeDisabled();
      });
    });

    it('navigates to next page on click', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 3');
      });
      
      const nextButton = screen.getByTestId('next-page-button');
      await user.click(nextButton);
      
      await waitFor(() => {
        expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 2 of 3');
      });
    });
  });

  describe('Zoom Controls', () => {
    it('increases zoom on zoom in click', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByText('150%')).toBeInTheDocument();
      });
      
      const zoomInButton = screen.getByTestId('zoom-in-button');
      await user.click(zoomInButton);
      
      await waitFor(() => {
        expect(screen.getByText('175%')).toBeInTheDocument();
      });
    });

    it('decreases zoom on zoom out click', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByText('150%')).toBeInTheDocument();
      });
      
      const zoomOutButton = screen.getByTestId('zoom-out-button');
      await user.click(zoomOutButton);
      
      await waitFor(() => {
        expect(screen.getByText('125%')).toBeInTheDocument();
      });
    });
  });

  describe('Field Selection', () => {
    it('calls onFieldClick when field is selected', async () => {
      const user = userEvent.setup();
      const mockFieldClick = vi.fn();
      
      render(<DocumentViewer document={sampleDocument} onFieldClick={mockFieldClick} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-item-field-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('field-item-field-1'));
      
      expect(mockFieldClick).toHaveBeenCalledWith(sampleParsedFields[0]);
    });

    it('highlights selected field', async () => {
      const user = userEvent.setup();
      render(<DocumentViewer document={sampleDocument} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('field-item-field-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('field-item-field-1'));
      
      const fieldItem = screen.getByTestId('field-item-field-1');
      expect(fieldItem).toHaveClass('border-primary-500');
    });
  });

  describe('Empty State', () => {
    it('shows message when no fields are extracted', async () => {
      const emptyDocument: DocumentData = {
        ...sampleDocument,
        parsedFields: [],
      };
      
      render(<DocumentViewer document={emptyDocument} />);
      
      await waitFor(() => {
        expect(screen.getByText('No fields extracted yet')).toBeInTheDocument();
      });
    });
  });

  describe('Average Confidence Calculation', () => {
    it('calculates average confidence correctly', async () => {
      render(<DocumentViewer document={sampleDocument} />);
      
      // Average of 0.95, 0.88, 0.72, 0.65, 0.3 = 0.7 = 70%
      await waitFor(() => {
        expect(screen.getByTestId('avg-confidence')).toHaveTextContent('70%');
      });
    });
  });
});

