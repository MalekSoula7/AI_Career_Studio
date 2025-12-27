import { io, Socket } from 'socket.io-client';
import { InterviewQuestion, InterviewInsights, FaceSummary } from './api';

// ==========================================
// Socket Event Types
// ==========================================

export interface SocketError {
  error: string;
}

export interface QuestionEvent {
  question: InterviewQuestion | null;
  progress?: string;
}

export interface FeedbackEvent {
  feedback: string | null;
}

export interface FinalEvent {
  done: boolean;
  scores: Record<string, number>;
  face_summary: FaceSummary;
  insights: InterviewInsights;
}

export interface FaceStatusEvent {
  ema_attention: number;
  ema_faces: number;
  frames: number;
  present_ratio: number;
  smile_ratio: number;
}

// ==========================================
// Socket Client Class
// ==========================================

const SOCKET_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class InterviewSocketClient {
  private socket: Socket | null = null;
  private sessionId: string | null = null;

  /**
   * Connect to the interview socket with authentication
   */
  connect(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket?.connected) {
        resolve();
        return;
      }

      this.socket = io(SOCKET_URL, {
        auth: { token },
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      });

      this.socket.on('connect', () => {
        console.log('Socket connected:', this.socket?.id);
        resolve();
      });

      this.socket.on('connect_error', (error) => {
        console.error('Socket connection error:', error);
        reject(error);
      });

      this.socket.on('disconnect', (reason) => {
        console.log('Socket disconnected:', reason);
      });
    });
  }

  /**
   * Disconnect from the socket
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.sessionId = null;
    }
  }

  /**
   * Join an interview session
   */
  joinInterview(sessionId: string) {
    if (!this.socket?.connected) {
      throw new Error('Socket not connected. Call connect() first.');
    }
    this.sessionId = sessionId;
    this.socket.emit('join_interview', { session_id: sessionId });
  }

  /**
   * Send transcript text (for real-time feedback during answer)
   */
  sendTranscript(text: string) {
    if (!this.socket?.connected || !this.sessionId) {
      throw new Error('Not in an active interview session');
    }
    this.socket.emit('transcript', {
      session_id: this.sessionId,
      text,
    });
  }

  /**
   * Mark answer as complete and move to next question
   */
  submitAnswer(answer: string) {
    if (!this.socket?.connected || !this.sessionId) {
      throw new Error('Not in an active interview session');
    }
    this.socket.emit('answer_done', {
      session_id: this.sessionId,
      answer,
    });
  }

  /**
   * Send face detection metrics for attention tracking
   */
  sendFaceMetrics(metrics: {
    attention: number;
    smiling: boolean;
    faces: number;
  }) {
    if (!this.socket?.connected || !this.sessionId) {
      throw new Error('Not in an active interview session');
    }
    this.socket.emit('face_metrics', {
      session_id: this.sessionId,
      ...metrics,
    });
  }

  // ==========================================
  // Event Listeners
  // ==========================================

  /**
   * Listen for error events
   */
  onError(callback: (data: SocketError) => void) {
    if (!this.socket) return;
    this.socket.on('error', callback);
  }

  /**
   * Listen for new questions
   */
  onQuestion(callback: (data: QuestionEvent) => void) {
    if (!this.socket) return;
    this.socket.on('question', callback);
  }

  /**
   * Listen for real-time feedback
   */
  onFeedback(callback: (data: FeedbackEvent) => void) {
    if (!this.socket) return;
    this.socket.on('feedback', callback);
  }

  /**
   * Listen for final results (interview complete)
   */
  onFinal(callback: (data: FinalEvent) => void) {
    if (!this.socket) return;
    this.socket.on('final', callback);
  }

  /**
   * Listen for face tracking status updates
   */
  onFaceStatus(callback: (data: FaceStatusEvent) => void) {
    if (!this.socket) return;
    this.socket.on('face_status', callback);
  }

  // ==========================================
  // Remove Event Listeners
  // ==========================================

  offError() {
    this.socket?.off('error');
  }

  offQuestion() {
    this.socket?.off('question');
  }

  offFeedback() {
    this.socket?.off('feedback');
  }

  offFinal() {
    this.socket?.off('final');
  }

  offFaceStatus() {
    this.socket?.off('face_status');
  }

  /**
   * Remove all event listeners
   */
  removeAllListeners() {
    this.socket?.removeAllListeners();
  }

  // ==========================================
  // Status Checks
  // ==========================================

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  getSessionId(): string | null {
    return this.sessionId;
  }
}

// ==========================================
// Export singleton instance
// ==========================================

const interviewSocket = new InterviewSocketClient();

export default interviewSocket;

// ==========================================
// Hook-ready utility function
// ==========================================

/**
 * Initialize and connect to interview socket
 * Returns cleanup function for React useEffect
 */
export async function initializeInterviewSocket(
  token: string
): Promise<() => void> {
  await interviewSocket.connect(token);
  return () => interviewSocket.disconnect();
}
