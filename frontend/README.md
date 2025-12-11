# Health Bill Auditor - Frontend

React + TypeScript frontend for the AI Health Bill Auditor platform.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router v6** - Client-side routing
- **Axios** - HTTP client
- **TailwindCSS** - Utility-first styling

## Project Structure

```
src/
├── components/       # Reusable UI components
│   ├── auth/        # Authentication components
│   ├── common/      # Shared components (Button, Input, Card, etc.)
│   └── layout/      # Layout components (Header, Sidebar)
├── pages/           # Page components
├── services/        # API service functions
├── types/           # TypeScript type definitions
├── utils/           # Utility functions
└── styles/          # Global styles
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server on port 3000 |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
| `npm run type-check` | Run TypeScript type checking |

## Pages

| Route | Page | Auth Required |
|-------|------|---------------|
| `/` | Home/Landing | No |
| `/login` | Login | No |
| `/register` | Register | No |
| `/dashboard` | Dashboard | Yes |
| `/upload` | Upload Bill | Yes |
| `/audit/:id` | Audit Results | Yes |
| `/negotiate/:id` | Negotiation | Yes |
| `/history` | History | Yes |
| `/settings` | Settings | Yes |

## API Integration

All API calls go through the `services/` directory:

- `auth.ts` - Authentication (login, register, logout)
- `documents.ts` - Document upload and management
- `audit.ts` - Audit results and parsed fields
- `negotiation.ts` - Letter generation and delivery

## Styling

Uses TailwindCSS with custom theme:

- Primary color: Blue (`primary-*`)
- Accent color: Green (`accent-*`)
- Custom utility classes in `globals.css`

## License

MIT

