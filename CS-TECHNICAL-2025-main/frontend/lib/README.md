# API Client Documentation

This directory contains the API client configuration for the frontend application.

## Files

- **`api.ts`** - Main REST API client with all backend endpoints
- **`socket.ts`** - Socket.IO client for real-time interview features
- **`.env.local`** - Environment configuration (not committed)

## Setup

1. Install dependencies (already done):
```bash
npm install axios socket.io-client
```

2. Configure environment variables in `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Usage

### Authentication

```typescript
import api from '@/lib/api';

// Register new user
const { access_token, email } = await api.register('user@example.com', 'password123');

// Login existing user
const { access_token, email } = await api.login('user@example.com', 'password123');

// Logout
api.logout();

// Check if authenticated
import { isAuthenticated } from '@/lib/api';
if (isAuthenticated()) {
  // User is logged in
}
```

### Resume Upload & Analysis

```typescript
import api from '@/lib/api';

// Upload resume
const file = event.target.files[0]; // File from input
const { resume_id } = await api.uploadResume(file);

// Get parsed resume data
const resume = await api.getResume(resume_id);

// Get resume review/feedback
const review = await api.reviewResume(resume_id);
```

### Interview

```typescript
import api from '@/lib/api';
import interviewSocket from '@/lib/socket';

// Start interview session
const { session_id, first } = await api.startInterview(resume_id, 'Backend Engineer');

// Connect to socket (in useEffect)
const token = api.getToken();
if (token) {
  await interviewSocket.connect(token);
  interviewSocket.joinInterview(session_id);
}

// Listen for questions
interviewSocket.onQuestion((data) => {
  console.log('New question:', data.question);
  console.log('Progress:', data.progress);
});

// Listen for real-time feedback
interviewSocket.onFeedback((data) => {
  console.log('Feedback:', data.feedback);
});

// Send transcript (as user speaks)
interviewSocket.sendTranscript('I have 5 years of experience...');

// Submit complete answer
interviewSocket.submitAnswer('Full answer text here');

// Send face metrics (from webcam analysis)
interviewSocket.sendFaceMetrics({
  attention: 0.85,
  smiling: true,
  faces: 1,
});

// Listen for face tracking updates
interviewSocket.onFaceStatus((data) => {
  console.log('Attention:', data.ema_attention);
  console.log('Present ratio:', data.present_ratio);
});

// Listen for final results
interviewSocket.onFinal((data) => {
  console.log('Interview complete!');
  console.log('Scores:', data.scores);
  console.log('Insights:', data.insights);
  console.log('Face summary:', data.face_summary);
});

// Cleanup (in useEffect return)
return () => {
  interviewSocket.removeAllListeners();
  interviewSocket.disconnect();
};
```

### Job Matching

```typescript
import api from '@/lib/api';

// Match jobs with custom parameters
const { jobs, skills_used } = await api.matchJobs(
  resume_id,
  'Remote', // region
  ['Python', 'React', 'AWS'] // optional skills override
);

// Auto-match based on resume
const { jobs } = await api.autoMatchJobs(resume_id);

// Display jobs
jobs.forEach(job => {
  console.log(`${job.title} at ${job.company}`);
  console.log(`Location: ${job.location}`);
  console.log(`Match score: ${job.score}`);
});
```

### Digital Footprint Analysis

```typescript
import api from '@/lib/api';

const footprint = await api.getFootprint(
  resume_id,
  'github_username',
  'stackoverflow_id'
);

console.log('GitHub repos:', footprint.github?.public_repos);
console.log('SO reputation:', footprint.stackoverflow?.reputation);
```

### Career Report

```typescript
import api from '@/lib/api';

const report = await api.getCareerReport(resume_id);

console.log('Summary:', report.summary);
console.log('Strengths:', report.strengths);
console.log('Risks:', report.risks);
console.log('Role fit:', report.role_fit);
console.log('Learning plan:', report.learning_plan);
console.log('Top jobs:', report.top_jobs);
```

## Error Handling

```typescript
import api, { getErrorMessage, isApiError } from '@/lib/api';

try {
  const result = await api.uploadResume(file);
} catch (error) {
  // Get user-friendly error message
  const message = getErrorMessage(error);
  console.error(message);
  
  // Check if it's an API error
  if (isApiError(error)) {
    if (error.response?.status === 401) {
      // Unauthorized - redirect to login
    } else if (error.response?.status === 400) {
      // Bad request - show validation errors
    }
  }
}
```

## TypeScript Types

All API responses are fully typed. Import types as needed:

```typescript
import type {
  ParsedResume,
  ReviewResponse,
  InterviewQuestion,
  Job,
  FootprintResponse,
  CareerReportResponse,
} from '@/lib/api';
```

## API Endpoints Reference

### Auth
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user

### Resume
- `POST /upload` - Upload resume file
- `GET /resume/:id` - Get parsed resume
- `POST /review/:id` - Get resume review

### Interview
- `POST /interview/ai/start` - Start interview session
- Socket events:
  - `join_interview` - Join session
  - `transcript` - Send live transcript
  - `answer_done` - Submit complete answer
  - `face_metrics` - Send face tracking data
  - `question` - Receive new question
  - `feedback` - Receive real-time feedback
  - `final` - Receive final results
  - `face_status` - Receive face tracking updates

### Jobs
- `POST /match/:id` - Match jobs with parameters
- `POST /match/auto/:id` - Auto-match from resume

### Footprint
- `POST /footprint/:id` - Analyze digital footprint

### Report
- `POST /report/:id` - Generate career report

## Notes

- All endpoints except `/auth/*` require authentication
- Token is automatically managed by the API client
- Token is stored in localStorage and auto-attached to requests
- 401 responses automatically clear the token
- Socket connection requires valid JWT token
- File uploads use `multipart/form-data` automatically
