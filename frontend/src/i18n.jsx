/**
 * KUECSF Counseling – Bilingual UI  (English 🇬🇧 / አማርኛ 🇪🇹)
 *
 * Usage:
 *   const { t, lang, setLang } = useLang();
 *   <p>{t("welcome")}</p>
 *
 * Language is persisted in localStorage so it survives page refreshes.
 */
import { createContext, useCallback, useContext, useState } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// Translation table
// ─────────────────────────────────────────────────────────────────────────────
const TRANSLATIONS = {
  en: {
    // ── Shell / nav ───────────────────────────────────────────────────────────
    appName: "KUECSF Counseling",
    appSubtitle: "Care workspace",
    signOut: "Sign out",
    toggleTheme: "Toggle color theme",

    // ── Login page ────────────────────────────────────────────────────────────
    secureSignIn: "Secure sign in",
    welcomeBack: "Welcome back! 👋",
    loginHint: "Use your username and the password set for your account.",
    usernamePlaceholder: "Username",
    usernameLabel: "Username",
    passwordLabel: "Password",
    signingIn: "Signing in…",
    signIn: "Sign in",
    loginError: "Could not sign in. Check your username and password.",

    // ── Admin dashboard ───────────────────────────────────────────────────────
    operationsOverview: "Overview",
    adminManagement: "Admin panel",
    adminSubtitle: "Manage adviser accounts, assign users, and view activity.",
    careTeam: "Care team",
    advisers: "advisers",
    tabAssignments: "Assignments",
    tabAdvisers: "Advisers",
    tabActivity: "Activity",

    // ── Intake / assignment queue ─────────────────────────────────────────────
    intakeQueue: "Incoming requests",
    awaitingAssignment: "waiting to be assigned",
    loadingIntakes: "Loading requests…",
    colUser: "User",
    colAge: "Age",
    colConcern: "Concern",
    colAssignAdviser: "Assign adviser",
    chooseAdviser: "Choose adviser…",
    telegramUser: "Telegram user",
    noIntakeYet: "No pending requests",
    noIntakeDesc: "New user intakes from the Telegram bot will appear here.",

    // ── Adviser (psychiatrist) card ───────────────────────────────────────────
    advisersSection: "Advisers",
    advisersSectionDesc: "Accounts registered as care advisers.",
    statusAvailable: "Available",
    statusBusy: "Busy",
    statusInactive: "Inactive",
    caseLimit: "Case limit",
    savingLimit: "Saving…",
    saveLimit: "Save limit",
    viewUsers: "View users",
    hideUsers: "Hide users",
    assignedUsers: "Assigned users",
    loadingUsers: "Loading users…",
    noUsersAssigned: "No users assigned yet.",
    waitingFirstLogin: "Waiting for first sign-in and password change.",

    // ── Activity log ──────────────────────────────────────────────────────────
    interactionActivity: "Activity log",
    activityDesc: "Message counts and timestamps per conversation.",
    colAdviserName: "Adviser",
    colMessages: "Messages",
    colUserAdviser: "User / Adviser",
    colLatest: "Latest activity",
    noActivityYet: "No activity yet",
    noActivityDesc: "Conversation counts will appear here when messages are exchanged.",

    // ── Adviser dashboard (clinician) ─────────────────────────────────────────
    clinicalWorkspace: "Your workspace",
    yourUsers: "Your assigned users",
    yourUsersSubtitle: "Open a user to continue the conversation.",
    activeCases: "Active conversations",
    assignedToYou: "Assigned to your account",
    caseOverview: "Overview",
    yourWorkload: "Your current workload",
    chatSyncNote: "Chats sync automatically every few seconds while open.",
    loadingUsers2: "Loading users…",
    noActiveCases: "No active conversations yet",
    noActiveCasesDesc: "New assignments will appear in your workspace.",
    intakeDate: "Intake",
    yearsOld: "yrs",

    // ── Chat page ─────────────────────────────────────────────────────────────
    backToUsers: "← Back to users",
    openNotesSeparately: "Open notes separately",
    couldNotLoadUser: "Could not load this user.",
    userConversation: "User conversation",
    loadingUser: "Loading user…",
    telegramChat: "Telegram chat",
    intake: "Intake",
    typeMessage: "Type a message…",
    send: "Send",
    sending: "Sending…",
    editMessage: "Edit",
    cancelEdit: "Cancel",
    saveEdit: "Save",
    deleteForMe: "Delete for me",
    deleteForAll: "Delete for all",
    youLabel: "You",
    userLabel: "User",
    editedLabel: "edited",
    deletedLabel: "Message removed",
    noMessages: "No messages yet",
    noMessagesDesc: "Send a message below to start the conversation.",

    // ── Notes panel ───────────────────────────────────────────────────────────
    privateNotes: "Private notes",
    onlyVisibleToYou: "only visible to you",
    addNotePlaceholder: "Write a private note about this user…",
    privateToAccount: "Private to your account",
    addNote: "Add note",
    loadingNotes: "Loading notes…",
    noNotesYet: "No notes yet",
    noNotesDesc: "Add private notes to keep track of this user's care.",
    editNote: "Edit note",
    deleteNote: "Delete note",
    confirmDeleteNote: "Delete this private note? This cannot be undone.",
    saving: "Saving…",
    save: "Save",
    cancel: "Cancel",

    // ── Notes page (standalone) ───────────────────────────────────────────────
    privateNotesFor: "Private notes for",
    backToChat: "← Back to chat",

    // ── Change password page ──────────────────────────────────────────────────
    changePassword: "Set your password",
    changePasswordSubtitle: "Create a personal password before you continue.",
    newPassword: "New password",
    confirmPassword: "Confirm password",
    passwordsDontMatch: "Passwords do not match.",
    passwordTooShort: "Password must be at least 12 characters.",
    changingPassword: "Saving…",
    setPassword: "Set password",

    // ── Footer ────────────────────────────────────────────────────────────────
    footer: "KUECSF Counseling · Handle user information according to your organisation's privacy policy.",

    // ── Misc ──────────────────────────────────────────────────────────────────
    loadingDashboard: "Loading…",
    errorLoadingDashboard: "Could not load dashboard data.",
    assignmentFailed: "Assignment failed.",
    dateUnavailable: "date unavailable",
    assigned: "Assigned",
  },

  am: {
    // ── Shell / nav ───────────────────────────────────────────────────────────
    appName: "KUECSF Counseling",
    appSubtitle: "የእንክብካቤ ስፍራ",
    signOut: "ውጣ",
    toggleTheme: "ጨለማ/ብሩህ ቀይር",

    // ── Login page ────────────────────────────────────────────────────────────
    secureSignIn: "ደህና ግቡ",
    welcomeBack: "እንኳን ደህና መጡ! 👋",
    loginHint: "የተጠቃሚ ስምዎን እና የይለፍ ቃልዎን ያስገቡ።",
    usernamePlaceholder: "የተጠቃሚ ስም",
    usernameLabel: "የተጠቃሚ ስም",
    passwordLabel: "የይለፍ ቃል",
    signingIn: "እየገባ ነው…",
    signIn: "ግባ",
    loginError: "መግባት አልተቻለም። ስምዎን እና የይለፍ ቃልዎን ያረጋግጡ።",

    // ── Admin dashboard ───────────────────────────────────────────────────────
    operationsOverview: "አጠቃላይ እይታ",
    adminManagement: "አስተዳዳሪ ፓነል",
    adminSubtitle: "አማካሪዎችን ያስተዳድሩ፣ ተጠቃሚዎችን ይመድቡ፣ እና ተግባሮችን ይከታተሉ።",
    careTeam: "የእንክብካቤ ቡድን",
    advisers: "አማካሪዎች",
    tabAssignments: "ምደባዎች",
    tabAdvisers: "አማካሪዎች",
    tabActivity: "ተግባራት",

    // ── Intake / assignment queue ─────────────────────────────────────────────
    intakeQueue: "አዳዲስ ጥያቄዎች",
    awaitingAssignment: "ምደባ እየጠበቁ",
    loadingIntakes: "ጥያቄዎችን እየጫነ ነው…",
    colUser: "ተጠቃሚ",
    colAge: "እድሜ",
    colConcern: "ጉዳይ",
    colAssignAdviser: "አማካሪ ምደብ",
    chooseAdviser: "አማካሪ ምረጥ…",
    telegramUser: "የቴሌግራም ተጠቃሚ",
    noIntakeYet: "ምንም ጥያቄ የለም",
    noIntakeDesc: "ከቴሌግራም ቦት የሚመጡ አዳዲስ ጥያቄዎች እዚህ ይታያሉ።",

    // ── Adviser (psychiatrist) card ───────────────────────────────────────────
    advisersSection: "አማካሪዎች",
    advisersSectionDesc: "እንደ አማካሪ የተመዘገቡ አካውንቶች።",
    statusAvailable: "ዝግጁ",
    statusBusy: "ተጠምዷል",
    statusInactive: "ፈቃደ ወጥቷል",
    caseLimit: "የጉዳይ ወሰን",
    savingLimit: "እየቀመጠ ነው…",
    saveLimit: "ወሰን አስቀምጥ",
    viewUsers: "ተጠቃሚዎች ይመልከቱ",
    hideUsers: "ተጠቃሚዎቹን ደብቅ",
    assignedUsers: "የተመደቡ ተጠቃሚዎች",
    loadingUsers: "ተጠቃሚዎችን እየጫነ ነው…",
    noUsersAssigned: "እስካሁን ምንም ተጠቃሚ አልተመደበም።",
    waitingFirstLogin: "ለመጀመሪያ ጊዜ ስለ መግባትና የይለፍ ቃልን ስለ መቀየር ይጠበቃል።",

    // ── Activity log ──────────────────────────────────────────────────────────
    interactionActivity: "የተግባር ምዝግብ",
    activityDesc: "በእያንዳንዱ ንግግር ውስጥ የመልዕክቶች ቁጥር እና ሰዓት።",
    colAdviserName: "አማካሪ",
    colMessages: "መልዕክቶች",
    colUserAdviser: "ተጠቃሚ / አማካሪ",
    colLatest: "የመጨረሻ ተግባር",
    noActivityYet: "እስካሁን ምንም ተግባር የለም",
    noActivityDesc: "መልዕክቶች ሲለዋወጡ የቁጥር ዝርዝር እዚህ ይታያሉ።",

    // ── Adviser dashboard (clinician) ─────────────────────────────────────────
    clinicalWorkspace: "የእርስዎ ስፍራ",
    yourUsers: "የተመደቡ ተጠቃሚዎችዎ",
    yourUsersSubtitle: "ንግግርን ለመቀጠል ተጠቃሚ ይክፈቱ።",
    activeCases: "ንቁ ንግግሮች",
    assignedToYou: "ለእርስዎ አካውንት የተመደቡ",
    caseOverview: "አጠቃላይ",
    yourWorkload: "አሁናዊ ሥራዎ",
    chatSyncNote: "ንግግሮቹ ሲከፈቱ ሁሌም ይዘምናሉ።",
    loadingUsers2: "ተጠቃሚዎችን እየጫነ ነው…",
    noActiveCases: "ምንም ንቁ ንግግር የለም",
    noActiveCasesDesc: "አዳዲስ ምደባዎች ሲደርሱ ይታያሉ።",
    intakeDate: "ምዝገባ",
    yearsOld: "ዓ",

    // ── Chat page ─────────────────────────────────────────────────────────────
    backToUsers: "← ወደ ዝርዝር ተመለስ",
    openNotesSeparately: "ማስታወሻዎቹን ለብቻ ክፈት",
    couldNotLoadUser: "ተጠቃሚውን መጫን አልተቻለም።",
    userConversation: "የተጠቃሚ ንግግር",
    loadingUser: "ተጠቃሚ እየጫነ ነው…",
    telegramChat: "ቴሌግራም ንግግር",
    intake: "ምዝገባ",
    typeMessage: "መልዕክት ይጻፉ…",
    send: "ላክ",
    sending: "እየተላከ ነው…",
    editMessage: "አርትዕ",
    cancelEdit: "ሰርዝ",
    saveEdit: "አስቀምጥ",
    deleteForMe: "ለእኔ ብቻ ሰርዝ",
    deleteForAll: "ለሁሉም ሰርዝ",
    youLabel: "እርስዎ",
    userLabel: "ተጠቃሚ",
    editedLabel: "ተስተካክሏል",
    deletedLabel: "መልዕክቱ ተሰርዟል",
    noMessages: "እስካሁን ምንም መልዕክት የለም",
    noMessagesDesc: "ንግግሩን ለመጀመር ከታች ይጻፉ።",

    // ── Notes panel ───────────────────────────────────────────────────────────
    privateNotes: "የግል ማስታወሻዎች",
    onlyVisibleToYou: "ለእርስዎ ብቻ የሚታይ",
    addNotePlaceholder: "ስለዚህ ተጠቃሚ የግል ማስታወሻ ይጻፉ…",
    privateToAccount: "ለእርስዎ አካውንት ብቻ",
    addNote: "ማስታወሻ ጨምር",
    loadingNotes: "ማስታወሻዎችን እየጫነ ነው…",
    noNotesYet: "ምንም ማስታወሻ የለም",
    noNotesDesc: "ስለ ተጠቃሚው ሁኔታ ለመከታተል የግል ማስታወሻዎች ይጨምሩ።",
    editNote: "ማስታወሻ አርትዕ",
    deleteNote: "ማስታወሻ ሰርዝ",
    confirmDeleteNote: "ይህን የግል ማስታወሻ ሰርዞ ይወገዳል፣ ሊቀለበስ አይችልም። ይቀጥሉ?",
    saving: "እየቀመጠ ነው…",
    save: "አስቀምጥ",
    cancel: "ሰርዝ",

    // ── Notes page (standalone) ───────────────────────────────────────────────
    privateNotesFor: "ለ",
    backToChat: "← ወደ ንግግር ተመለስ",

    // ── Change password page ──────────────────────────────────────────────────
    changePassword: "የይለፍ ቃልዎን ያዘጋጁ",
    changePasswordSubtitle: "ከመቀጠልዎ በፊት የራስዎ የይለፍ ቃል ያስቀምጡ።",
    newPassword: "አዲስ የይለፍ ቃል",
    confirmPassword: "የይለፍ ቃልን ያረጋግጡ",
    passwordsDontMatch: "የይለፍ ቃሎቹ አይዛመዱም።",
    passwordTooShort: "የይለፍ ቃሉ ቢያንስ 12 ቁምፊ ሊኖረው ይገባል።",
    changingPassword: "እየቀመጠ ነው…",
    setPassword: "የይለፍ ቃል አስቀምጥ",

    // ── Footer ────────────────────────────────────────────────────────────────
    footer: "KUECSF Counseling· የተጠቃሚ መረጃን የድርጅትዎን የግላዊነት ፖሊሲ ተከትሎ ያስተዳድሩ።",

    // ── Misc ──────────────────────────────────────────────────────────────────
    loadingDashboard: "እየጫነ ነው…",
    errorLoadingDashboard: "ዳሽቦርዱን መጫን አልተቻለም።",
    assignmentFailed: "ምደባው አልተሳካም።",
    dateUnavailable: "ቀን አልተገኘም",
    assigned: "ተመድቧል",
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Context
// ─────────────────────────────────────────────────────────────────────────────
const LangContext = createContext(null);

const STORAGE_KEY = "KUECSF Counseling_ui_lang";

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === "am" || saved === "en" ? saved : "en";
  });

  const setLang = useCallback((next) => {
    if (next === "am" || next === "en") {
      localStorage.setItem(STORAGE_KEY, next);
      setLangState(next);
    }
  }, []);

  const t = useCallback(
    (key) => TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS["en"]?.[key] ?? key,
    [lang]
  );

  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used inside <LangProvider>");
  return ctx;
}

