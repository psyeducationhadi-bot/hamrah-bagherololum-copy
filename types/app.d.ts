/**
 * =============================================================================
 * HAMRAH BAGHEROLOLUM -- APPLICATION RUNTIME AMBIENT TYPE DEFINITIONS
 * File: types/app.d.ts
 *
 * Comprehensive TypeScript ambient typings for all global runtime engines,
 * reactive state objects, security services, Shamsi calendar routines,
 * IndexedDB storage, router, and UI controllers in `index.html`.
 * =============================================================================
 */

import type {
  AppDatabase,
  AuthSessionRecord,
  User,
  EntityId
} from './db';

// =============================================================================
// 1. ROUTING & APPLICATION VIEWS
// =============================================================================

export type AppView =
  | 'home'
  | 'categories'
  | 'category'
  | 'explorer'
  | 'post'
  | 'videos'
  | 'podcasts'
  | 'downloads'
  | 'quizzes'
  | 'quiz-take'
  | 'quiz-results'
  | 'faq'
  | 'tools'
  | 'majors'
  | 'study-plan'
  | 'study-plans'
  | 'student-portal'
  | 'counselor'
  | 'announcements'
  | 'calendar'
  | 'about'
  | 'contact'
  | 'privacy'
  | 'terms'
  | 'admin'
  | '404';

export type AdminTab =
  | 'dashboard'
  | 'content'
  | 'editor'
  | 'categories'
  | 'faqs'
  | 'quizzes'
  | 'users'
  | 'backup'
  | 'settings'
  | 'audit';

export type ToolsTab =
  | 'timer'
  | 'schedule'
  | 'goals'
  | 'notes'
  | 'paths'
  | 'calendar';

export type PomodoroMode = 'study' | 'shortBreak' | 'longBreak' | 'deep' | 'exam' | 'break';

export type ToastType = 'success' | 'warning' | 'error' | 'info';

// =============================================================================
// 2. RUNTIME STATE (STATE)
// =============================================================================

export interface AppState {
  currentView: AppView | string;
  viewParams: Record<string, any>;
  currentUser: User | any;
  adminActiveTab: AdminTab | string;
  editingPostId: string | null;
  editorDraftTimer: any;
  toolsActiveTab: ToolsTab | string;
  timerSeconds: number;
  timerRunning: boolean;
  timerMode: PomodoroMode | string;
  timerSubject: string;
  timerInterval: any;
  timerInitialSeconds?: number;
  timerElapsedSeconds?: number;
  timerLastTickAt?: number;
  activeQuizId: string | null;
  quizAnswers: Record<string, any>;
  adminHasUnpublishedChanges?: boolean;
  liveEditMode?: boolean;
  inlineTextEditActive?: boolean;
  _lastViewedPostId?: string | null;
  comparedMajorIds?: string[];
  [key: string]: any;
}

// =============================================================================
// 3. AUTHENTICATION & SESSION ENGINE (AuthService)
// =============================================================================

export interface LoginResult {
  ok: boolean;
  user?: User | any;
  session?: AuthSessionRecord;
  error?: string;
  require2FA?: boolean;
  message?: string;
}

export interface IAuthService {
  currentSession: AuthSessionRecord | null;
  pending2FAUser: any | null;
  initSession(): void;
  setGuestMode(): void;
  getActiveStudentKey(): string;
  syncStudentProfilePointer(): void;
  updateHeaderBadges(): void;
  isAuthenticated(): boolean;
  isAuthenticatedStaff(): boolean;
  isSuperAdmin(): boolean;
  hasPermission(permCode: string): boolean;
  login(username: string, password: string, twoFactorCode?: string): LoginResult;
  logout(): void;
  revokeSessionById(sessionId: string): void;
}

// =============================================================================
// 4. CLOUD SYNCHRONIZATION ENGINE (CloudSync)
// =============================================================================

export interface ICloudSync {
  REPO: string;
  BRANCH: string;
  FILE_PATH: string;
  TOKEN_KEY: string;
  LAST_SYNC_KEY: string;
  _syncInterval?: any;
  getToken(): string;
  setToken(t: string): void;
  utf8ToBase64(str: string): string;
  publishToCloud(): Promise<void>;
  fetchFromCloud(forceToast?: boolean): Promise<void>;
  openConfigModal(autoFocus?: boolean): void;
  saveTokenAndPublish(): void;
  initAutoSyncChecker(): void;
  initTokenTransferListener(): void;
}

// =============================================================================
// 5. JALALI DATE & SOLAR HIJRI CALENDAR (OnlineShamsiCalendar & JalaliDateEngine)
// =============================================================================

export interface JalaliTodayInfo {
  jy: number;
  jm: number;
  jd: number;
  weekdayName: string;
  monthName: string;
  season: string;
  timeStr: string;
  rawTimeStr: string;
  fullPersian: string;
  shortDate: string;
  rawShortDate: string;
  gregorianStr: string;
  dayOfYear: string;
  daysToNewYear: string;
  isOnline: boolean;
}

export interface CalendarOccasion {
  title: string;
  holiday: boolean;
  schoolEvent?: boolean;
}

export interface CalendarCountdown {
  id: string;
  title: string;
  sub: string;
  days: number;
  dateStr: string;
  icon: string;
  badge: string;
}

export interface IOnlineShamsiCalendar {
  isOnline: boolean;
  timeOffsetMs: number;
  lastSyncTime: number | null;
  activeWidgetMonth: number | null;
  activeWidgetYear: number | null;
  activeWidgetDay: number | null;
  monthNames: string[];
  monthDaysCount: number[];
  weekdays: Array<{ name: string; short: string }>;
  isLeapYear(jy: number): boolean;
  getDaysInMonth(jy: number, jm: number): number;
  getOccasions(jm: number, jd: number): CalendarOccasion | null;
  getNow(): Date;
  getToday(): JalaliTodayInfo;
  toPersianDigits(str: string | number): string;
  getCountdowns(): CalendarCountdown[];
  syncOnlineTime(): Promise<void>;
  startTicker(): void;
  tick(): void;
}

export interface IJalaliDateEngine {
  toPersianDigits(str: string | number): string;
  toEnglishDigits(str: string | number): string;
  gregorianToJalali(gy: number, gm: number, gd: number): [number, number, number];
  jalaliToGregorian(jy: number, jm: number, jd: number): [number, number, number];
  nowDate(dateObj?: Date): string;
  nowDateTime(dateObj?: Date): string;
  getWeekdayFromJalali(jalaliStr: string): string;
}

// =============================================================================
// 6. INDEXEDDB MEDIA STORAGE (MediaStorageIDB)
// =============================================================================

export interface SavedMediaRecord {
  mediaId: string;
  objectUrl: string;
}

export interface IMediaStorageIDB {
  dbName: string;
  storeName: string;
  blobUrlCache: Record<string, string>;
  openDB(): Promise<IDBDatabase | null>;
  saveMediaFile(file: File | Blob, category?: string): Promise<SavedMediaRecord>;
  resolveMediaUrl(mediaIdOrUrl: string): Promise<string>;
}

// =============================================================================
// 7. SECURITY & CRYPTOGRAPHIC ENGINE (SecurityEngine)
// =============================================================================

export interface FileValidationResult {
  ok: boolean;
  error?: string;
  ext?: string;
  formattedSize?: string;
  rawSize?: number;
}

export interface ISecurityEngine {
  escapeHtml(input: any): string;
  sanitizeRichHtml(dirtyHtml: string): string;
  generateSecureSalt(): string;
  hashPassword(password: string, salt?: string): string;
  verifyPassword(password: string, storedHash: string, salt?: string): boolean;
  generateToken(prefix?: string): string;
  computeDataIntegrityHash(jsonString: string): string;
  validateUploadFile(file: File, allowedCategory?: 'image' | 'video' | 'audio' | 'attachment'): Promise<FileValidationResult>;
}

// =============================================================================
// 8. CONTENT WORKFLOW & MEDIA ENGINES
// =============================================================================

export interface WorkflowStateConfig {
  label: string;
  badge: string;
}

export interface IWorkflowEngine {
  STATES: Record<string, WorkflowStateConfig>;
  isPostPublic(post: any): boolean;
  isEntityPublic(entity: any): boolean;
  getPendingApprovalCount(): number;
  recordApprovalAction(
    targetType: string,
    targetId: string,
    title: string,
    version: number,
    decision: string,
    notes?: string
  ): void;
}

export interface IMediaPlayerEngine {
  vttBlobCache: Record<string, string>;
  getWebVttBlobUrl(postId: string, subtitleText?: string): string;
}

// =============================================================================
// 9. LIVE VISUAL CMS & GESTALT CMS STUDIO
// =============================================================================

export interface ILiveVisualCMS {
  isActive(): boolean;
  toggleLiveMode(): void;
  toggleInlineTextEdit(): void;
  applyInlineEditableAttributes(): void;
  renderFloatingAdminDock(): void;
  openQuickSiteTextModal(): void;
  openQuickPostModal(postId?: string | null, prefillCategoryId?: string): void;
  openQuickCategoryModal(catId?: string | null): void;
  openQuickSubcategoryModal(parentId: string, subId?: string | null): void;
  openQuickFaqModal(faqId?: string | null): void;
  openQuickQuizModal(quizId?: string | null): void;
  openQuickMajorModal(majorId?: string | null): void;
  openQuickAnnouncementModal(annId?: string | null): void;
  openQuickCalendarEventModal(eventId?: string | null): void;
  openQuickShortTipModal(tipId?: string | null): void;
  saveQuickEntity(type: string, entityData: any): void;
  deleteQuickEntity(type: string, id: string): void;
  wrapSectionWithLiveControls(sectionKey: string, title: string, innerHtml: string, addModalFn?: string): string;
  wrapCardWithLiveControls(type: string, id: string, innerHtml: string, editModalFn?: string, deleteModalFn?: string): string;
}

export interface IUnifiedCMSStudio {
  openStudio(initialTab?: string): void;
  openCategoryEditor(catId: string): void;
  openSubcategoryEditor(catId: string, subId: string): void;
  openPostEditor(postId: string | null): void;
  openFaqEditor(faqId: string): void;
  openQuizFullEditor(quizId: string): void;
  openMajorFullEditor(index: number): void;
  openPathEditor(index: number): void;
  saveCategoryEditor(catId: string): void;
  saveSubcategoryEditor(catId: string, subId: string): void;
  savePostEditor(postId: string, isDraft?: boolean): void;
  saveFaqEditor(faqId: string): void;
  saveQuizFullEditor(quizId: string): void;
  saveMajorFullEditor(index: number): void;
  savePathEditor(index: number): void;
  saveIdentity(): void;
  deleteCategory(catId: string): void;
  deleteSub(catId: string, subId: string): void;
  deletePostForever(postId: string): void;
  deleteFaqItem(faqId: string): void;
  moveItem(listKey: string, index: number, direction: number): void;
  moveSubcategory(catId: string, index: number, direction: number): void;
  toggleCategoryActive(catId: string): void;
  togglePostPublish(postId: string): void;
  swapListByNumbers(listKey: string): void;
  swapSubcategoriesByNumber(catId: string): void;
  demoteMainCategoryTo(catId: string, targetParentId: string): void;
  promoteSubToMain(catId: string, subId: string): void;
  addCategoryOrSub(): void;
  addFaq(): void;
  addNewQuiz(): void;
  addMajor(): void;
  addPath(): void;
  addUniversity(): void;
  removeItem(listKey: string, index: number): void;
  addQuizQuestion(quizId: string): void;
  deleteQuizQuestion(quizId: string, qIdx: number): void;
  addDefaultChecklist(): void;
  deleteDefaultChecklist(index: number): void;
  [key: string]: any;
}

// =============================================================================
// 10. STUDY PLANS DATABASE (STUDY_PLANS_DATABASE)
// =============================================================================

export interface StudyPlanPrioritySubject {
  name: string;
  note: string;
}

export interface StudyPlanScheduleDay {
  day: string;
  p1: string;
  p2: string;
  p3: string;
  p4: string;
  p5: string;
  target: string;
}

export interface StudyPlan {
  gradeCode: '10' | '11' | '12' | string;
  gradeLabel: string;
  majorCode: 'tajrobi' | 'ensani' | 'riazi' | string;
  majorLabel: string;
  majorIcon: string;
  themeColor: string;
  badgeClass: string;
  headerGradient: string;
  title: string;
  subtitle: string;
  counselorQuote: string;
  weeklyHours: string;
  examSplit: string;
  prioritySubjects: StudyPlanPrioritySubject[];
  schedule: StudyPlanScheduleDay[];
}

export type StudyPlansDatabase = Record<
  | '10_tajrobi'
  | '10_ensani'
  | '10_riazi'
  | '11_tajrobi'
  | '11_ensani'
  | '11_riazi'
  | '12_tajrobi'
  | '12_ensani'
  | '12_riazi'
  | string,
  StudyPlan
>;

// =============================================================================
// 11. STUDENT GAMIFICATION
// =============================================================================

export interface StudentGamificationStats {
  completedCount: number;
  studyMinutes: number;
  quizCount: number;
  bookmarkCount: number;
  xp: number;
  level: number;
  levelTitle: string;
  nextLevelXp: number;
  progressPercent: number;
}

// =============================================================================
// 12. AMBIENT GLOBAL VARIABLES & OBJECTS
// =============================================================================

declare global {
  // Application Data & State
  let DB: AppDatabase;
  let STATE: AppState;
  const STUDY_PLANS_DATABASE: StudyPlansDatabase;

  // Runtime Engines & Services
  const AuthService: IAuthService;
  const CloudSync: ICloudSync;
  const OnlineShamsiCalendar: IOnlineShamsiCalendar;
  const JalaliDateEngine: IJalaliDateEngine;
  const MediaStorageIDB: IMediaStorageIDB;
  const SecurityEngine: ISecurityEngine;
  const WorkflowEngine: IWorkflowEngine;
  const MediaPlayerEngine: IMediaPlayerEngine;
  const LiveVisualCMS: ILiveVisualCMS;
  const UnifiedCMSStudio: IUnifiedCMSStudio;

  // Constants & Catalogs
  const DB_STORAGE_KEY: string;
  const AUTH_SESSION_KEY_V3: string;
  const PERMISSIONS_CATALOG: Array<{ id: string; code: string; title: string }>;
  const ROLES_V3: Array<{ id: string; name: string; description: string; permissions: string[] }>;

  // Global Flags
  let isAppMode: boolean;
  let isModalOpen: boolean;

  // Global Routing Functions
  function navigateTo(view: AppView | string, params?: Record<string, any>, skipHashUpdate?: boolean): void;
  function handleHashChangeRoute(): void;
  function renderApp(): void;
  function renderHomeView(): string;
  function renderCategoriesListView(): string;
  function renderSingleCategoryView(): string;
  function renderInteractiveShamsiCalendarWidget(targetJy?: number, targetJm?: number, selectedJd?: number, containerId?: string): string;

  // Global UI Utilities
  function showToast(message: string, type?: ToastType): void;
  function openModal(htmlContent: string, modalId?: string): void;
  function closeModal(fromPopstate?: boolean): void;
  function toggleMegaCategories(forceState?: boolean): void;
  function toggleMobileMenu(forceState?: boolean): void;
  function toggleReadingMode(): void;
  function updateReadingModeBtn(): void;
  function closeHeaderSearchDropdown(): void;

  // Global Modal Controllers
  function openStaffLoginModal(redirectParams?: any): void;
  function openPasswordRecoveryModal(): void;
  function openShamsiCalendarModal(targetJy?: number, targetJm?: number, targetJd?: number): void;
  function openAddToReadingListModal(postId: string): void;
  function openAskCounselorModal(): void;
  function openCounselorModal(): void;
  function openBreathingZenModal(): void;
  function openRubikaChat(): void;
  function openAboutModal(): void;
  function openContactModal(): void;
  function openPrivacyModal(): void;
  function openTermsModal(): void;
  function openSwitchUserModal(): void;
  function openSitemapModal(): void;
  function openEditorForNewPost(): void;
  function openEditorForPost(postId: string): void;
  function openRejectOrRevisionModal(postId: string, mode: 'reject' | 'revision'): void;
  function openRevisionHistoryAndDiffModal(postId: string): void;
  function openEditCompassItemModal(itemId: string): void;

  // Pomodoro & Study Tools Suite
  function setPomodoroMode(mode: PomodoroMode | string, minutes: number): void;
  function togglePomodoroTimer(): void;
  function resetPomodoroTimer(): void;
  function completeAndLogStudySession(autoFinished?: boolean): void;
  function addScheduleBlock(): void;
  function deleteScheduleBlock(id: string): void;
  function addChecklistItem(): void;
  function deleteChecklistItem(id: string): void;
  function resetDailyChecklist(): void;
  function addNewGoalItem(): void;
  function incrementGoalProgress(id: string, delta: number): void;
  function addPersonalNote(): void;
  function startEditPersonalNote(id: string): void;
  function deletePersonalNote(id: string): void;
  function purgeCurrentStudentPersonalData(): void;

  // Database Management
  function loadDatabase(): AppDatabase;
  function saveDatabase(dbObj?: any, isExplicitAdminEdit?: boolean): void;
  function getCleanDatabaseForStorage(sourceDb?: any): any;
  function syncCategoryCountBadges(): void;
  function upgradeAndMigrateDatabaseV3(rawDb: any): AppDatabase;

  // Logging & Audit
  function logAdminAction(actionText: string): void;
  function logStudentActivity(actionText: string): void;

  // Text, Digits & Escaping
  function toPersianDigits(val: any): string;
  function toFaNum(val: any): string;
  function escapeHtml(input: any): string;
  function sanitizeRichHtml(dirtyHtml: string): string;

  // Gamification & Social
  function getStudentGamificationStats(): StudentGamificationStats;
  function renderPostCard(p: any): string;
  function sharePost(postId: string): void;
  function toggleBookmarkPost(postId: string): void;
  function toggleCompletedPost(postId: string): void;

  // Shamsi Calendar Ticker & Switchers
  function changeShamsiCalendarMonth(jy: number, jm: number, containerId?: string, targetDay?: number): void;
  function selectShamsiCalendarDay(jy: number, jm: number, jd: number, containerId?: string): void;

  // Window Extensions
  interface Window {
    DB: AppDatabase;
    STATE: AppState;
    AuthService: IAuthService;
    CloudSync: ICloudSync;
    OnlineShamsiCalendar: IOnlineShamsiCalendar;
    JalaliDateEngine: IJalaliDateEngine;
    MediaStorageIDB: IMediaStorageIDB;
    SecurityEngine: ISecurityEngine;
    WorkflowEngine: IWorkflowEngine;
    LiveVisualCMS: ILiveVisualCMS;
    UnifiedCMSStudio: IUnifiedCMSStudio;
    STUDY_PLANS_DATABASE: StudyPlansDatabase;

    __HAMRAH_IS_APP_MODE?: boolean;
    __HAMRAH_TW_CONFIG?: any;
    __REFD?: boolean;
    __zenTimer?: any;
    __ftObs?: any;
    tailwind?: any;

    toPersianDigits(val: any): string;
    escapeHtml(input: any): string;
    sanitizeRichHtml(dirtyHtml: string): string;

    navigateTo: typeof navigateTo;
    showToast: typeof showToast;
    openModal: typeof openModal;
    closeModal: typeof closeModal;
    renderApp: typeof renderApp;
    renderHomeView: typeof renderHomeView;
    renderCategoriesListView: typeof renderCategoriesListView;
    renderSingleCategoryView: typeof renderSingleCategoryView;
    renderInteractiveShamsiCalendarWidget: typeof renderInteractiveShamsiCalendarWidget;
    changeShamsiCalendarMonth: typeof changeShamsiCalendarMonth;
    selectShamsiCalendarDay: typeof selectShamsiCalendarDay;

    getStudentGamificationStats: typeof getStudentGamificationStats;
    renderPostCard: typeof renderPostCard;
    openBreathingZenModal: typeof openBreathingZenModal;
    openRubikaChat: typeof openRubikaChat;
    openAboutModal: typeof openAboutModal;
    openContactModal: typeof openContactModal;
    openPrivacyModal: typeof openPrivacyModal;
    openTermsModal: typeof openTermsModal;
    openStaffLoginModal: typeof openStaffLoginModal;
    openPasswordRecoveryModal: typeof openPasswordRecoveryModal;
    openShamsiCalendarModal: typeof openShamsiCalendarModal;
    openCounselorModal: typeof openCounselorModal;
    openRejectOrRevisionModal: typeof openRejectOrRevisionModal;
    openRevisionHistoryAndDiffModal: typeof openRevisionHistoryAndDiffModal;
    openEditCompassItemModal: typeof openEditCompassItemModal;

    toggleCompassTargetFields: (prefix: string) => void;
    adminSaveCompassGeneralSettings: () => void;
    adminAddCompassItem: () => void;
    adminSaveEditedCompassItem: (itemId: string) => void;
    adminDeleteCompassItem: (itemId: string) => void;
    adminMoveCompassItem: (itemId: string, direction: number) => void;
    adminResetCompassDefaults: () => void;

    changeArticleFontSize: (delta: number) => void;
    refGrade: (i: number) => void;
    refQuiz: (a?: number) => void;
    qi0: () => void;
    refSearch: (q: string) => void;
    refFind: (q: string) => void;
    refFooter: () => void;
  }
}
