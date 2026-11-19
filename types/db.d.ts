/**
 * =============================================================================
 * HAMRAH BAGHEROLOLUM -- CENTRAL DATABASE STATIC TYPING DEFINITIONS
 * File: types/db.d.ts
 *
 * Database Schema Version: 3.0.0
 * Architecture: 46 Top-Level Keys (5 Primitives/Metadata, 6 Objects, 35 Collections)
 * =============================================================================
 */

export type EntityId = string;

/**
 * Workflow states for content publishing and editorial review
 */
export type WorkflowState =
  | 'Draft'
  | 'Submitted'
  | 'Under Review'
  | 'Revision Required'
  | 'Approved'
  | 'Scheduled'
  | 'Published'
  | 'Rejected'
  | 'Archived'
  | string;

/**
 * Administrative approval statuses
 */
export type ApprovalStatus = 'Approved' | 'Pending' | 'Rejected' | string;

/**
 * Educational content types for posts
 */
export type PostContentType =
  | 'guide'
  | 'article'
  | 'tutorial'
  | 'video'
  | 'note'
  | 'audio'
  | 'checklist'
  | string;

/**
 * Supported media formats for posts
 */
export type MediaFormat = 'text' | 'image' | 'audio' | 'video' | string;

/**
 * Importance / priority badges
 */
export type ImportanceLevel = 'پیشنهاد ویژه' | 'بسیار مهم' | 'مهم' | string;

/**
 * VARK learning style dimension identifiers
 */
export type VarkDimension = 'V' | 'A' | 'R' | 'K';

// =============================================================================
// ROOT DATABASE SCHEMA
// =============================================================================

export interface AppDatabase {
  // --- Root Metadata & Primitives (5 keys) ---
  version: string;
  schemaVersion: '3.0.0' | string;
  lastLocalEdit: number;
  lastPublished: number;
  lastPublishedDateFa: string;

  // --- Single-Object / Record Dictionaries (6 keys) ---
  siteSettings: SiteSettings;
  studentData: StudentData;
  studentProfiles: Record<string, StudentData>;
  autoSavedDrafts: Record<string, AutoSavedDraft>;
  customPageTexts: CustomPageTexts;
  quickCompass: QuickCompass;

  // --- Entity Collections (35 keys) ---
  categories: Category[];
  subcategories: Subcategory[];
  posts: Post[];
  postRevisions: PostRevision[];
  postApprovals: PostApproval[];
  attachments: Attachment[];
  tags: Tag[];
  faqs: Faq[];
  quizzes: Quiz[];
  quizQuestions: QuizQuestion[];
  quizOptions: QuizOption[];
  quizResults: QuizResult[];
  announcements: Announcement[];
  shortTips: ShortTip[];
  calendarEvents: CalendarEvent[];
  learningPaths: LearningPath[];
  learningPathSteps: LearningPathStep[];
  majorsDirectory: Major[];
  majors: Major[];
  universities: University[];
  careers: Career[];
  counselorsList: Counselor[];
  roles: Role[];
  permissions: Permission[];
  users: User[];
  sessions: AuthSessionRecord[];
  adminAuditLogs: AuditLog[];
  auditLogs: AuditLog[];
  backupRecords: BackupRecord[];
  media: MediaItem[];
  studentNotes: StudentNote[];
  studySessions: StudySession[];
  studySchedules: StudySchedule[];
  studentGoals: StudentGoal[];
  counselorMessages: CounselorMessage[];
}

// =============================================================================
// ENTITY DEFINITIONS
// =============================================================================

export interface CategorySubcategoryItem {
  id: EntityId;
  parentId: EntityId | null;
  title: string;
  icon?: string;
  color?: string;
  accent?: string;
  description?: string;
  order?: number;
  cleanTitle?: string;
  _lastFormattedTitle?: string;
}

export interface Category {
  id: EntityId;
  order: number;
  displayNumber: number;
  active: boolean;
  icon: string;
  color: string;
  title: string;
  cleanTitle: string;
  _lastFormattedTitle: string;
  slug: string;
  description: string;
  approvalStatus: ApprovalStatus;
  approvedBy: string;
  subcategories: CategorySubcategoryItem[];
}

export interface Subcategory {
  id: EntityId;
  categoryId: EntityId;
  parentId: EntityId | null;
  title: string;
  order: number;
  approvalStatus: ApprovalStatus;
}

export interface PostAttachmentSummary {
  id: EntityId;
  name: string;
  fileType: string;
  size: string;
  description: string;
  content: string;
}

export interface PostGalleryItem {
  title: string;
  caption: string;
  url?: string;
}

export interface Post {
  id: EntityId;
  title: string;
  slug: string;
  categoryId: EntityId;
  subcategoryId: EntityId;
  contentType: PostContentType;
  mediaFormat: MediaFormat;
  grade: string;
  importance: ImportanceLevel;
  readingTime: string;
  author: string;
  summary: string;
  content: string;
  tags: string[];
  featured: boolean;
  views: number;
  likes: number;
  status: 'published' | 'draft' | 'trash' | string;
  workflowState: WorkflowState;
  approvalStatus: ApprovalStatus;
  approvedBy: string;
  approvedAt: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  coverType: string;
  customCoverDataUrl?: string;
  videoUrl: string;
  aparatHash: string;
  videoSubtitles: string;
  audioUrl: string;
  audioDuration: string;
  audioTranscript: string;
  attachments: PostAttachmentSummary[];
  gallery: PostGalleryItem[];
}

export interface PostRevision {
  id: EntityId;
  postId: EntityId;
  version: number;
  title: string;
  summary: string;
  content: string;
  workflowState: WorkflowState;
  createdAt: string;
  author: string;
  changeNote: string;
}

export interface PostApproval {
  id: EntityId;
  postId: EntityId;
  version: number;
  targetType: string;
  title: string;
  decision: string;
  notes: string;
  approverName: string;
  createdAt: string;
}

export interface Attachment {
  id: EntityId;
  postId: EntityId;
  name: string;
  fileType: string;
  size: string;
  description: string;
  content: string;
  approvalStatus: ApprovalStatus;
}

export interface MediaItem {
  id: EntityId;
  name: string;
  mimeType: string;
  sizeLabel: string;
  category: string;
  url: string;
  uploadedBy: string;
  createdAt: string;
}

export interface Tag {
  id: EntityId;
  name: string;
  slug: string;
  usageCount: number;
}

export interface Faq {
  id: EntityId;
  categoryId: EntityId;
  question: string;
  answer: string;
  relatedPostIds: EntityId[];
  approved: boolean;
  approvalStatus: ApprovalStatus;
  askedBy: string;
  askedByPublic: string;
  consentToPublishName: boolean;
  createdAt: string;
  mediaType: string;
  mediaUrl: string;
  attachmentName: string;
  ownerId?: string;
  trackingCode?: string;
  workflowState?: WorkflowState;
}

export interface QuizEmbeddedOption {
  text: string;
  score: number;
  dimension?: VarkDimension | string;
  tag?: string;
}

export interface QuizEmbeddedQuestion {
  q: string;
  cleanQ?: string;
  options: QuizEmbeddedOption[];
}

export interface QuizInterpretation {
  min: number;
  max: number;
  level: string;
  advice: string;
  recommendedPosts: EntityId[];
}

export interface Quiz {
  id: EntityId;
  title: string;
  cleanTitle: string;
  _lastFormattedTitle: string;
  category: string;
  duration: string;
  icon: string;
  description: string;
  approvalStatus: ApprovalStatus;
  isVarkMultidimensional: boolean | null;
  questions: QuizEmbeddedQuestion[];
  interpretations: QuizInterpretation[];
}

export interface QuizQuestion {
  id: EntityId;
  quizId: EntityId;
  order: number;
  questionText: string;
}

export interface QuizOption {
  id: EntityId;
  questionId: EntityId;
  quizId: EntityId;
  text: string;
  score: number;
  dimension: VarkDimension | string | null;
}

export interface VarkBreakdown {
  V: number;
  A: number;
  R: number;
  K: number;
  dominant?: string;
}

export interface QuizResult {
  id: EntityId;
  userId?: string;
  quizId: EntityId;
  quizTitle: string;
  score: number;
  level: string;
  advice?: string;
  varkBreakdown?: VarkBreakdown;
  date: string;
}

export interface Announcement {
  id: EntityId;
  title: string;
  date: string;
  badge: string;
  grade: string;
  content: string;
  approvalStatus?: ApprovalStatus;
}

export interface ShortTip {
  id: EntityId;
  title: string;
  text: string;
  category: string;
}

export interface CalendarEvent {
  id: EntityId;
  title: string;
  date: string;
  day: string;
  grade: string;
  type: string;
  approvalStatus: ApprovalStatus;
}

export interface LearningPath {
  id: EntityId;
  title: string;
  description: string;
  grade: string;
  postIds: EntityId[];
  approvalStatus: ApprovalStatus;
}

export interface LearningPathStep {
  id: EntityId;
  pathId: EntityId;
  postId: EntityId;
  stepOrder: number;
}

export interface Major {
  id: EntityId;
  group: string;
  title: string;
  intro: string;
  tracks: string;
  courses: string;
  skills: string;
  admissionRules: string;
  universities: string;
  careerOutlook: string;
  careerPaths: string;
  furtherStudy: string;
  officialSource: string;
  validityYear: string;
  updatedAt: string;
  approvalStatus: ApprovalStatus;
}

export interface University {
  id: EntityId;
  name: string;
  city: string;
  type: string;
  fields: string;
  website: string;
}

export interface Career {
  id: EntityId;
  title: string;
  relatedMajorId: EntityId;
  demandLevel: string;
  futureOutlook: string;
}

export interface Counselor {
  id: EntityId;
  name: string;
  role: string;
  icon: string;
  bio: string;
  schedule: string;
}

export interface Permission {
  id: EntityId;
  code: string;
  title: string;
}

export interface Role {
  id: EntityId;
  name: string;
  description: string;
  permissions: string[];
}

export interface User {
  id: EntityId;
  username: string;
  name: string;
  roleId: EntityId;
  roleLabel: string;
  grade: string;
  active: boolean;
  salt: string;
  passwordHash: string;
  twoFactorEnabled: boolean;
  failedAttempts: number;
  lockedUntil: number;
  createdAt: string;
  lastActivity: string;
}

export interface AuthSessionRecord {
  sessionId: string;
  userId: EntityId;
  username: string;
  userNameLabel: string;
  roleId: EntityId;
  roleLabel: string;
  csrfToken: string;
  createdAt: number;
  createdAtJalali: string;
  expiresAt: number;
  revoked: boolean;
}

export interface AuditLog {
  id: EntityId;
  actor: string;
  action: string;
  time: string;
}

export interface BackupRecord {
  id: EntityId;
  createdAt: string;
  createdBy: string;
  checksum: string;
  postsCount: number;
  categoriesCount: number;
}

export interface CounselorMessageHistoryItem {
  actor: string;
  text: string;
  time: string;
}

export interface CounselorMessage {
  id: EntityId;
  ownerId?: string;
  trackingCode?: string;
  studentName: string;
  grade: string;
  phone?: string;
  type: 'question' | 'feedback' | 'private' | string;
  isPrivate?: boolean;
  categoryId?: EntityId;
  subject: string;
  message: string;
  reply: string;
  status: string;
  history?: CounselorMessageHistoryItem[];
  createdAt: string;
  approvedForPublicFaq?: boolean;
}

export interface StudentNote {
  id: EntityId;
  userId?: string;
  title: string;
  tag: string;
  content: string;
  date: string;
}

export interface StudySession {
  id: EntityId;
  userId?: string;
  type?: 'study' | 'break' | string;
  modeLabel?: string;
  subject: string;
  minutes: number;
  elapsedSeconds?: number;
  date: string;
}

export interface StudySchedule {
  id: EntityId;
  userId?: string;
  day: string;
  timeSlot: string;
  startTime?: string;
  endTime?: string;
  subject: string;
  targetTests: string;
  done: boolean;
}

export interface GoalHistoryItem {
  date: string;
  val: number;
}

export interface StudentGoal {
  id: EntityId;
  userId?: string;
  title: string;
  current: number;
  target: number;
  unit: string;
  history?: GoalHistoryItem[];
}

export interface DailyChecklistItem {
  id: EntityId;
  text: string;
  done: boolean;
}

export interface ReadingList {
  id: EntityId;
  title: string;
  postIds: EntityId[];
}

export interface StudentActivityLog {
  id: EntityId;
  action: string;
  date: string;
}

export interface StudentData {
  ownerId: string;
  bookmarkedPostIds: EntityId[];
  completedPostIds: EntityId[];
  recentlyViewedPostIds: EntityId[];
  readingLists: ReadingList[];
  quizHistory: QuizResult[];
  counselorMessages: CounselorMessage[];
  weeklySchedule: StudySchedule[];
  dailyChecklist: DailyChecklistItem[];
  goals: StudentGoal[];
  personalNotes: StudentNote[];
  studySessions: StudySession[];
  activityLogs: StudentActivityLog[];
}

export interface AutoSavedDraft {
  title: string;
  slug: string;
  categoryId: string;
  subcategoryId: string;
  contentType: string;
  grade: string;
  importance: string;
  summary: string;
  tags: string;
  content: string;
  aparat: string;
  subtitles: string;
  audioDur: string;
  audioTranscript: string;
  savedAt: string;
}

export interface SiteSettingsModulesVisibility {
  showTopBar: boolean;
  showHeroStats: boolean;
  showShortTips: boolean;
  showCategories: boolean;
  showFeaturedPosts: boolean;
  showPopularPosts: boolean;
  showMediaSection: boolean;
  showAnnouncements: boolean;
  showCounselorBox: boolean;
  showHomeFaq: boolean;
  showCalendar: boolean;
}

export interface SiteSettings {
  siteTitle: string;
  schoolName: string;
  heroTitle: string;
  heroSubtitle: string;
  counselorLeadName: string;
  counselorPhone: string;
  officeHours: string;
  requireSuperAdminApproval: boolean;
  allowGuestPublicAccess: boolean;
  retentionPolicyDays: number;
  canonicalDomain: string;
  versionBadge: string;
  topBarBadge: string;
  topBarAnnouncement: string;
  heroBadge: string;
  counselorSectionHeading: string;
  counselorLeadDegree: string;
  counselorMissionText: string;
  footerSubtitle: string;
  footerDescription: string;
  schoolAddress: string;
  copyrightText: string;
  modulesVisibility: SiteSettingsModulesVisibility;
  counselorRubikaUrl: string;
  googleSheetsWebhookUrl: string;
}

export interface CustomPageTexts {
  aboutText: string;
  contactExtra: string;
  privacyText: string;
  termsText: string;
}

export interface QuickCompassItem {
  id: EntityId;
  icon: string;
  title: string;
  badge: string;
  targetType: 'category' | 'modal' | 'view';
  targetValue: string;
  colorVar: string;
}

export interface QuickCompass {
  enabled: boolean;
  title: string;
  subtitle: string;
  items: QuickCompassItem[];
}
