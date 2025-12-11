import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import UploadPage from '../pages/UploadPage';
import apiClient from '../services/api';

// Mock the API client
vi.mock('../services/api', () => ({
  default: {
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
 * Helper to render component with router.
 */
const renderUploadPage = () => {
  return render(
    <BrowserRouter>
      <UploadPage />
    </BrowserRouter>
  );
};

/**
 * Create a mock file.
 */
const createMockFile = (
  name: string,
  size: number,
  type: string
): File => {
  const file = new File(['x'.repeat(size)], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

describe('UploadPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    it('renders the upload page with title', () => {
      renderUploadPage();
      
      expect(screen.getByText('Upload Bill')).toBeInTheDocument();
      expect(screen.getByText(/Upload your medical bill/)).toBeInTheDocument();
    });

    it('renders the drop zone', () => {
      renderUploadPage();
      
      expect(screen.getByTestId('drop-zone')).toBeInTheDocument();
      expect(screen.getByText(/Drag and drop your bill here/)).toBeInTheDocument();
    });

    it('renders browse files button', () => {
      renderUploadPage();
      
      expect(screen.getByText('browse files')).toBeInTheDocument();
    });

    it('renders file input', () => {
      renderUploadPage();
      
      expect(screen.getByTestId('file-input')).toBeInTheDocument();
    });

    it('renders upload button in disabled state initially', () => {
      renderUploadPage();
      
      const uploadButton = screen.getByTestId('upload-button');
      expect(uploadButton).toBeDisabled();
    });
  });

  describe('File Selection', () => {
    it('accepts valid PDF file', async () => {
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      expect(screen.getByTestId('file-name')).toHaveTextContent('test.pdf');
      expect(screen.getByTestId('upload-button')).not.toBeDisabled();
    });

    it('accepts valid PNG image', async () => {
      renderUploadPage();
      
      const file = createMockFile('scan.png', 2048, 'image/png');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      expect(screen.getByTestId('file-name')).toHaveTextContent('scan.png');
    });

    it('accepts valid JPEG image', async () => {
      renderUploadPage();
      
      const file = createMockFile('bill.jpg', 2048, 'image/jpeg');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      expect(screen.getByTestId('file-name')).toHaveTextContent('bill.jpg');
    });

    it('rejects invalid file type', async () => {
      renderUploadPage();
      
      const file = createMockFile('document.txt', 1024, 'text/plain');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
      expect(screen.getByText(/Invalid file type/)).toBeInTheDocument();
    });

    it('rejects file larger than 10MB', async () => {
      renderUploadPage();
      
      const file = createMockFile('large.pdf', 11 * 1024 * 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
      expect(screen.getByText(/too large/)).toBeInTheDocument();
    });

    it('displays file size after selection', async () => {
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 5 * 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      expect(screen.getByTestId('file-size')).toBeInTheDocument();
    });

    it('allows removing selected file', async () => {
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      expect(screen.getByTestId('file-name')).toBeInTheDocument();
      
      const removeButton = screen.getByTestId('remove-file-button');
      await userEvent.click(removeButton);
      
      expect(screen.queryByTestId('file-name')).not.toBeInTheDocument();
    });
  });

  describe('Drag and Drop', () => {
    it('shows visual feedback on drag over', () => {
      renderUploadPage();
      
      const dropZone = screen.getByTestId('drop-zone');
      
      fireEvent.dragOver(dropZone, {
        dataTransfer: { files: [] },
      });
      
      expect(dropZone).toHaveClass('border-primary-500');
    });

    it('removes visual feedback on drag leave', () => {
      renderUploadPage();
      
      const dropZone = screen.getByTestId('drop-zone');
      
      fireEvent.dragOver(dropZone, {
        dataTransfer: { files: [] },
      });
      
      fireEvent.dragLeave(dropZone, {
        dataTransfer: { files: [] },
      });
      
      expect(dropZone).not.toHaveClass('border-primary-500');
    });

    it('accepts dropped file', async () => {
      renderUploadPage();
      
      const file = createMockFile('dropped.pdf', 1024, 'application/pdf');
      const dropZone = screen.getByTestId('drop-zone');
      
      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file],
        },
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('file-name')).toHaveTextContent('dropped.pdf');
      });
    });
  });

  describe('Upload Process', () => {
    it('calls API on upload button click', async () => {
      const mockPost = vi.mocked(apiClient.post);
      mockPost.mockResolvedValueOnce({
        data: { document_id: 123, status: 'uploaded' },
      });
      
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      const uploadButton = screen.getByTestId('upload-button');
      await userEvent.click(uploadButton);
      
      expect(mockPost).toHaveBeenCalledWith(
        '/uploads/',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      );
    });

    it('shows progress bar during upload', async () => {
      const mockPost = vi.mocked(apiClient.post);
      
      // Create a promise that we can control
      let resolveUpload: (value: any) => void;
      mockPost.mockImplementationOnce((url, data, config) => {
        // Simulate progress callback
        if (config?.onUploadProgress) {
          config.onUploadProgress({ loaded: 50, total: 100 });
        }
        
        return new Promise((resolve) => {
          resolveUpload = resolve;
          // Resolve after a delay
          setTimeout(() => {
            resolve({ data: { document_id: 123 } });
          }, 100);
        });
      });
      
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      const uploadButton = screen.getByTestId('upload-button');
      await userEvent.click(uploadButton);
      
      // Check progress bar is visible
      await waitFor(() => {
        expect(screen.getByTestId('progress-bar')).toBeInTheDocument();
      });
    });

    it('shows success message on successful upload', async () => {
      const mockPost = vi.mocked(apiClient.post);
      mockPost.mockResolvedValueOnce({
        data: { document_id: 456, status: 'uploaded' },
      });
      
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      const uploadButton = screen.getByTestId('upload-button');
      await userEvent.click(uploadButton);
      
      await waitFor(() => {
        expect(screen.getByTestId('success-message')).toBeInTheDocument();
      });
    });

    it('shows error message on failed upload', async () => {
      const mockPost = vi.mocked(apiClient.post);
      mockPost.mockRejectedValueOnce({
        response: { data: { detail: 'Server error occurred' } },
      });
      
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      const uploadButton = screen.getByTestId('upload-button');
      await userEvent.click(uploadButton);
      
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
        expect(screen.getByText(/Server error occurred/)).toBeInTheDocument();
      });
    });

    it('navigates to audit page on successful upload', async () => {
      vi.useFakeTimers();
      
      const mockPost = vi.mocked(apiClient.post);
      mockPost.mockResolvedValueOnce({
        data: { document_id: 789, status: 'uploaded' },
      });
      
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      const uploadButton = screen.getByTestId('upload-button');
      await userEvent.click(uploadButton);
      
      await waitFor(() => {
        expect(screen.getByTestId('success-message')).toBeInTheDocument();
      });
      
      // Fast-forward timer for redirect
      vi.advanceTimersByTime(2000);
      
      expect(mockNavigate).toHaveBeenCalledWith('/audit/789');
      
      vi.useRealTimers();
    });

    it('disables upload button while uploading', async () => {
      const mockPost = vi.mocked(apiClient.post);
      
      // Create a never-resolving promise to simulate ongoing upload
      mockPost.mockImplementationOnce(() => new Promise(() => {}));
      
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      const uploadButton = screen.getByTestId('upload-button');
      await userEvent.click(uploadButton);
      
      await waitFor(() => {
        expect(uploadButton).toBeDisabled();
      });
    });
  });

  describe('Accessibility', () => {
    it('has accessible file input', () => {
      renderUploadPage();
      
      const input = screen.getByTestId('file-input');
      expect(input).toHaveAttribute('accept', '.pdf,.png,.jpg,.jpeg,.tiff');
    });

    it('has accessible remove button', async () => {
      renderUploadPage();
      
      const file = createMockFile('test.pdf', 1024, 'application/pdf');
      const input = screen.getByTestId('file-input');
      
      await userEvent.upload(input, file);
      
      const removeButton = screen.getByTestId('remove-file-button');
      expect(removeButton).toHaveAttribute('aria-label', 'Remove file');
    });
  });
});

