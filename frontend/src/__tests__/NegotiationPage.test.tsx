import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import NegotiationPage, { DocumentSummary, GeneratedLetter, NegotiationResult } from '../pages/NegotiationPage';
import apiClient from '../services/api';

// Mock the API client
vi.mock('../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

/**
 * Sample documents for testing.
 */
const sampleDocuments: DocumentSummary[] = [
  {
    id: 1,
    fileName: 'hospital_bill.pdf',
    uploadDate: '2024-01-10T10:00:00Z',
    auditScore: 72,
    potentialSavings: 450.75,
  },
  {
    id: 2,
    fileName: 'lab_results.pdf',
    uploadDate: '2024-01-12T14:30:00Z',
    auditScore: 85,
    potentialSavings: 125.50,
  },
  {
    id: 3,
    fileName: 'urgent_care_visit.pdf',
    uploadDate: '2024-01-15T09:15:00Z',
    auditScore: 45,
    potentialSavings: 890.00,
  },
];

/**
 * Sample generated letter for testing.
 */
const sampleGeneratedLetter: GeneratedLetter = {
  letterId: 'letter-123',
  content: `January 15, 2024

Healthcare Provider
123 Medical Center Drive
Health City, CA 90210

Subject: Dispute Regarding Account Number: ACC-12345

Dear Sir/Madam,

This letter serves as a formal dispute regarding the medical bill associated with Account Number ACC-12345.

Upon careful review of the enclosed bill, our audit has identified the following discrepancies:

1. Duplicate charge detected for "Lab Test - CBC". Recommendation: Request removal of the duplicate charge.
2. Subtotal calculation error. Recommendation: Request a corrected invoice with accurate calculations.

We kindly request a thorough review of these identified issues and a revised statement reflecting the necessary adjustments.

Sincerely,
John Doe`,
  tone: 'formal',
  generatedAt: '2024-01-15T10:30:00Z',
  wordCount: 142,
};

/**
 * Sample successful negotiation result.
 */
const sampleSuccessResult: NegotiationResult = {
  success: true,
  deliveryStatus: 'sent',
  messageId: 'msg-abc123',
  timestamp: '2024-01-15T10:35:00Z',
  retryCount: 0,
};

/**
 * Sample failed negotiation result.
 */
const sampleFailedResult: NegotiationResult = {
  success: false,
  deliveryStatus: 'failed',
  timestamp: '2024-01-15T10:35:00Z',
  retryCount: 1,
  errorMessage: 'Unable to reach recipient',
};

/**
 * Render NegotiationPage with router context.
 */
const renderNegotiationPage = (documentId?: string) => {
  const path = documentId ? `/negotiate/${documentId}` : '/negotiate';
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/negotiate/:documentId?" element={<NegotiationPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('NegotiationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({ data: sampleDocuments });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    it('renders the negotiation page', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('negotiation-page')).toBeInTheDocument();
      });
    });

    it('displays page title', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByText('Negotiate Bill')).toBeInTheDocument();
      });
    });

    it('shows loading state initially', () => {
      vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));
      
      renderNegotiationPage();
      
      expect(screen.getByTestId('loading-state')).toBeInTheDocument();
    });
  });

  describe('Document Selection', () => {
    it('displays document list', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-list')).toBeInTheDocument();
        sampleDocuments.forEach((doc) => {
          expect(screen.getByTestId(`document-option-${doc.id}`)).toBeInTheDocument();
        });
      });
    });

    it('displays document file names', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByText('hospital_bill.pdf')).toBeInTheDocument();
        expect(screen.getByText('lab_results.pdf')).toBeInTheDocument();
      });
    });

    it('displays potential savings for documents', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByText('Save $450.75')).toBeInTheDocument();
      });
    });

    it('allows selecting a document', async () => {
      const user = userEvent.setup();
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      
      const selectedOption = screen.getByTestId('document-option-1');
      expect(selectedOption).toHaveClass('border-primary-500');
    });

    it('pre-selects document from URL parameter', async () => {
      renderNegotiationPage('2');
      
      await waitFor(() => {
        const selectedOption = screen.getByTestId('document-option-2');
        expect(selectedOption).toHaveClass('border-primary-500');
      });
    });

    it('shows empty state when no documents', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: [] });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByText('No documents available')).toBeInTheDocument();
        expect(screen.getByText('Upload a Bill')).toBeInTheDocument();
      });
    });
  });

  describe('Channel Selection', () => {
    it('displays channel options', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('channel-options')).toBeInTheDocument();
        expect(screen.getByTestId('channel-email')).toBeInTheDocument();
        expect(screen.getByTestId('channel-whatsapp')).toBeInTheDocument();
      });
    });

    it('selects email by default', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        const emailOption = screen.getByTestId('channel-email');
        expect(emailOption).toHaveClass('border-primary-500');
      });
    });

    it('allows switching to WhatsApp', async () => {
      const user = userEvent.setup();
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('channel-whatsapp')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('channel-whatsapp'));
      
      const whatsappOption = screen.getByTestId('channel-whatsapp');
      expect(whatsappOption).toHaveClass('border-primary-500');
    });

    it('shows email input when email is selected', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('email-input')).toBeInTheDocument();
      });
    });

    it('shows phone input when WhatsApp is selected', async () => {
      const user = userEvent.setup();
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('channel-whatsapp')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('channel-whatsapp'));
      
      expect(screen.getByTestId('phone-input')).toBeInTheDocument();
    });
  });

  describe('Tone Selection', () => {
    it('displays tone options', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('tone-options')).toBeInTheDocument();
        expect(screen.getByTestId('tone-formal')).toBeInTheDocument();
        expect(screen.getByTestId('tone-friendly')).toBeInTheDocument();
        expect(screen.getByTestId('tone-assertive')).toBeInTheDocument();
      });
    });

    it('selects formal by default', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        const formalOption = screen.getByTestId('tone-formal');
        expect(formalOption).toHaveClass('border-primary-500');
      });
    });

    it('allows changing tone', async () => {
      const user = userEvent.setup();
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('tone-assertive')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('tone-assertive'));
      
      const assertiveOption = screen.getByTestId('tone-assertive');
      expect(assertiveOption).toHaveClass('border-primary-500');
    });
  });

  describe('Letter Generation', () => {
    it('renders generate button', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('generate-button')).toBeInTheDocument();
      });
    });

    it('disables generate button when no document selected', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('generate-button')).toBeDisabled();
      });
    });

    it('enables generate button when document selected', async () => {
      const user = userEvent.setup();
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      
      expect(screen.getByTestId('generate-button')).not.toBeDisabled();
    });

    it('calls API to generate letter', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: sampleGeneratedLetter });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.click(screen.getByTestId('generate-button'));
      
      expect(apiClient.post).toHaveBeenCalledWith('/negotiations/generate', {
        documentId: 1,
        tone: 'formal',
      });
    });

    it('displays generated letter content', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: sampleGeneratedLetter });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('letter-preview')).toBeInTheDocument();
        expect(screen.getByTestId('letter-content')).toHaveTextContent('This letter serves as a formal dispute');
      });
    });

    it('shows word count after generation', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: sampleGeneratedLetter });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByText('142 words')).toBeInTheDocument();
      });
    });

    it('shows empty preview before generation', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('empty-preview')).toBeInTheDocument();
      });
    });
  });

  describe('Sending Negotiation', () => {
    it('shows send button after letter is generated', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: sampleGeneratedLetter });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
    });

    it('calls execute API when send is clicked', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post)
        .mockResolvedValueOnce({ data: sampleGeneratedLetter })
        .mockResolvedValueOnce({ data: sampleSuccessResult });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.type(screen.getByTestId('email-input'), 'billing@hospital.com');
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('send-button'));
      
      expect(apiClient.post).toHaveBeenCalledWith('/negotiations/execute', {
        documentId: 1,
        channel: 'email',
        tone: 'formal',
        recipient: 'billing@hospital.com',
        letterId: 'letter-123',
      });
    });

    it('shows error when recipient is missing', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: sampleGeneratedLetter });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      // Don't enter email
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('send-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('error-banner')).toBeInTheDocument();
        expect(screen.getByText('Please enter an email address')).toBeInTheDocument();
      });
    });
  });

  describe('Delivery Status', () => {
    it('shows idle status initially', async () => {
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('delivery-status')).toHaveTextContent('Ready to generate');
      });
    });

    it('shows ready status after generation', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: sampleGeneratedLetter });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('delivery-status')).toHaveTextContent('Letter ready to send');
      });
    });

    it('shows sent status after successful delivery', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post)
        .mockResolvedValueOnce({ data: sampleGeneratedLetter })
        .mockResolvedValueOnce({ data: sampleSuccessResult });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.type(screen.getByTestId('email-input'), 'test@test.com');
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('send-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('delivery-status')).toHaveTextContent('Successfully sent');
      });
    });

    it('shows failed status after failed delivery', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post)
        .mockResolvedValueOnce({ data: sampleGeneratedLetter })
        .mockResolvedValueOnce({ data: sampleFailedResult });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.type(screen.getByTestId('email-input'), 'test@test.com');
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('send-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('delivery-status')).toHaveTextContent('Delivery failed');
      });
    });

    it('shows success message after successful send', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post)
        .mockResolvedValueOnce({ data: sampleGeneratedLetter })
        .mockResolvedValueOnce({ data: sampleSuccessResult });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.type(screen.getByTestId('email-input'), 'test@test.com');
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('send-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('success-message')).toBeInTheDocument();
        expect(screen.getByText('Letter sent successfully!')).toBeInTheDocument();
      });
    });

    it('displays error message on failure', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post)
        .mockResolvedValueOnce({ data: sampleGeneratedLetter })
        .mockResolvedValueOnce({ data: sampleFailedResult });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.type(screen.getByTestId('email-input'), 'test@test.com');
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('send-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toHaveTextContent('Unable to reach recipient');
      });
    });
  });

  describe('Retry Functionality', () => {
    it('shows retry button after failure', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post)
        .mockResolvedValueOnce({ data: sampleGeneratedLetter })
        .mockResolvedValueOnce({ data: sampleFailedResult });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.type(screen.getByTestId('email-input'), 'test@test.com');
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('send-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('retry-button')).toBeInTheDocument();
      });
    });

    it('resets status on retry click', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post)
        .mockResolvedValueOnce({ data: sampleGeneratedLetter })
        .mockResolvedValueOnce({ data: sampleFailedResult });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.type(screen.getByTestId('email-input'), 'test@test.com');
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('send-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('retry-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('retry-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('delivery-status')).toHaveTextContent('Letter ready to send');
      });
    });
  });

  describe('Regenerate Letter', () => {
    it('shows regenerate button after generation', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: sampleGeneratedLetter });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('regenerate-button')).toBeInTheDocument();
      });
    });

    it('clears letter when selections change', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: sampleGeneratedLetter });
      
      renderNegotiationPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('document-option-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('document-option-1'));
      await user.click(screen.getByTestId('generate-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('letter-preview')).toBeInTheDocument();
      });
      
      // Change tone - should clear letter
      await user.click(screen.getByTestId('tone-assertive'));
      
      await waitFor(() => {
        expect(screen.getByTestId('empty-preview')).toBeInTheDocument();
      });
    });
  });
});

