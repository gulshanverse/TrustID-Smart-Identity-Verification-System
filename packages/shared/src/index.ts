export const VERIFICATION_STATES = [
  "CREATED",
  "UPLOADED",
  "QUALITY_CHECK",
  "OCR_PROCESSING",
  "VALIDATING",
  "TAMPERING_ANALYSIS",
  "FACE_VERIFICATION",
  "RISK_ASSESSMENT",
  "COMPLETED",
  "FAILED",
  "REQUIRES_REVIEW",
  "CANCELLED",
] as const;

export type VerificationState = (typeof VERIFICATION_STATES)[number];

export const FACE_RESULTS = ["MATCH", "NO_MATCH", "COULD_NOT_VERIFY", "NOT_AVAILABLE"] as const;
export type FaceResult = (typeof FACE_RESULTS)[number];

export const RISK_LEVELS = ["LOW", "REVIEW", "HIGH"] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];

export interface HealthResponse {
  status: "ok";
  service: "trustid-api";
  environment: string;
}

export interface VerificationSummary {
  id: string;
  state: VerificationState;
  riskLevel?: RiskLevel;
}
