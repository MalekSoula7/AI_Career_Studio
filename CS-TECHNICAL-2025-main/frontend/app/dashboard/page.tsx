"use client";

import api, { getErrorMessage, type ReviewResponse, type Job } from "@/lib/api";
import { useAuthGuard } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { ChangeEvent, DragEvent, useEffect, useState } from "react";

export default function DashboardPage() {
    const router = useRouter();
    const { loading, email } = useAuthGuard();
    const [signingOut, setSigningOut] = useState(false);
    const [resumeId, setResumeId] = useState<string | null>(
        typeof window !== "undefined" ? localStorage.getItem("last_resume_id") : null
    );
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const [reviewSummary, setReviewSummary] = useState<string | null>(null);
    const [reviewData, setReviewData] = useState<ReviewResponse | null>(null);
    const [reviewOpen, setReviewOpen] = useState(false);
    const [reportSummary, setReportSummary] = useState<string | null>(null);
    const [reportData, setReportData] = useState<any | null>(null);
    const [reportOpen, setReportOpen] = useState(false);
    const [loadingReview, setLoadingReview] = useState(false);
    const [loadingReport, setLoadingReport] = useState(false);
    // Matching preferences
    const [regionChoice, setRegionChoice] = useState<"MENA" | "SSA" | "Any">("MENA");
    const [workMode, setWorkMode] = useState<"remote" | "onsite" | "hybrid">("remote");
    const [countryOptions, setCountryOptions] = useState<string[]>([]);
    const [countries, setCountries] = useState<string[]>([]);
    const [skillsOverride, setSkillsOverride] = useState("");
    const [matching, setMatching] = useState(false);
    const [jobs, setJobs] = useState<Job[]>([]);
    const [jobModalOpen, setJobModalOpen] = useState(false);
    const [selectedJob, setSelectedJob] = useState<Job | null>(null);
        // Region-specific country lists (subset; can be expanded)
        const MENA_COUNTRIES = [
            "Algeria","Bahrain","Djibouti","Egypt","Iran","Iraq","Israel","Jordan",
            "Kuwait","Lebanon","Libya","Mauritania","Morocco","Oman","Palestine",
            "Qatar","Saudi Arabia","Tunisia","United Arab Emirates","Yemen","Sudan"
        ];
        const SSA_COUNTRIES = [
            "Kenya","Nigeria","Ghana","Ethiopia","Uganda","Tanzania","South Africa",
            "Rwanda","Senegal","Ivory Coast","Cameroon","Zimbabwe","Zambia","Mozambique"
        ];

        // Update country options when region changes
        const updateCountryOptions = (r: "MENA" | "SSA" | "Any") => {
            if (r === "MENA") setCountryOptions(MENA_COUNTRIES);
            else if (r === "SSA") setCountryOptions(SSA_COUNTRIES);
            else setCountryOptions([]);
        };

        // Initialize and update country options on region change
        useEffect(() => {
            updateCountryOptions(regionChoice);
            setCountries([]);
            // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [regionChoice]);
    const [refining, setRefining] = useState(false);
    const [covering, setCovering] = useState(false);
    const [refineResult, setRefineResult] = useState<{
        summary_suggestion?: string;
        keywords_to_emphasize?: string[];
        experience_bullets?: string[];
        skills_to_add?: string[];
        notes?: string;
        raw_response?: string;
    } | null>(null);
    const [coverLetter, setCoverLetter] = useState<string | null>(null);
    const [jobModalTab, setJobModalTab] = useState<"refine" | "cover" | "none">("none");
    const [startingInterview, setStartingInterview] = useState(false);
    const [role, setRole] = useState("Software Engineer");
    const [sessionInfo, setSessionInfo] = useState<
        { session_id: string; first?: { text?: string } | null } | null
    >(null);
    const [deletingResume, setDeletingResume] = useState(false);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-200">
                <p className="text-sm text-slate-400">Checking your session...</p>
            </div>
        );
    }

    const handleLogout = () => {
        setSigningOut(true);
        api.logout();
        router.replace("/login");
    };

    const handleDeleteResume = async () => {
        if (!resumeId) return;
        setDeletingResume(true);
        try {
            await api.deleteResume(resumeId);
            setResumeId(null);
            setReviewData(null);
            setReviewSummary(null);
            setReportData(null);
            setReportSummary(null);
            setJobs([]);
            setSkillsOverride("");
            setCountries([]);
            if (typeof window !== "undefined") {
                localStorage.removeItem("last_resume_id");
            }
        } finally {
            setDeletingResume(false);
        }
    };

    const handleFile = async (file: File) => {
        setUploadError(null);
        if (!file) return;
        setUploading(true);
        try {
            const { resume_id } = await api.uploadResume(file);
            setResumeId(resume_id);
            if (typeof window !== "undefined") {
                localStorage.setItem("last_resume_id", resume_id);
            }
        } catch (err) {
            setUploadError(getErrorMessage(err));
        } finally {
            setUploading(false);
        }
    };

    const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
    };

    const onDrop = (e: DragEvent<HTMLLabelElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        const file = e.dataTransfer.files?.[0];
        if (file) handleFile(file);
    };

    const onDragOver = (e: DragEvent<HTMLLabelElement>) => {
        e.preventDefault();
        e.stopPropagation();
        if (!dragActive) setDragActive(true);
    };

    const onDragLeave = (e: DragEvent<HTMLLabelElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
    };

    const handleReview = async () => {
        if (!resumeId) return;
        setLoadingReview(true);
        try {
            const review = await api.reviewResume(resumeId);
            setReviewData(review);
            const s = review?.overall?.score;
            const strengths = (review?.strengths || []).slice(0, 2).join(", ");
            setReviewSummary(`Score: ${s ?? "n/a"} • Strengths: ${strengths}`);
            setReviewOpen(true);
        } finally {
            setLoadingReview(false);
        }
    };

    const handleReport = async () => {
        if (!resumeId) return;
        setLoadingReport(true);
        try {
            const report = await api.getCareerReport(resumeId);
            console.log("[CareerReport] Full API response:", JSON.stringify(report, null, 2));

            // Prefer high-level narrative if present
            const summary =
                report?.career_report?.summary ||
                report?.career_report?.narrative_summary ||
                report?.review?.summary ||
                null;
            setReportData(report);
            setReportSummary(summary);
            setReportOpen(true);
        } finally {
            setLoadingReport(false);
        }
    };

    const handleMatch = async () => {
        if (!resumeId) return;
        setMatching(true);
        try {
            const skillsArr = skillsOverride
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean);
            const matchPayload = {
                region: regionChoice === "Any" ? undefined : regionChoice,
                workMode,
                countries: countries,
                skillsOverride: skillsArr.length ? skillsArr : undefined,
            };
            console.log("[MatchJobs] Sending payload:", matchPayload);
            const res = await api.matchJobs(resumeId, matchPayload);
            setJobs(res.jobs);
        } finally {
            setMatching(false);
        }
    };

    const handleStartInterview = async () => {
        if (!resumeId) return;
        setStartingInterview(true);
        try {
            const res = await api.startInterview(resumeId, role);
            // Redirect to dedicated interview page with session_id & role
            router.push(
                `/interview?session_id=${res.session_id}&resume_id=${resumeId}&role=${encodeURIComponent(
                    role
                )}`
            );
        } finally {
            setStartingInterview(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col">
            <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-sm">
                <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="h-8 w-8 rounded-xl bg-sky-500/90 flex items-center justify-center text-xs font-bold text-slate-950">
                            AI
                        </div>
                        <div>
                            <p className="text-sm font-medium">Career Studio</p>
                            <p className="text-xs text-slate-400">Interview • Match • Insights</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {email && (
                            <p className="text-xs text-slate-400 hidden sm:block">
                                Signed in as <span className="text-slate-100">{email}</span>
                            </p>
                        )}
                        <button
                            onClick={handleLogout}
                            disabled={signingOut}
                            className="text-xs rounded-full border border-slate-600 px-3 py-1.5 bg-slate-900/60 hover:bg-slate-800 transition-colors disabled:opacity-60"
                        >
                            {signingOut ? "Signing out..." : "Sign out"}
                        </button>
                    </div>
                </div>
            </header>

            <main className="flex-1">
                <div className="max-w-5xl mx-auto px-4 py-8 grid gap-6 md:grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)]">
                    {/* Left column - primary actions */}
                    <section className="space-y-4">
                        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 shadow-lg shadow-slate-950/40 space-y-4">
                            <h2 className="text-lg font-semibold mb-1">Welcome back</h2>
                            <p className="text-sm text-slate-400 mb-4">
                                Start by uploading a resume (PDF, DOC, DOCX), then we&apos;ll help
                                you review it, match roles and generate a career report.
                            </p>

                            <div className="space-y-3">
                                <label
                                    onDrop={onDrop}
                                    onDragOver={onDragOver}
                                    onDragLeave={onDragLeave}
                                    className={`flex flex-col items-center justify-center rounded-xl border border-dashed px-4 py-6 text-sm cursor-pointer transition-colors ${dragActive
                                            ? "border-sky-400 bg-sky-500/5"
                                            : "border-slate-700 bg-slate-900/80 hover:border-sky-500 hover:bg-slate-900"
                                        }`}
                                >
                                    <input
                                        type="file"
                                        accept=".pdf,.doc,.docx,.txt"
                                        onChange={onFileChange}
                                        className="hidden"
                                    />
                                    <span className="text-slate-100 font-medium mb-1">
                                        {uploading ? "Uploading resume..." : "Drag & drop CV here"}
                                    </span>
                                    <span className="text-xs text-slate-500">
                                        or click to browse — PDF or DOC up to 10MB.
                                    </span>
                                </label>

                                {uploadError && (
                                    <p className="text-xs text-rose-400 bg-rose-950/40 border border-rose-900/60 rounded-lg px-3 py-2">
                                        {uploadError}
                                    </p>
                                )}

                                {resumeId && (
                                    <div className="flex items-center justify-between gap-2">
                                        <p className="text-xs text-emerald-400">
                                            Resume uploaded. ID: <span className="font-mono">{resumeId}</span>
                                        </p>
                                        <button
                                            type="button"
                                            onClick={handleDeleteResume}
                                            disabled={deletingResume}
                                            className="text-[11px] px-2 py-1 rounded-md border border-rose-600/70 bg-rose-900/20 text-rose-200 hover:bg-rose-900/40 disabled:opacity-60"
                                        >
                                            {deletingResume ? "Resetting..." : "Delete CV"}
                                        </button>
                                    </div>
                                )}
                            </div>

                            <div className="grid gap-3 sm:grid-cols-2 pt-2 border-t border-slate-800 mt-4">
                                <button
                                    onClick={handleReview}
                                    disabled={!resumeId || loadingReview}
                                    className="rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-xs text-slate-300 flex flex-col gap-1 disabled:opacity-50"
                                >
                                    <span className="text-slate-100 font-medium text-sm">
                                        {loadingReview ? "Fetching review..." : "Resume review"}
                                    </span>
                                    <span className="text-[11px] text-slate-500">
                                        Get a quick automated assessment of this CV.
                                    </span>
                                    {reviewSummary && (
                                        <span className="text-[11px] text-emerald-300 mt-1 line-clamp-2">
                                            {reviewSummary}
                                        </span>
                                    )}
                                </button>

                                <button
                                    onClick={handleReport}
                                    disabled={!resumeId || loadingReport}
                                    className="rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-xs text-slate-300 flex flex-col gap-1 disabled:opacity-50"
                                >
                                    <span className="text-slate-100 font-medium text-sm">
                                        {loadingReport ? "Building report..." : "Career report"}
                                    </span>
                                    <span className="text-[11px] text-slate-500">
                                        (start an ai interview first)Combine review, interviews and market data into a snapshot.
                                    </span>
                                    {reportSummary && (
                                        <span className="text-[11px] text-sky-300 mt-1 line-clamp-2">
                                            {reportSummary}
                                        </span>
                                    )}
                                </button>
                            </div>
                        </div>
                    </section>
                    <aside className="space-y-4">
                        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 flex flex-col gap-3">
                            <h3 className="text-sm font-semibold text-slate-100">
                                Quick AI interview
                            </h3>
                            <div className="space-y-2 text-xs text-slate-400">
                                <p>
                                    Pick a target role and start an AI interview once your resume
                                    is uploaded.
                                </p>
                                <input
                                    type="text"
                                    value={role}
                                    onChange={(e) => setRole(e.target.value)}
                                    className="w-full rounded-md border border-slate-700 bg-slate-950/70 px-2 py-1 text-xs text-slate-100"
                                />
                                <button
                                    onClick={handleStartInterview}
                                    disabled={!resumeId || startingInterview}
                                    className="inline-flex items-center justify-center rounded-md bg-emerald-500/90 hover:bg-emerald-400 text-slate-950 text-xs font-medium px-3 py-1.5 disabled:opacity-50"
                                >
                                    {startingInterview ? "Starting interview..." : "Start AI interview"}
                                </button>
                                {sessionInfo && (
                                    <div className="mt-2 space-y-1 text-[11px] text-slate-300 border-t border-slate-800 pt-2">
                                        <p>
                                            Session ID: <span className="font-mono">{sessionInfo.session_id}</span>
                                        </p>
                                        {sessionInfo.first?.text && (
                                            <p className="text-slate-400">
                                                First question: <span className="text-slate-100">{sessionInfo.first.text}</span>
                                            </p>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </aside>
                    <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 flex flex-col gap-3 w-full col-span-2">
                        <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-300 text-xs">
                                ●
                            </span>
                            Session overview
                        </h3>
                        <p className="text-xs text-slate-400 mb-2">
                            Once you upload a resume, this space will summarise your latest
                            review and best-matching roles at a glance.
                        </p>

                        <div className="mt-1 space-y-3 text-xs">
                            <div className="flex flex-wrap items-center gap-3">
                                <div className="flex items-center gap-2">
                                    <span className="text-slate-400">Work mode:</span>
                                    <div className="inline-flex overflow-hidden rounded-md border border-slate-700">
                                        {(["remote","onsite","hybrid"] as const).map((m) => (
                                            <button
                                                key={m}
                                                type="button"
                                                onClick={() => setWorkMode(m)}
                                                className={`px-2 py-1 text-[11px] ${workMode===m?"bg-sky-500/20 text-sky-300":"bg-slate-900/60 text-slate-300 hover:bg-slate-800"}`}
                                            >
                                                {m === "remote" ? "Remote" : m === "onsite" ? "On-site" : "Hybrid"}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-slate-400">Region:</span>
                                    <select
                                        value={regionChoice}
                                        onChange={(e) => { const r = e.target.value as any; setRegionChoice(r); updateCountryOptions(r); setCountries([]); }}
                                        className="bg-slate-950/70 border border-slate-700 rounded-md px-2 py-1 text-xs text-slate-100"
                                    >
                                        <option value="MENA">MENA</option>
                                        <option value="SSA">Sub-Saharan Africa</option>
                                        <option value="Any">Any</option>
                                    </select>
                                </div>
                            </div>

                            <div className="grid gap-1">
                                <p className="text-slate-400">Countries (optional):</p>
                                <select
                                    multiple
                                    value={countries}
                                    onChange={(e) => {
                                        const vals = Array.from(e.target.selectedOptions).map((o) => o.value);
                                        setCountries(vals);
                                    }}
                                    className="w-full min-h-[92px] rounded-md border border-slate-700 bg-slate-950/70 px-2 py-1 text-xs text-slate-100"
                                >
                                    {countryOptions.length === 0 ? (
                                        <option disabled value="">Select a region to choose countries</option>
                                    ) : (
                                        countryOptions.map((c) => (
                                            <option key={c} value={c}>{c}</option>
                                        ))
                                    )}
                                </select>
                                <p className="text-[11px] text-slate-500">Tip: Hold Ctrl/Cmd to select multiple countries.</p>
                                <p className="text-[11px] text-slate-500 mt-1">Fairness: matching ignores name, gender, photo, and age — only skills, roles, and experience.</p>
                            </div>

                            <div className="space-y-1">
                                <p className="text-slate-400">Skills override (comma separated):</p>
                                <input
                                    type="text"
                                    value={skillsOverride}
                                    onChange={(e) => setSkillsOverride(e.target.value)}
                                    placeholder="python, react, aws"
                                    className="w-full rounded-md border border-slate-700 bg-slate-950/70 px-2 py-1 text-xs text-slate-100 placeholder:text-slate-500"
                                />
                            </div>

                            <button
                                onClick={handleMatch}
                                disabled={!resumeId || matching}
                                className="mt-1 inline-flex items-center justify-center rounded-md bg-sky-500/95 hover:bg-sky-400 text-slate-950 text-xs font-medium px-3 py-1.5 disabled:opacity-50"
                            >
                                {matching ? "Matching roles..." : "Match jobs"}
                            </button>
                        </div>

                        {jobs.length > 0 && (
                            <div className="mt-3 border-t border-slate-800 pt-3 space-y-3 w-full">
                                <p className="text-[11px] text-slate-400">Top matches:</p>
                                {/* Top Match - Featured Card */}
                                {jobs[0] && (
                                    <button
                                        onClick={() => { setSelectedJob(jobs[0]); setJobModalOpen(true); setRefineResult(null); setCoverLetter(null); setJobModalTab("none"); }}
                                        className="text-left rounded-xl border-2 border-emerald-500/40 bg-gradient-to-br from-emerald-500/5 to-sky-500/5 hover:from-emerald-500/10 hover:to-sky-500/10 transition-all p-4 space-y-3 w-full shadow-lg shadow-emerald-500/10"
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/90 text-slate-950 font-semibold">
                                                        🏆 TOP MATCH
                                                    </span>
                                                    {typeof jobs[0].score === 'number' && (
                                                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-medium">
                                                            {(jobs[0].score * 100).toFixed(0)}%
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-[14px] font-semibold text-slate-100 line-clamp-2 leading-tight">{jobs[0].title}</div>
                                            </div>
                                        </div>
                                        <div className="text-[12px] text-slate-300 font-medium">
                                            {jobs[0].company} {jobs[0].location ? `· ${jobs[0].location}` : ''}
                                        </div>
                                        {jobs[0].tags && jobs[0].tags.length > 0 && (
                                            <div className="flex flex-wrap gap-1.5">
                                                {jobs[0].tags.slice(0, 6).map((t, i) => (
                                                    <span key={`tag-top-${i}`} className="text-[10px] px-2 py-1 rounded-md bg-slate-800/80 text-slate-200 font-medium">{t}</span>
                                                ))}
                                            </div>
                                        )}
                                    </button>
                                )}
                                {/* Other Matches Grid */}
                                {jobs.length > 1 && (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto pr-1 w-full">
                                        {jobs.slice(1).map((job, idx) => (
                                            <button
                                                key={`${job.title}-${job.company}-${idx + 1}`}
                                                onClick={() => { setSelectedJob(job); setJobModalOpen(true); setRefineResult(null); setCoverLetter(null); setJobModalTab("none"); }}
                                                className="text-left rounded-xl border border-slate-800 bg-slate-900/70 hover:bg-slate-900 transition-colors p-3 space-y-2 w-full"
                                            >
                                                <div className="flex items-center justify-between gap-2">
                                                    <div className="text-[12px] font-medium text-slate-100 line-clamp-2">{job.title}</div>
                                                    {typeof job.score === 'number' && (
                                                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300">
                                                            {(job.score * 100).toFixed(0)}%
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-[11px] text-slate-400">
                                                    {job.company} {job.location ? `· ${job.location}` : ''}
                                                </div>
                                                {job.explanation?.summary && (
                                                    <div className="text-[11px] text-slate-300 line-clamp-2">
                                                        {job.explanation.summary}
                                                    </div>
                                                )}
                                                {job.tags && job.tags.length > 0 && (
                                                    <div className="flex flex-wrap gap-1">
                                                        {job.tags.slice(0, 4).map((t, i) => (
                                                            <span key={`tag-${i}`} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">{t}</span>
                                                        ))}
                                                    </div>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Right column - secondary info */}
                    
                </div>
            </main>
            {/* Job Detail Modal */}
            {jobModalOpen && selectedJob && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/60" onClick={() => setJobModalOpen(false)} />
                    <div className="relative z-10 w-full max-w-3xl max-h-[90vh] rounded-2xl border border-slate-800 bg-slate-950 text-slate-100 shadow-xl flex flex-col">
                        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 flex-shrink-0">
                            <div>
                                <h4 className="text-sm font-semibold">{selectedJob.title}</h4>
                                <p className="text-[11px] text-slate-400">{selectedJob.company} {selectedJob.location ? `· ${selectedJob.location}` : ''} {selectedJob.source ? `· ${selectedJob.source}` : ''}</p>
                            </div>
                            <button
                                onClick={() => setJobModalOpen(false)}
                                className="text-slate-400 hover:text-slate-200 text-sm"
                                aria-label="Close"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="overflow-y-auto flex-1 px-5 py-4">
                            <div className="grid gap-4">
                            {typeof selectedJob.score === 'number' && (
                                <div className="text-[11px] text-emerald-300">Match score: {(selectedJob.score * 100).toFixed(0)}%</div>
                            )}
                            {selectedJob.explanation?.summary && (
                                <div className="text-[12px] text-slate-200">{selectedJob.explanation.summary}</div>
                            )}
                            {selectedJob.explanation?.gaps && selectedJob.explanation.gaps.length > 0 && (
                                <div>
                                    <p className="text-[11px] text-slate-400">Gaps compared to job:</p>
                                    <div className="flex flex-wrap gap-1">
                                        {selectedJob.explanation.gaps.slice(0,6).map((g, i) => (
                                            <span key={`gap-${i}`} className="text-[10px] px-1.5 py-0.5 rounded bg-rose-900/40 text-rose-200 border border-rose-900/60">{g}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {selectedJob.explanation?.fairness && (
                                <p className="text-[11px] text-slate-500">{selectedJob.explanation.fairness}</p>
                            )}
                            {selectedJob.tags && selectedJob.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                    {selectedJob.tags.slice(0, 8).map((t, i) => (
                                        <span key={`tag-${i}`} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">{t}</span>
                                    ))}
                                </div>
                            )}
                            {selectedJob.snippet && (
                                <div className="text-xs text-slate-300 leading-relaxed">
                                    {selectedJob.snippet
                                        .replace(/<[^>]+>/g, "")
                                        .trim()
                                        .split(/\n\n+/)
                                        .map((para, idx) => (
                                            <p key={`para-${idx}`} className="mb-3 last:mb-0">
                                                {para.replace(/\s+/g, " ").trim()}
                                            </p>
                                        ))}
                                </div>
                            )}
                            <div className="flex flex-wrap gap-2 pt-1">
                                {selectedJob.url && (
                                    <a
                                        href={selectedJob.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center justify-center rounded-md bg-sky-500/90 hover:bg-sky-400 text-slate-950 text-xs font-medium px-3 py-1.5"
                                    >
                                        Apply on site ↗
                                    </a>
                                )}
                                <button
                                    onClick={() => setJobModalTab("refine")}
                                    disabled={!resumeId}
                                    className={`inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${jobModalTab === "refine"
                                            ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                                            : "border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-slate-200"
                                        }`}
                                >
                                    Refine resume to job
                                </button>
                                <button
                                    onClick={() => setJobModalTab("cover")}
                                    disabled={!resumeId}
                                    className={`inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${jobModalTab === "cover"
                                            ? "border-sky-500 bg-sky-500/10 text-sky-300"
                                            : "border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-slate-200"
                                        }`}
                                >
                                    Generate cover letter
                                </button>
                            </div>
                            {jobModalTab === 'refine' && (
                                <div className="border border-slate-800 rounded-lg p-3 space-y-2">
                                    <p className="text-xs font-medium text-slate-200 flex items-center justify-between">
                                        <span>Tailoring suggestions</span>
                                        <button
                                            onClick={async () => {
                                                if (!resumeId || !selectedJob) return;
                                                setRefining(true); setRefineResult(null);
                                                try {
                                                    const res = await api.refineResumeForJob(resumeId, selectedJob as any);
                                                    setRefineResult(res);
                                                } finally {
                                                    setRefining(false);
                                                }
                                            }}
                                            disabled={refining}
                                            className="text-[11px] px-2 py-0.5 rounded border border-slate-700 bg-slate-900/80 hover:bg-slate-800 disabled:opacity-50"
                                        >
                                            {refining ? 'Refining…' : 'Run refine'}
                                        </button>
                                    </p>
                                    {refineResult ? (
                                        <>
                                            {refineResult.summary_suggestion && (
                                                <div className="text-xs text-slate-300"><span className="text-slate-400">Summary: </span>{refineResult.summary_suggestion}</div>
                                            )}
                                            {refineResult.keywords_to_emphasize && refineResult.keywords_to_emphasize.length > 0 && (
                                                <div>
                                                    <p className="text-[11px] text-slate-400">Keywords to emphasize:</p>
                                                    <div className="flex flex-wrap gap-1">
                                                        {refineResult.keywords_to_emphasize.map((k, i) => (
                                                            <span key={`kw-${i}`} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">{k}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                            {refineResult.experience_bullets && refineResult.experience_bullets.length > 0 && (
                                                <div>
                                                    <p className="text-[11px] text-slate-400">Experience bullets:</p>
                                                    <ul className="list-disc list-inside space-y-1 text-xs text-slate-300">
                                                        {refineResult.experience_bullets.map((b, i) => (
                                                            <li key={`b-${i}`}>{b}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            {refineResult.skills_to_add && refineResult.skills_to_add.length > 0 && (
                                                <div>
                                                    <p className="text-[11px] text-slate-400">Skills to add:</p>
                                                    <div className="flex flex-wrap gap-1">
                                                        {refineResult.skills_to_add.map((k, i) => (
                                                            <span key={`sa-${i}`} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">{k}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                            {refineResult.notes && (
                                                <div className="text-[11px] text-slate-400">{refineResult.notes}</div>
                                            )}
                                        </>
                                    ) : (
                                        <p className="text-[11px] text-slate-500">Click "Run refine" to generate tailored suggestions.</p>
                                    )}
                                </div>
                            )}

                            {jobModalTab === 'cover' && (
                                <div className="border border-slate-800 rounded-lg p-3 space-y-2">
                                    <p className="text-xs font-medium text-slate-200 flex items-center justify-between">
                                        <span>Cover letter</span>
                                        <button
                                            onClick={async () => {
                                                if (!resumeId || !selectedJob) return;
                                                setCovering(true); setCoverLetter(null);
                                                try {
                                                    const res = await api.generateCoverLetter(resumeId, selectedJob as any);
                                                    setCoverLetter(res.cover_letter || res.raw_response || '');
                                                } finally {
                                                    setCovering(false);
                                                }
                                            }}
                                            disabled={covering}
                                            className="text-[11px] px-2 py-0.5 rounded border border-slate-700 bg-slate-900/80 hover:bg-slate-800 disabled:opacity-50"
                                        >
                                            {covering ? 'Generating…' : 'Generate letter'}
                                        </button>
                                    </p>
                                    {coverLetter ? (
                                        <pre className="whitespace-pre-wrap text-xs text-slate-300">{coverLetter}</pre>
                                    ) : (
                                        <p className="text-[11px] text-slate-500">Click "Generate letter" to create a tailored cover letter.</p>
                                    )}
                                </div>
                            )}
                            </div>
                        </div>
                        <div className="px-5 py-3 border-t border-slate-800 flex justify-end flex-shrink-0">
                            <button
                                onClick={() => setJobModalOpen(false)}
                                className="rounded-md border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Review Modal */}
            {reviewOpen && reviewData && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div className="absolute inset-0 bg-black/60" onClick={() => setReviewOpen(false)} />
                    <div className="relative z-10 w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-950 text-slate-100 shadow-xl">
                        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
                            <h4 className="text-sm font-semibold">Resume Review</h4>
                            <button
                                onClick={() => setReviewOpen(false)}
                                className="text-slate-400 hover:text-slate-200 text-sm"
                                aria-label="Close"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="p-5 grid gap-5">
                            {/* Overall score */}
                            <div className="flex items-center gap-4">
                                <div className="h-16 w-16 rounded-full border-4 border-emerald-500/70 flex items-center justify-center">
                                    <span className="text-lg font-bold">{reviewData.overall?.score ?? "--"}</span>
                                </div>
                                <div className="text-sm">
                                    <p className="text-slate-300 font-medium">Overall Resume Score</p>
                                    <p className="text-slate-400">
                                        {reviewData.overall?.label || "—"} · out of {reviewData.overall?.out_of ?? 100}
                                    </p>
                                </div>
                            </div>

                            {/* Breakdown bars */}
                            <div>
                                <p className="text-xs text-slate-400 mb-2">Detailed Breakdown</p>
                                <div className="space-y-3 text-xs">
                                    {([
                                        ["Skills Coverage", reviewData.breakdown?.skills_coverage ?? 0],
                                        ["Structure & Formatting", reviewData.breakdown?.structure_formatting ?? 0],
                                        ["Clarity & Impact", reviewData.breakdown?.clarity_impact ?? 0],
                                        ["Regional Relevance", reviewData.breakdown?.regional_relevance ?? 0],
                                    ] as const).map(([label, val]) => (
                                        <div key={label}>
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-slate-300">{label}</span>
                                                <span className="text-slate-400">{val}/100</span>
                                            </div>
                                            <div className="h-2 rounded bg-slate-800 overflow-hidden">
                                                <div
                                                    className="h-full bg-emerald-500"
                                                    style={{ width: `${Math.max(0, Math.min(100, val))}%` }}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Strengths & Improvements */}
                            <div className="grid md:grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs font-medium text-emerald-300 mb-1">Strengths</p>
                                    <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                                        {(reviewData.strengths || []).slice(0, 6).map((s, i) => (
                                            <li key={`str-${i}`}>{s}</li>
                                        ))}
                                        {(!reviewData.strengths || reviewData.strengths.length === 0) && (
                                            <li className="text-slate-500">No strengths provided</li>
                                        )}
                                    </ul>
                                </div>
                                <div>
                                    <p className="text-xs font-medium text-rose-300 mb-1">Areas for improvement</p>
                                    <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                                        {(reviewData.areas_for_improvement || []).slice(0, 6).map((s, i) => (
                                            <li key={`imp-${i}`}>{s}</li>
                                        ))}
                                        {(!reviewData.areas_for_improvement || reviewData.areas_for_improvement.length === 0) && (
                                            <li className="text-slate-500">No suggestions provided</li>
                                        )}
                                    </ul>
                                </div>
                            </div>

                            {/* Notes */}
                            {reviewData.notes && (
                                <div className="text-xs text-slate-300">
                                    <p className="text-slate-400 mb-1">Notes</p>
                                    <p className="whitespace-pre-wrap leading-relaxed">{reviewData.notes}</p>
                                </div>
                            )}
                        </div>
                        <div className="px-5 py-3 border-t border-slate-800 flex justify-end">
                            <button
                                onClick={() => setReviewOpen(false)}
                                className="rounded-md border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Career Report Modal */}
            {reportOpen && reportData && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div className="absolute inset-0 bg-black/60" onClick={() => setReportOpen(false)} />
                    <div className="relative z-10 w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-950 text-slate-100 shadow-xl">
                        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
                            <h4 className="text-sm font-semibold">Career Report</h4>
                            <button
                                onClick={() => setReportOpen(false)}
                                className="text-slate-400 hover:text-slate-200 text-sm"
                                aria-label="Close"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="p-5 max-h-[80vh] overflow-y-auto">
                            <div className="grid gap-6 text-xs">
                                {/* Summary at top */}
                                {reportData.career_report?.summary && (
                                    <div className="rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900/90 to-slate-800/50 p-4">
                                        <p className="text-sm text-slate-100 leading-relaxed">
                                            {reportData.career_report.summary}
                                        </p>
                                    </div>
                                )}

                                {/* Six Month Focus - Featured Section */}
                                {reportData.career_report?.six_month_focus && (
                                    <div className="rounded-xl border border-sky-500/30 bg-sky-900/10 p-4">
                                        <div className="flex items-center gap-2 mb-3">
                                            <span className="text-lg">🎯</span>
                                            <h5 className="text-sm font-semibold text-sky-300">Next 6 Months Focus</h5>
                                        </div>
                                        {reportData.career_report.six_month_focus.headline && (
                                            <p className="text-base font-medium text-slate-100 mb-3">
                                                {reportData.career_report.six_month_focus.headline}
                                            </p>
                                        )}
                                        {reportData.career_report.six_month_focus.themes && reportData.career_report.six_month_focus.themes.length > 0 && (
                                            <div className="flex flex-wrap gap-2 mb-2">
                                                {reportData.career_report.six_month_focus.themes.map((theme: string, i: number) => (
                                                    <span key={i} className="px-2.5 py-1 rounded-full bg-sky-500/20 text-sky-200 text-xs font-medium border border-sky-500/30">
                                                        {theme}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                        {reportData.career_report.six_month_focus.target_roles && reportData.career_report.six_month_focus.target_roles.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-sky-500/20">
                                                <p className="text-xs text-slate-400 mb-2">Target Roles:</p>
                                                <div className="flex flex-wrap gap-2">
                                                    {reportData.career_report.six_month_focus.target_roles.map((role: string, i: number) => (
                                                        <span key={i} className="text-xs text-sky-100">• {role}</span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                            {/* Headline & narrative */}
                            {reportData.career_report?.narrative_summary && !reportData.career_report?.summary && (
                                <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                                    <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                                        {reportData.career_report.narrative_summary}
                                    </p>
                                </div>
                            )}

                            {/* Target roles */}
                            {reportData.career_report?.target_roles && reportData.career_report.target_roles.length > 0 && (
                                <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-lg">💼</span>
                                        <h5 className="text-sm font-semibold text-slate-200">Recommended Roles</h5>
                                    </div>
                                    <div className="space-y-3">
                                        {reportData.career_report.target_roles.slice(0, 5).map((r: any, idx: number) => (
                                            <div key={idx} className="flex items-start justify-between gap-3 pb-3 border-b border-slate-800 last:border-0 last:pb-0">
                                                <div className="flex-1">
                                                    <p className="text-sm font-medium text-slate-100 mb-1">{r.role}</p>
                                                    {r.why && (
                                                        <p className="text-xs text-slate-400 leading-relaxed">{r.why}</p>
                                                    )}
                                                </div>
                                                {typeof r.fit_score === "number" && (
                                                    <div className="flex flex-col items-end">
                                                        <span className="text-lg font-bold text-emerald-400">{Math.round(r.fit_score * 100)}%</span>
                                                        <span className="text-[10px] text-slate-500">fit</span>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Skills Section - Two columns */}
                            {((reportData.career_report?.skills_to_double_down && reportData.career_report.skills_to_double_down.length > 0) ||
                              (reportData.career_report?.skills_to_learn && reportData.career_report.skills_to_learn.length > 0)) && (
                                <div className="grid md:grid-cols-2 gap-4">
                                    {reportData.career_report?.skills_to_double_down && reportData.career_report.skills_to_double_down.length > 0 && (
                                        <div className="rounded-xl border border-emerald-500/30 bg-emerald-900/10 p-4">
                                            <div className="flex items-center gap-2 mb-3">
                                                <span className="text-lg">💪</span>
                                                <h5 className="text-sm font-semibold text-emerald-300">Double Down On</h5>
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                {reportData.career_report.skills_to_double_down.map((s: string, i: number) => (
                                                    <span key={i} className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-200 text-xs font-medium border border-emerald-500/40">
                                                        {s}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {reportData.career_report?.skills_to_learn && reportData.career_report.skills_to_learn.length > 0 && (
                                        <div className="rounded-xl border border-sky-500/30 bg-sky-900/10 p-4">
                                            <div className="flex items-center gap-2 mb-3">
                                                <span className="text-lg">📚</span>
                                                <h5 className="text-sm font-semibold text-sky-300">Learn Next</h5>
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                {reportData.career_report.skills_to_learn.map((s: string, i: number) => (
                                                    <span key={i} className="px-3 py-1.5 rounded-lg bg-sky-500/20 text-sky-200 text-xs font-medium border border-sky-500/40">
                                                        {s}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Certifications */}
                            {reportData.career_report?.certifications && reportData.career_report.certifications.length > 0 && (
                                <div className="rounded-xl border border-amber-500/30 bg-amber-900/10 p-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-lg">🏆</span>
                                        <h5 className="text-sm font-semibold text-amber-300">Suggested Certifications</h5>
                                    </div>
                                    <ul className="grid md:grid-cols-2 gap-2">
                                        {reportData.career_report.certifications.slice(0, 6).map((c: string, i: number) => (
                                            <li key={i} className="flex items-start gap-2 text-slate-300">
                                                <span className="text-amber-400 mt-0.5">✓</span>
                                                <span className="text-xs">{c}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Month-by-month learning plan */}
                            {reportData.career_report?.learning_plan && reportData.career_report.learning_plan.length > 0 && (
                                <div className="rounded-xl border border-violet-500/30 bg-violet-900/10 p-4">
                                    <div className="flex items-center gap-2 mb-4">
                                        <span className="text-lg">📅</span>
                                        <h5 className="text-sm font-semibold text-violet-300">6-Month Learning Plan</h5>
                                    </div>
                                    <div className="grid gap-3">
                                        {reportData.career_report.learning_plan.slice(0, 6).map((m: any, idx: number) => (
                                            <div key={idx} className="rounded-lg border border-violet-500/20 bg-slate-900/50 p-3">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-violet-500/20 text-violet-300 text-xs font-bold">
                                                        {m.month}
                                                    </span>
                                                    <p className="text-sm text-violet-200 font-medium">{m.focus}</p>
                                                </div>
                                                {m.actions && m.actions.length > 0 && (
                                                    <ul className="ml-8 space-y-1">
                                                        {m.actions.slice(0, 4).map((a: string, i: number) => (
                                                            <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                                                                <span className="text-violet-400 mt-0.5">→</span>
                                                                <span>{a}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Market insights */}
                            {reportData.career_report?.market_insights && (
                                <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-lg">🌍</span>
                                        <h5 className="text-sm font-semibold text-slate-200">Market Insights</h5>
                                    </div>
                                    <div className="space-y-3 text-xs">
                                        {reportData.career_report.market_insights.target_regions && reportData.career_report.market_insights.target_regions.length > 0 && (
                                            <div>
                                                <span className="text-slate-400 font-medium">Target Regions: </span>
                                                <span className="text-slate-200">
                                                    {reportData.career_report.market_insights.target_regions.join(", ")}
                                                </span>
                                            </div>
                                        )}
                                        {reportData.career_report.market_insights.hot_skills && reportData.career_report.market_insights.hot_skills.length > 0 && (
                                            <div>
                                                <span className="text-slate-400 font-medium">Hot Skills: </span>
                                                <div className="flex flex-wrap gap-1.5 mt-1.5">
                                                    {reportData.career_report.market_insights.hot_skills.map((skill: string, i: number) => (
                                                        <span key={i} className="px-2 py-0.5 rounded bg-orange-500/10 text-orange-300 text-xs border border-orange-500/30">
                                                            {skill}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                        {reportData.career_report.market_insights.notes && (
                                            <p className="text-slate-300 leading-relaxed pt-2 border-t border-slate-800">
                                                {reportData.career_report.market_insights.notes}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Interview tips */}
                            {reportData.career_report?.interview_tips && reportData.career_report.interview_tips.length > 0 && (
                                <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-lg">💡</span>
                                        <h5 className="text-sm font-semibold text-slate-200">Interview Tips</h5>
                                    </div>
                                    <ul className="space-y-2">
                                        {reportData.career_report.interview_tips.slice(0, 6).map((t: string, i: number) => (
                                            <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                                                <span className="text-sky-400 mt-0.5">💬</span>
                                                <span>{t}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Fallback: No data */}
                            {!reportData.career_report && (
                                <div className="rounded-xl border border-amber-500/30 bg-amber-900/10 p-4 text-center">
                                    <span className="text-3xl mb-2 block">⚠️</span>
                                    <p className="text-sm text-amber-200 mb-2">
                                        Career report data is being generated...
                                    </p>
                                    <p className="text-xs text-slate-400">
                                        Please try again in a moment.
                                    </p>
                                </div>
                            )}
                            </div>
                        </div>
                        <div className="px-5 py-3 border-t border-slate-800 flex justify-end">
                            <button
                                onClick={() => setReportOpen(false)}
                                className="rounded-md border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
