# Frontend (Next.js)

Next.js app (App Router) for auth, dashboard, resume upload/review, interview UI, and job matching. Talks to the Flask backend via REST + Socket.IO.

## Requirements
- Node.js 18+ (recommend LTS)

## Setup & Run
```powershell
Set-Location "c:\Users\darkloverr\Desktop\test2\frontend"
npm install
npm run dev
# -> http://localhost:3000
```

## Environment
Create `.env.local` (optional):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
Defaults to `http://localhost:8000` if unset. Socket.IO uses the same base URL.

## Scripts
- `npm run dev` — Next.js dev server
- `npm run build` — Production build
- `npm run start` — Start built app
- `npm run lint` — ESLint

## Code Pointers
- `lib/api.ts` — Axios client, types, and API methods (auth, upload, review, report, match, footprint, AI aids). Stores JWT in `localStorage`.
- `lib/socket.ts` — Socket.IO client with helpers for interview session events and face metrics.
- `app/(auth)/login`, `app/(auth)/register` — Auth pages
- `app/dashboard` — Main dashboard
- `app/interview` — Interview surface (consumes Socket.IO events)

## Notes
- Ensure backend CORS allows `http://localhost:3000`.
- Auth token persists in `localStorage` as `token`; API client auto‑attaches it.
- Some endpoints (review/report) call LLMs and may take longer; UI should handle loading states.This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
