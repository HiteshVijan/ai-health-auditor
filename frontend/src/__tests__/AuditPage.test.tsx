import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import AuditPage, { AuditResult } from '../pages/AuditPage';
import apiClient from '../services/api';

// Mock the API client
vi.mock('../services/api', () => ({
  default: {
    get: vi.fn(),
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
 * Sample audit result for testing.
 */
const sampleAuditResult: AuditResult = {
  documentId: 123,
  fileName: 'hospital_bill.pdf',
  auditDate: '2024-01-15T10:30:00Z',
  score: 72,
  totalIssues: 5,
  criticalCount: 1,
  highCount: 2,
  mediumCount: 1,
  lowCount: 1,
  potentialSavings: 450.75,
  issues: [
    {
      id: 1,
      type: 'duplicate_charge',
      severity: 'critical',
      description: 'Duplicate charge detected for "Lab Test - CBC"',
      field: 'line_items[3]',
      expected: 'Unique charge',
      actual: 'Duplicate of item 1',
      amountImpact: 150.00,
    },
    {
      id: 2,
      type: 'arithmetic_mismatch',
      severity: 'high',
      description: 'Subtotal does not match sum of line items',
      field: 'subtotal',
      expected: '850.00',
      actual: '950.00',
      amountImpact: 100.00,
    },
    {
      id: 3,
      type: 'overcharge',
      severity: 'high',
      description: 'Office visit charge exceeds standard rate for CPT 99213',
      field: 'line_items[0]',
      expected: '≤175.00',
      actual: '275.00',
      amountImpact: 100.00,
    },
    {
      id: 4,
      type: 'tax_mismatch',
      severity: 'medium',
      description: 'Unusual tax rate of 18% applied',
      field: 'tax',
      expected: '0-15% of subtotal',
      actual: '18%',
      amountImpact: 50.75,
    },
    {
      id: 5,
      type: 'missing_field',
      severity: 'low',
      description: 'Provider NPI number is missing',
      field: 'provider_npi',
    },
  ],
  llmSummary: {
    summaryBullets: [
      'The bill audit identified 5 issues with an overall score of 72/100.',
      'Potential savings of $450.75 identified through duplicate charges and overcharges.',
      'Moderate issues were detected, warranting attention and possible dispute.',
    ],
    keyIssues: [
      {
        id: 1,
        description: 'Duplicate charge for CBC lab test',
        recommendation: 'Request removal of the duplicate charge.',
      },
      {
        id: 2,
        description: 'Subtotal calculation error',
        recommendation: 'Request a corrected invoice with accurate calculations.',
      },
      {
        id: 3,
        description: 'Overcharged office visit',
        recommendation: 'Dispute the overcharged amount based on standard CPT code thresholds.',
      },
    ],
  },
};

/**
 * Render AuditPage with router context.
 */
const renderAuditPage = (documentId: string = '123') => {
  return render(
    <MemoryRouter initialEntries={[`/audit/${documentId}`]}>
      <Routes>
        <Route path="/audit/:documentId" element={<AuditPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('AuditPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Loading State', () => {
    it('shows loading state while fetching data', () => {
      vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));
      
      renderAuditPage();
      
      expect(screen.getByTestId('loading-state')).toBeInTheDocument();
      expect(screen.getByText('Analyzing your bill...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('displays error message when API fails', async () => {
      vi.mocked(apiClient.get).mockRejectedValueOnce({
        response: { data: { detail: 'Audit not found' } },
      });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('error-state')).toBeInTheDocument();
        expect(screen.getByText('Audit not found')).toBeInTheDocument();
      });
    });

    it('shows back to dashboard button on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network error'));
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByText('Back to Dashboard')).toBeInTheDocument();
      });
    });
  });

  describe('Audit Score Display', () => {
    it('displays the audit score', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('score-card')).toBeInTheDocument();
        expect(screen.getByText('72')).toBeInTheDocument();
      });
    });

    it('shows appropriate message for score level', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByText('Some issues found')).toBeInTheDocument();
      });
    });

    it('shows "Bill looks accurate" for high scores', async () => {
      const highScoreResult = { ...sampleAuditResult, score: 85 };
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: highScoreResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByText('Bill looks accurate')).toBeInTheDocument();
      });
    });

    it('shows "Significant issues detected" for low scores', async () => {
      const lowScoreResult = { ...sampleAuditResult, score: 35 };
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: lowScoreResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByText('Significant issues detected')).toBeInTheDocument();
      });
    });
  });

  describe('Issues Display', () => {
    it('displays total issues count', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('total-issues')).toHaveTextContent('5');
      });
    });

    it('displays severity count badges', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('critical-count')).toHaveTextContent('1 Critical');
        expect(screen.getByTestId('high-count')).toHaveTextContent('2 High');
        expect(screen.getByTestId('medium-count')).toHaveTextContent('1 Medium');
        expect(screen.getByTestId('low-count')).toHaveTextContent('1 Low');
      });
    });

    it('renders all issues in the list', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('issues-list')).toBeInTheDocument();
        sampleAuditResult.issues.forEach((issue) => {
          expect(screen.getByTestId(`issue-item-${issue.id}`)).toBeInTheDocument();
        });
      });
    });

    it('displays issue descriptions', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('issue-description-1')).toHaveTextContent(
          'Duplicate charge detected for "Lab Test - CBC"'
        );
      });
    });

    it('shows issue details when expanded', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('issue-item-1')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('issue-item-1'));
      
      expect(screen.getByTestId('issue-details-1')).toBeInTheDocument();
    });

    it('shows no issues message when empty', async () => {
      const noIssuesResult = { ...sampleAuditResult, issues: [], totalIssues: 0 };
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: noIssuesResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('no-issues')).toBeInTheDocument();
        expect(screen.getByText('No issues detected. Your bill looks accurate!')).toBeInTheDocument();
      });
    });
  });

  describe('Potential Savings', () => {
    it('displays potential savings amount', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('potential-savings')).toHaveTextContent('$450.75');
      });
    });
  });

  describe('LLM Summary', () => {
    it('displays LLM summary card', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('llm-summary-card')).toBeInTheDocument();
        expect(screen.getByText('AI Summary')).toBeInTheDocument();
      });
    });

    it('displays summary bullets', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('summary-bullets')).toBeInTheDocument();
        sampleAuditResult.llmSummary.summaryBullets.forEach((_, index) => {
          expect(screen.getByTestId(`summary-bullet-${index}`)).toBeInTheDocument();
        });
      });
    });

    it('displays summary bullet content', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('summary-bullet-0')).toHaveTextContent(
          'The bill audit identified 5 issues with an overall score of 72/100.'
        );
      });
    });

    it('displays key issues with recommendations', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('key-issues')).toBeInTheDocument();
        sampleAuditResult.llmSummary.keyIssues.forEach((keyIssue) => {
          expect(screen.getByTestId(`key-issue-${keyIssue.id}`)).toBeInTheDocument();
        });
      });
    });

    it('displays key issue recommendations', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByText('Request removal of the duplicate charge.')).toBeInTheDocument();
      });
    });
  });

  describe('Export PDF', () => {
    it('renders export PDF button', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('export-pdf-button')).toBeInTheDocument();
      });
    });

    it('calls export API when clicked', async () => {
      const user = userEvent.setup();
      
      // Mock for initial data fetch
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      // Mock for PDF export
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: new Blob(['mock pdf content'], { type: 'application/pdf' }),
      });
      
      // Mock URL methods
      const createObjectURLMock = vi.fn().mockReturnValue('blob:mock-url');
      const revokeObjectURLMock = vi.fn();
      global.URL.createObjectURL = createObjectURLMock;
      global.URL.revokeObjectURL = revokeObjectURLMock;
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByTestId('export-pdf-button')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('export-pdf-button'));
      
      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledWith('/audits/123/export', {
          responseType: 'blob',
        });
      });
    });
  });

  describe('Navigation', () => {
    it('fetches audit data with correct document ID', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage('456');
      
      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledWith('/audits/456');
      });
    });
  });

  describe('Document Info', () => {
    it('displays file name in header', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByText(/hospital_bill.pdf/)).toBeInTheDocument();
      });
    });

    it('displays audit date', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByText(/Analyzed on/)).toBeInTheDocument();
      });
    });
  });

  describe('Severity Badges', () => {
    it('displays correct severity badges for issues', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        // Check that critical/high/medium/low badges are shown correctly
        expect(screen.getByText('🚨 Critical')).toBeInTheDocument();
        expect(screen.getAllByText('⚠️ High')).toHaveLength(2);
        expect(screen.getByText('⚡ Medium')).toBeInTheDocument();
        expect(screen.getByText('ℹ️ Low')).toBeInTheDocument();
      });
    });
  });

  describe('Amount Impact', () => {
    it('displays amount impact for issues with monetary impact', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: sampleAuditResult });
      
      renderAuditPage();
      
      await waitFor(() => {
        expect(screen.getByText('$150.00')).toBeInTheDocument();
        expect(screen.getByText('$100.00')).toBeInTheDocument();
      });
    });
  });
});

