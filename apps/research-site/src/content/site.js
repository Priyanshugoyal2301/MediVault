/**
 * MediVault Research — production site content.
 * Source of truth for narrative: project BIBLE, Plan B/C reports, PROJECT_STATE.
 * Claims stay conservative (see docs/PRESENTATION_CLAIMS.md).
 */

export const site = {
  brand: "MediVault",
  institution: "MediVault Research",
  tagline: "Longitudinal medical intelligence — without diagnosis",
  domain: "https://medivault.research",
  version: "1.0.0",
  build: "2026.08.10",
  email: "research@medivault.dev",
  github: "https://github.com/Priyanshugoyal2301/MediVault",
  linkedin: "https://github.com/Priyanshugoyal2301/MediVault",
  location: "Research initiative · India-focused lab literacy (en-IN / hi-IN)",
  lastReview: "10 August 2026",
};

/** Core narrative blocks used across pages */
export const narrative = {
  abstract:
    "MediVault is a research prototype that converts scattered medical lab reports into an owner-scoped health vault. It combines three capabilities usually shipped in isolation: longitudinal memory of structured results, personal-series trend and anomaly monitoring on short outpatient timelines, and evidence-cited question answering over a curated guideline corpus plus the user’s own values. Every explanation path is non-diagnostic by design—template-bound language, deterministic emergency safety before retrieval, and structural privacy at the repository layer. Evaluation is published under explicit synthetic protocols (anomaly F1 ≈ 0.87 on spike series; BM25+intent Hit@5 = 1.0 on a 50-question FAQ set; IE field F1 ≈ 0.97 on layout fixtures), with clear limits: these numbers are research measurements, not clinical validation.",

  problem:
    "Healthcare interaction is still binary for many people: “I feel fine” or “I need a clinician.” Between those states, patients are left to interpret multi-page lab PDFs, notice patterns across years of tests, and judge free-form answers from search or chatbots that neither remember their history nor cite sources. Existing products typically solve one slice well—OCR parsers, generic health chat, or single-point flagging against population reference ranges—but rarely combine durable personal memory, within-person trend reasoning, and cited retrieval under a hard non-diagnostic and safety constraint.",

  mission:
    "To give individuals an understandable, evidence-grounded record of their own laboratory history—structured, bilingual, privacy-scoped, and explicit about uncertainty—without substituting for clinical judgment.",

  vision:
    "A durable personal health-intelligence layer that any future biometric login, health-ID verification, or conversational interface can attach to, because the core—owner-scoped memory, explainable monitoring, and citable knowledge—was designed as infrastructure, not a disposable chatbot demo.",

  philosophy:
    "Safety before generation. Citations before fluency. Owner identity from authenticated gateways, never from client-supplied identifiers. Prefer simple, auditable methods that fit short personal series and a tiny curated knowledge base over black-box models that force diagnoses or inflate claims. Publish ablations and rejected approaches with the same discipline as promoted metrics.",

  contribution:
    "A unified system architecture and open evaluation of three coupled methods: (1) classical OCR plus multi-alias regex information extraction for CBC, lipid, thyroid, and HbA1c panels; (2) a causal statistical personal-series monitor—leave-last-out z-score, relative change for narration, and two-sided CUSUM—replacing IsolationForest on n≈3–10 series; (3) BM25 with panel intent boosting and a template synthesizer for cited answers, with optional warm MiniLM hybrid retrieval under strict demo-risk gates. Structural multi-tenant privacy (ScopedRepository + owner_id FKs) and a rule-based red-flag safety layer complete the research platform.",

  limitations:
    "Anomaly and retrieval results are primarily synthetic or small labeled sets; they are not a substitute for multi-site clinical trials. OCR quality on diverse Indian printouts and handwriting is not rigorously measured. Live Q&A loads an in-memory knowledge base rather than production pgvector retrieval. The stack is a hackathon-grade prototype: no encryption-at-rest by default, no durable OCR job queue, no formal access audit log, and no HIPAA/clinical-device certification. Hindi support uses template and phrase assistance, not full neural machine translation.",

  future:
    "Near-term: durable parse queues, encrypt-at-rest and TLS, integration tests, and optional warm dense retrieval. Medium-term: licensed India lab image corpora for OCR/IE evaluation, access auditing, and S3-backed storage. Longer horizon: pluggable identity (device, ABHA-class IDs), family profiles only after privacy redesign, and clinical co-evaluation partners—without relaxing the non-diagnostic product boundary.",
};

export const hero = {
  brand: "MediVault Research",
  headline: "Medical intelligence that remembers — and refuses to guess.",
  support:
    "We turn lab PDFs into an owner-scoped vault with plain-language explanations, personal trend scoring, and citation-backed Q&A—engineered never to issue a diagnosis.",
  primaryCta: { label: "Explore the research", href: "/research" },
  secondaryCta: { label: "View architecture", href: "/architecture" },
};

export const problemStats = [
  {
    value: "3",
    label: "Capabilities, one system",
    note: "Memory · personal trends · cited answers—usually productized separately",
  },
  {
    value: "0",
    label: "Diagnostic claims allowed",
    note: "Templates, tone scrub, and safety rules forbid “you have X” outputs",
  },
  {
    value: "5",
    label: "Emergency red-flag families",
    note: "Cardiac, bleeding, vision loss, stroke patterns, crisis ideation—before any RAG",
  },
];

export const pillars = [
  {
    title: "Longitudinal memory",
    body: "Each report lands in an owner-scoped store: structured values, bilingual explanations, and timeline events keyed by metric and date—so questions and trends reason over the person’s history, not a single upload.",
  },
  {
    title: "Personal-series monitoring",
    body: "On short outpatient series we score leave-last-out causal z-score, optional CUSUM shift detection, and relative change for language—not population ML models that invent outliers on five points.",
  },
  {
    title: "Evidence-cited retrieval",
    body: "Questions hit a deterministic safety layer, then BM25 with lab-panel intent boost over curated guideline chunks, merged with keyword-matched personal values, and assembled by a template synthesizer with visible sources.",
  },
];

export const pipelineSteps = [
  {
    id: "01",
    title: "Ingest",
    detail:
      "Multipart upload with magic-byte MIME sniffing (PDF/JPEG/PNG/TIFF/WebP), 20 MB cap, and storage under an owner-scoped path. Demo seed endpoints populate CBC/lipid panels without OCR for reliable evaluation.",
  },
  {
    id: "02",
    title: "Perceive",
    detail:
      "pdfplumber/Tesseract OCR locally (no cloud OCR by default). Multi-alias regex extracts CBC, lipid, thyroid, and HbA1c fields with value, unit, and reference bounds where present.",
  },
  {
    id: "03",
    title: "Explain",
    detail:
      "Status (low / normal / high / unknown) from report reference intervals. Bilingual English–Hindi templates use educational framing—“commonly associated,” “discuss with a clinician”—never definitive diagnoses.",
  },
  {
    id: "04",
    title: "Monitor",
    detail:
      "Timeline aggregates dated points per metric. Anomaly analysis reports trend (rising/falling/stable), causal statistical score in [−1, +1], binary alert, and bilingual summary; reference-range notes stay soft-copy only.",
  },
  {
    id: "05",
    title: "Retrieve",
    detail:
      "Safety regex first. Then BM25 + intent (default) or optional MiniLM hybrid; user values injected by health service. Template answer with citations; emergency messages override entirely on red-flags.",
  },
];

export const techStack = [
  { layer: "Interface", items: "React research portal · product BFF SPA (Vite) for demos" },
  { layer: "Gateway", items: "FastAPI BFF — JWT verify, strip client X-User-ID, proxy auth/health" },
  { layer: "Services", items: "Auth · health (reports, timeline, Q&A proxy) · internal AI" },
  { layer: "Intelligence", items: "OCR · regex IE · statistical monitor · BM25 RAG · red-flag safety" },
  { layer: "Data", items: "PostgreSQL 16 · Alembic · owner_id FKs · pgvector-ready schema" },
  { layer: "Ops", items: "Docker Compose (localhost-bound internal ports) · Ruff · Pytest" },
];

export const benchmarks = [
  {
    name: "Statistical anomaly monitor",
    metric: "F1",
    value: "0.87",
    baseline: "IF 0.84",
    note: "Plan B: n=200 synthetic Hb patients, 20% last-point spikes, seed 42. FAR 0.075. Not clinical performance.",
  },
  {
    name: "BM25 + intent retrieval",
    metric: "Hit@5",
    value: "1.00",
    baseline: "MRR 0.95",
    note: "50 labeled FAQ pairs over ≈13 curated KB chunks. Default live path; not MiniLM unless dense bake-off.",
  },
  {
    name: "Information extraction",
    metric: "Field F1",
    value: "0.97",
    baseline: "P 0.94 / R 1.0",
    note: "Plan C: 8 synthetic India-style layout fixtures, 29 gold fields. Not scanned-print CER.",
  },
  {
    name: "Tone compliance",
    metric: "Violations",
    value: "0%",
    baseline: "was 72%",
    note: "Substring heuristic for diagnostic phrasing after synthesizer scrub + KB wording fixes (Plan C).",
  },
];

export const anomalyAblation = [
  { method: "statistical_monitor (prod)", precision: 0.769, recall: 1.0, f1: 0.87, far: 0.075 },
  { method: "causal_z_only", precision: 0.769, recall: 1.0, f1: 0.87, far: 0.075 },
  { method: "pct_delta_only", precision: 0.8, recall: 0.7, f1: 0.747, far: 0.044 },
  { method: "cusum_only", precision: 1.0, recall: 0.575, f1: 0.73, far: 0.0 },
  { method: "isolation_forest (legacy)", precision: 0.736, recall: 0.975, f1: 0.839, far: 0.088 },
];

export const timeline = [
  {
    date: "2026 · Scope freeze",
    title: "Product and research framing locked",
    body: "USP fixed as memory + personal trends + cited retrieval. Out of scope: diagnosis chatbots, family multi-profile, prescription OCR, wearables.",
  },
  {
    date: "2026-08 · MVP stack",
    title: "Services, schema, and BFF identity",
    body: "Auth (JWT/bcrypt), health reports and timeline, AI parse path, Alembic migrations through explanation columns, gateway that injects trusted owner identity.",
  },
  {
    date: "2026-08 · Plan B",
    title: "Defensible ML path",
    body: "Removed IsolationForest and MD5 “embedding” theater. Shipped causal statistical monitor + pure-Python BM25 with intent. Documented ablations and retracted prior metric misclaims.",
  },
  {
    date: "2026-08 · Plan C",
    title: "Lab gates, no vanity training",
    body: "IE alias hardening and tone scrub promoted. Dense MiniLM optional with cold-start veto for demos. Ref-range OR into anomaly rejected (FAR regression). Zero newly trained weights.",
  },
  {
    date: "Next",
    title: "Hardening and real corpora",
    body: "Encrypt-at-rest, durable parse workers, integration tests, and licensed India lab images for OCR/IE measurement—while keeping non-diagnostic constraints.",
  },
];

export const features = [
  {
    title: "Report intelligence",
    body: "Upload PDF or images of common lab panels; extract structured fields; generate bilingual plain-language notes from report reference ranges.",
  },
  {
    title: "Owner-scoped timeline",
    body: "Every query path requires owner_id. Repository base classes and database FKs prevent casual cross-user reads even if a handler forgets.",
  },
  {
    title: "Personal anomaly stories",
    body: "EN/HI summaries describe rising, falling, or unusual personal patterns and invite clinician discussion—without alarmist or diagnostic language.",
  },
  {
    title: "Safety-first Q&A",
    body: "Five red-flag categories with fixed emergency guidance in English and Hindi run before retrieval or synthesis, targeting sub-100 ms rule evaluation.",
  },
  {
    title: "Citation discipline",
    body: "Answers list sources and pull user values as first-class evidence when the question maps to metrics on file.",
  },
  {
    title: "Transparent methods",
    body: "Thresholds, ablations, Guardian gates, and rejected models are documented in-repo for peer and faculty review.",
  },
];

export const publications = [
  {
    type: "Technical report",
    title: "Plan B ML — Benchmark & Validation Report",
    authors: "MediVault Research",
    year: "2026",
    venue: "Project literature (ML_PLAN_B_RESULTS)",
    cite: "MediVault Research. Plan B ML — Benchmark & Validation Report. Internal technical report, 10 August 2026. Anomaly F1 and BM25 Hit@5/MRR under disclosed synthetic protocols.",
    href: "https://github.com/Priyanshugoyal2301/MediVault/blob/main/docs/ML_PLAN_B_RESULTS.md",
  },
  {
    type: "Technical report",
    title: "Project Phoenix — Plan C Report",
    authors: "MediVault Research",
    year: "2026",
    venue: "Project literature (PLAN_C_REPORT)",
    cite: "MediVault Research. Project Phoenix — Plan C Report. Internal technical report, 10 August 2026. IE/tone promotions, dense bake-off, training rejection under metric ∧ data ∧ demo-risk gates.",
    href: "https://github.com/Priyanshugoyal2301/MediVault/blob/main/docs/PLAN_C_REPORT.md",
  },
  {
    type: "System encyclopedia",
    title: "MediVault BIBLE — Institutional Technical Memory",
    authors: "MediVault Research",
    year: "2026",
    venue: "Repository root",
    cite: "MediVault Research. BIBLE.md: Definitive project knowledge base. Repository document, August 2026.",
    href: "https://github.com/Priyanshugoyal2301/MediVault/blob/main/BIBLE.md",
  },
  {
    type: "Architecture guide",
    title: "Architecture & Project Structure",
    authors: "MediVault Research",
    year: "2026",
    venue: "docs/02_ARCHITECTURE.md",
    cite: "MediVault Research. Architecture & Project Structure. Engineering design document, 2026.",
    href: "https://github.com/Priyanshugoyal2301/MediVault/blob/main/docs/02_ARCHITECTURE.md",
  },
];

export const team = [
  {
    name: "Priyanshu Goyal",
    role: "Project lead & systems research",
    bio: "Steers MediVault architecture, privacy boundaries, and research–engineering integration across auth, health, and AI services.",
  },
  {
    name: "MediVault Research",
    role: "Intelligence & evaluation",
    bio: "Designs non-diagnostic pipelines: statistical personal-series monitoring, BM25 retrieval, template synthesis, and published evaluation harnesses.",
  },
  {
    name: "Open contributors",
    role: "Platform & documentation",
    bio: "Tests, migrations, demo reliability, and documentation that keep the system auditable.",
  },
];

export const faq = [
  {
    q: "Does MediVault diagnose medical conditions?",
    a: "No. The system is explicitly non-diagnostic. Explanations and Q&A use educational framing and always defer clinical decisions to qualified professionals. Product and research materials forbid “you have [condition]” language.",
  },
  {
    q: "How is privacy enforced?",
    a: "Browser traffic goes through a BFF that validates JWTs and injects a trusted X-User-ID after stripping any client-supplied identity header. Health repositories subclass ScopedRepository so queries require owner_id. Database foreign keys cascade on delete. Logs use a redacting shared logger. Encryption-at-rest and TLS termination are not yet production defaults—disclose that honestly.",
  },
  {
    q: "Is this production-ready for PHI?",
    a: "No. MediVault is a research and demonstration prototype. It lacks formal encrypt-at-rest, durable job queues, complete access audit logs, and healthcare compliance certifications. Do not treat demos as clinical systems of record.",
  },
  {
    q: "What ML models are used?",
    a: "Live defaults: classical OCR, regex information extraction, a stdlib statistical monitor (causal z and CUSUM), pure-Python BM25 with intent boosting, and template answer synthesis. Optional all-MiniLM-L6-v2 hybrid retrieval exists behind flags. There is no free-form diagnostic LLM and no IsolationForest on the promoted anomaly path.",
  },
  {
    q: "How should benchmarks be interpreted?",
    a: "As research measurements under disclosed protocols—synthetic spike patients, layout fixtures, and a 50-question FAQ set. They support method comparison and ablation claims. They are not clinical sensitivity/specificity for patient care.",
  },
  {
    q: "Can institutions collaborate?",
    a: "Yes. Reach the research inbox for evaluation partnerships, corpus licensing discussions, or co-supervision of measurement studies. We prioritize partners who accept non-diagnostic product boundaries and open reporting of limits.",
  },
  {
    q: "What languages are supported?",
    a: "MVP surfaces target English (en-IN) and Hindi (hi-IN). Hindi explanations combine templates and phrase maps; they are not a full neural translation product.",
  },
  {
    q: "How do emergency red-flags work?",
    a: "Rule-based regex categories—including combined cardiac symptoms, gastrointestinal bleeding, sudden vision loss, stroke patterns, and crisis ideation—run before retrieval. On match, fixed emergency guidance (with regional helpline numbers where applicable) returns with no model involvement.",
  },
  {
    q: "Where is the source code?",
    a: "The monorepo is public at github.com/Priyanshugoyal2301/MediVault, including BIBLE.md, evaluation reports, services, and tests.",
  },
];

export const gallery = [
  {
    title: "Gateway architecture",
    category: "Systems",
    note: "Browser → BFF JWT → auth/health; AI remains internal with path allowlists.",
  },
  {
    title: "Intelligence pipeline",
    category: "Workflow",
    note: "Ingest · perceive · explain · monitor · retrieve, with safety before synthesis.",
  },
  {
    title: "Anomaly monitor",
    category: "Methods",
    note: "Leave-last-out z and CUSUM on short personal lab series; binary rule excludes %Δ for FAR control.",
  },
  {
    title: "Retrieval topology",
    category: "Methods",
    note: "BM25 + intent over curated chunks; optional dense hybrid when warm and flagged.",
  },
  {
    title: "Product surfaces",
    category: "Product",
    note: "Dashboard, upload/demo seed, timeline analysis, and citation Q&A in the demo SPA.",
  },
  {
    title: "Lab literacy focus",
    category: "Domain",
    note: "CBC, lipids, thyroid, and HbA1c panels dominant in MVP scope.",
  },
];

export const blogPosts = [
  {
    slug: "why-statistical-monitors-beat-isolation-forest",
    title: "Why short personal series prefer causal statistics over IsolationForest",
    date: "2026-08-10",
    excerpt:
      "On n≈5–10 one-dimensional outpatient points, contamination-driven isolation methods invent outliers. Leave-last-out z and CUSUM are auditable and fit the data regime.",
    body: `Short personal laboratory series are nothing like industrial IoT streams. Patients often have three to ten comparable values across years—not thousands of sensors. IsolationForest, with a fixed contamination rate, will nearly always flag points because the algorithm assumes anomalies exist in the sample.

MediVault’s Plan B replaced that path with a **leave-last-out** baseline: mean and standard deviation from past points only, causal z for the newest reading, relative change for continuous scoring and language, and two-sided CUSUM for gradual drift. Production binary alerts use causal |z| ≥ 2 or CUSUM alarm—not %Δ—because OR-ing relative change raised false-alert rate in ablation.

On a 200-patient synthetic haemoglobin spike set (seed 42), the statistical monitor reached F1 ≈ 0.87 with FAR 0.075, edging out the legacy IsolationForest baseline while removing a live sklearn dependency. That is a scientific claim under a disclosed protocol—not a clinical proof.`,
  },
  {
    slug: "evaluation-honesty",
    title: "Evaluation honesty: retracting MD5-as-MiniLM",
    date: "2026-08-10",
    excerpt:
      "We corrected an earlier Precision@5 claim that measured keyword Hit@5 on mock embeddings. Defaults now report BM25 Hit@5 and MRR under the true retriever.",
    body: `Credibility in applied ML requires publishing failures of measurement, not only model upgrades.

An earlier write-up suggested MiniLM Precision@5 near 82%. The harness had used MD5-derived mock vectors and a keyword Hit@5 definition. That is not classical Precision@5 on a sentence transformer, and we retracted the claim in the development log.

Plan B evaluation now scores the **actual default retriever**—BM25 with intent—on 50 labeled FAQ questions over the curated knowledge base. Hit@5 saturates; MRR ≈ 0.95. Dense hybrid with MiniLM can improve MRR slightly when warm, but cold Hugging Face downloads are vetoed for live demos. The lesson is procedural: metric names must match methods, and demo reliability is part of the research gate.`,
  },
];

export const news = [
  {
    date: "2026-08-10",
    title: "Plan C lab closes with IE and tone promotions—no vanity training",
    body: "Guardian gates blocked ref-range anomaly ORs and cold dense deployment despite partial metric wins. Research literature and repository methods updated the same day.",
  },
  {
    date: "2026-08-10",
    title: "Institutional technical encyclopedia published",
    body: "BIBLE.md consolidates architecture, APIs, ML math, benchmarks, and operator guidance as the durable project knowledge base.",
  },
  {
    date: "2026-08",
    title: "JWT BFF hardens multi-service demo",
    body: "Browser clients no longer supply owner identity. Health and AI services bind to localhost in compose; AI is not exposed via the public gateway.",
  },
];

export const techDepth = {
  intro:
    "MediVault’s intelligence stack is deliberately classical where data is thin and constraints are strict. We reserve neural models for optional retrieval, not for emergency decisions or free-form diagnoses.",
  ocr:
    "Local pdfplumber text extraction for typed PDFs and Tesseract for images. Healthcare data does not leave the host for cloud OCR in the default configuration.",
  ie:
    "Panel patterns cover haemoglobin and differentials, lipids, thyroid panel members, and HbA1c/eAG with Indian alias variants and mixed separators. First match wins per canonical field.",
  anomaly:
    "Trend via whole-series normalized slope and latest series z-score for streaks. Scoring via leave-last-out μ,σ, causal z, %Δ, CUSUM k=0.5σ h=4σ. Score s ∈ [−1,+1] strengthens by max of normalized signal magnitudes.",
  rag:
    "Startup loads knowledge-base .txt files, chunks ≈300 words with overlap, builds BM25 (k1=1.5, b=0.75). Intent boosts for CBC/lipid/thyroid/HbA1c capped at 0.35. Template synthesizer inserts citations and scrubbed wording.",
  safety:
    "Five categories with bilingual fixed strings. Architecture rule: safety runs first on every /qa request and short-circuits synthesis.",
};

export const methodology = {
  workflow:
    "Hypotheses are written against failed baselines (IsolationForest; mock dense embeddings). Synthetic generators and fixtures create controlled labels. Ablations compare components. Guardian policy promotes only methods that improve metrics without worsening FAR or demo reliability. Results land in plan reports and unit tests.",
  validation:
    "Anomaly: 200 synthetic patients, 20% spiked last readings for Plan B spike protocol; Plan C adds mixed regimes for honesty about gradual drift. IE: eight hand-authored India-style layouts with gold fields. Retrieval: fifty FAQ questions with relevant chunk labels. Tone: substring audit for diagnostic phrasing across FAQ answers.",
  metrics:
    "Anomaly precision/recall/F1/FAR; IE field precision/recall/F1; retrieval Hit@5 and MRR; tone violation rate; citation presence. No claim of clinical AUC unless a labeled clinical study exists—which it does not yet.",
};

export const datasets = {
  overview:
    "Evaluation assets live under data/datasets and data/knowledge-base. Runtime health data is user-owned PostgreSQL content plus local uploaded files—not public PHI dumps.",
  sources:
    "Curated educational guideline texts (CBC, lipid, thyroid, HbA1c, general health) with SOURCE/URL/LICENCE headers. Synthetic anomaly generators and Plan C IE fixtures are project-owned. External sets (Eka Care, NidaanKosha, MIMIC-class corpora) were ranked but gated or rejected for hackathon timelines and license friction.",
  pipeline:
    "KB: load → section-aware chunk → optional MiniLM embed → BM25 index in memory at AI startup. Reports: upload → MIME → store → background parse → report_values + timeline_events. Q&A: load latest owner values → safety → retrieve → synthesize.",
  quality:
    "Synthetic spikes favour last-point detectors; mixed-regime results show lower recall on gradual drift. IE fixtures stress separators and aliases, not scan noise. FAQ labels fit a deliberately small corpus where BM25 is appropriate and dense models add limited, costly gain.",
};

export const downloads = [
  {
    label: "Plan B results (Markdown)",
    meta: "docs/ML_PLAN_B_RESULTS.md · evaluation tables",
    href: "https://github.com/Priyanshugoyal2301/MediVault/blob/main/docs/ML_PLAN_B_RESULTS.md",
  },
  {
    label: "Plan C report (Markdown)",
    meta: "docs/PLAN_C_REPORT.md · lab decisions",
    href: "https://github.com/Priyanshugoyal2301/MediVault/blob/main/docs/PLAN_C_REPORT.md",
  },
  {
    label: "Project BIBLE (Markdown)",
    meta: "BIBLE.md · full technical encyclopedia",
    href: "https://github.com/Priyanshugoyal2301/MediVault/blob/main/BIBLE.md",
  },
  {
    label: "Judge claims sheet",
    meta: "docs/PRESENTATION_CLAIMS.md · conservative talking points",
    href: "https://github.com/Priyanshugoyal2301/MediVault/blob/main/docs/PRESENTATION_CLAIMS.md",
  },
  {
    label: "Source repository",
    meta: "Full monorepo · services, tests, migrations",
    href: "https://github.com/Priyanshugoyal2301/MediVault",
  },
];

export const partners = {
  intro:
    "MediVault Research collaborates informally with the open scientific and open-source stack that makes the platform possible. Formal institutional partnerships for clinical evaluation are invited—not pre-claimed.",
  list: [
    { name: "Open-source core", blurb: "FastAPI, PostgreSQL/pgvector, React, scikit-learn (historical), sentence-transformers (optional)." },
    { name: "Public medical literacy sources", blurb: "Guideline-oriented knowledge files for educational Q&A—not a substitute for clinician guidance." },
    { name: "Evaluation community", blurb: "Hackathon and academic reviewers using the published demo and claims discipline." },
  ],
};

export const press = {
  boilerplate:
    "MediVault Research builds non-diagnostic software that helps people understand their own laboratory history. Combining owner-scoped memory, statistical personal-series monitoring, and citation-backed answers, the project publishes methods and limits alongside demos—so progress is measurable and claims stay honest.",
  facts: [
    "Microservices architecture with JWT BFF and internal AI service",
    "Default retrieval: BM25 + intent; default anomaly: causal statistical monitor",
    "Bilingual educational explanations (English / Hindi) for major lab panels",
    "Deterministic emergency safety layer before RAG",
    "Public evaluation reports for Plan B and Plan C (August 2026)",
    "Not a medical device; not HIPAA-certified as shipped",
  ],
};

export const legal = {
  privacy: `Last reviewed: ${site.lastReview}

MediVault Research prototypes process authentication data (email, hashed password, locale preference) and voluntarily uploaded laboratory documents and derived structured fields. Health rows are partitioned by owner_id and accessed only through authenticated gateways in the intended deployment topology.

What we collect in a typical local or demo deployment: account email, password hashes (bcrypt), uploaded files and metadata, extracted lab values, timeline events, and optional Q&A session payloads if persisted. We do not sell personal data.

Ownership and deletion: report deletion removes the file and cascades related rows. Database cascades also remove owned health data when a user row is hard-deleted. Soft-delete fields exist on accounts; operators must follow documented procedures.

Security posture: JWT sessions, optional service keys for internal AI, redacting logs, magic-byte upload checks. Encryption-at-rest, formal consent management, and comprehensive access audit trails are incomplete relative to production healthcare systems.

Contact: ${site.email} for data questions. This prototype is for research demonstration; do not process regulated PHI in production deployments without independent security review.`,

  terms: `Last reviewed: ${site.lastReview}

By using MediVault Research software or websites, you agree that the system is provided for research, education, and demonstration. It is not a medical device, not a diagnostic service, and not a substitute for professional medical advice, diagnosis, or treatment.

You may not rely on outputs for emergency decisions. If you believe you are experiencing a medical emergency, contact local emergency services immediately.

Software is provided “as is” without warranty of merchantability or fitness for a particular purpose, to the extent permitted by law. Repository licensing is defined in the monorepo LICENSE (and dependency licenses). Contributions must respect non-diagnostic and privacy rules stated in project agent and architecture documents.

Contact: ${site.email}.`,

  accessibility: `Last reviewed: ${site.lastReview}

MediVault Research aims for clear structure, keyboard-reachable controls, visible focus states, semantic landmarks, and reduced-motion compatibility for animated canvases and page transitions. Contrast targets clinical light and dark themes with lagoon-ink primaries.

Known gaps: a full formal WCAG 2.2 AA audit has not been completed; Hindi content is limited; some data tables require horizontal scroll on small screens; interactive charts are decorative supplements to tabular data.

Accommodations and defects: email ${site.email} with “Accessibility” in the subject. We treat accessibility reports as first-class engineering work items.`,

  acknowledgements: `We thank open-source maintainers of FastAPI, SQLAlchemy, PostgreSQL, React, Vite, Framer Motion, Tesseract, pdfplumber, and related libraries; authors of educational medical references used in the knowledge base; and peer reviewers who insisted on metric honesty (including retracting MD5-as-MiniLM claims).

Plan B and Plan C evaluation work was conducted under an explicit Guardian policy: no training promotion without simultaneous metric, data, and demo-risk clearance.`,

  licenses: `Application code follows the monorepo license at github.com/Priyanshugoyal2301/MediVault. Third-party packages retain their upstream licenses (MIT, Apache-2.0, BSD-family, and others as declared in dependency manifests).

Knowledge-base snippets retain SOURCE and LICENCE headers in data/knowledge-base. Do not redistribute third-party content beyond those grants.

Optional sentence-transformer weights follow Hugging Face model card terms when downloaded for dense experiments.`,

  credits: `Product and research direction: MediVault Research / Priyanshu Goyal.
Engineering surfaces: FastAPI services, React research portal, React demo SPA.
Intelligence: statistical anomaly design, BM25 retrieval, safety rules, evaluation harnesses.
Institutional documentation: BIBLE.md, Plan B/C reports, presentation claims sheet.
Visual system: clinical research site design tokens, Canvas scientific visuals, institutional typography (Space Grotesk, Source Serif 4, IBM Plex Mono).`,
};

// Navigation (unchanged structure)
export const navPrimary = [
  { label: "Research", href: "/research" },
  { label: "Technology", href: "/technology" },
  { label: "Methodology", href: "/methodology" },
  { label: "Benchmarks", href: "/benchmarks" },
  { label: "Publications", href: "/publications" },
];

export const navMega = [
  {
    title: "Science",
    links: [
      { label: "Research overview", href: "/research" },
      { label: "Methodology", href: "/methodology" },
      { label: "Datasets", href: "/datasets" },
      { label: "Benchmarks", href: "/benchmarks" },
      { label: "Publications", href: "/publications" },
    ],
  },
  {
    title: "Systems",
    links: [
      { label: "Technology", href: "/technology" },
      { label: "Architecture", href: "/architecture" },
      { label: "Features", href: "/features" },
      { label: "Documentation", href: "/documentation" },
      { label: "Downloads", href: "/downloads" },
    ],
  },
  {
    title: "Institute",
    links: [
      { label: "About", href: "/about" },
      { label: "Team", href: "/team" },
      { label: "Partners", href: "/partners" },
      { label: "Timeline", href: "/timeline" },
      { label: "Contact", href: "/contact" },
    ],
  },
  {
    title: "Media",
    links: [
      { label: "Gallery", href: "/gallery" },
      { label: "Blog", href: "/blog" },
      { label: "News", href: "/news" },
      { label: "Press kit", href: "/press" },
      { label: "Media resources", href: "/media" },
    ],
  },
];

export const footerColumns = [
  {
    title: "Research",
    links: [
      { label: "Overview", href: "/research" },
      { label: "Methodology", href: "/methodology" },
      { label: "Benchmarks", href: "/benchmarks" },
      { label: "Publications", href: "/publications" },
    ],
  },
  {
    title: "Platform",
    links: [
      { label: "Technology", href: "/technology" },
      { label: "Architecture", href: "/architecture" },
      { label: "Documentation", href: "/documentation" },
      { label: "Downloads", href: "/downloads" },
    ],
  },
  {
    title: "Institution",
    links: [
      { label: "About", href: "/about" },
      { label: "Team", href: "/team" },
      { label: "Partners", href: "/partners" },
      { label: "Contact", href: "/contact" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
      { label: "Accessibility", href: "/accessibility" },
      { label: "Licenses", href: "/licenses" },
    ],
  },
];

/** @deprecated use narrative — kept null-safe alias */
export const placeholders = narrative;
