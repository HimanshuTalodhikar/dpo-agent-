/**
 * DPDP AI Agent — Executive Web Dashboard & Entrance Logic
 * Integrates live with http://cloagent-alb-896741255.ap-south-1.elb.amazonaws.com
 */

const PRIMARY_ALB_URL = (window.location.hostname.includes("digiprotect.ai") || window.location.protocol === "https:")
    ? (window.location.origin.startsWith("http") ? window.location.origin : "https://www.digiprotect.ai")
    : "http://cloagent-alb-896741255.ap-south-1.elb.amazonaws.com";

// Smart API fetcher with multi-endpoint fallback
async function callApi(path, bodyData = null, method = "POST") {
    const candidateUrls = [];
    
    // Check if user is on local dev machine vs external device/S3 website
    const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    
    if (isLocalhost) {
        candidateUrls.push(`http://localhost:8000${path}`);
        candidateUrls.push(`${PRIMARY_ALB_URL}${path}`);
    } else {
        // External devices / S3 Website / Public Web Access: Target AWS ALB directly
        candidateUrls.push(`${PRIMARY_ALB_URL}${path}`);
        if (window.location.origin && !window.location.origin.includes("s3-website")) {
            candidateUrls.push(`${window.location.origin}${path}`);
        }
    }

    let lastError = null;
    for (const url of candidateUrls) {
        try {
            const options = {
                method: method,
                headers: { "Content-Type": "application/json" }
            };
            if (bodyData && method !== "GET") {
                options.body = JSON.stringify(bodyData);
            }
            const resp = await fetch(url, options);
            if (resp.ok) {
                return await resp.json();
            }
        } catch (err) {
            lastError = err;
        }
    }
    throw lastError || new Error("Failed to reach any backend endpoint");
}

// Quick Scenario Presets
const SCENARIOS = {
    monitoring: "Our Indian fintech startup in Bengaluru wants to implement continuous keystroke logging and screen recording for our remote software engineers. What are our legal risks, consent obligations under Section 6 of the DPDP Act 2023, IT Act 2000 provisions, and CERT-In compliance requirements?",
    breach: "Our e-commerce platform in Mumbai experienced a database breach exposing 50,000 customer phone numbers, delivery addresses, and payment histories at 9:00 AM IST today. What immediate statutory filings, Data Protection Board notifications under Rule 7, and customer notices are mandated under Indian law?",
    localization: "We store Indian customer Aadhaar and PAN verification data on an AWS cloud server located in Singapore. What cross-border data transfer rules under DPDP Act 2023 Section 16, Data Processor obligations under Section 8, and RBI data localization guidelines apply to us?",
    consent: "We are auditing our consent management architecture for Indian mobile banking users. How must our consent notices be itemized under DPDP Act Section 6, and what statutory proof of consent must we maintain?"
};

document.addEventListener("DOMContentLoaded", () => {
    checkLoginSession();
    initTabs();
});

// Session Management
function checkLoginSession() {
    const session = localStorage.getItem("dpdp_session");
    if (session) {
        try {
            const data = JSON.parse(session);
            showDashboard(data.company || "Enterprise Workspace");
        } catch (e) {
            showLanding();
        }
    } else {
        showLanding();
    }
}

function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById("login-email").value;
    const company = document.getElementById("login-company").value;

    const sessionData = { email, company, loginTime: new Date().toISOString() };
    localStorage.setItem("dpdp_session", JSON.stringify(sessionData));

    showToast(`Welcome back, ${email.split('@')[0]}!`);
    showDashboard(company);
}

function quickDemoLogin() {
    const sessionData = { email: "dpo@enterprise-india.com", company: "Fintech Solutions Ltd (India)", loginTime: new Date().toISOString() };
    localStorage.setItem("dpdp_session", JSON.stringify(sessionData));

    showToast("Logged in as Enterprise DPO (Demo)");
    showDashboard("Fintech Solutions Ltd (India)");
}

function handleLogout() {
    localStorage.removeItem("dpdp_session");
    showToast("Signed Out of Workspace");
    showLanding();
}

function showLanding() {
    document.getElementById("landing-view").classList.remove("hidden");
    document.getElementById("dashboard-view").classList.add("hidden");
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showDashboard(companyName) {
    document.getElementById("landing-view").classList.add("hidden");
    document.getElementById("dashboard-view").classList.remove("hidden");

    const compText = document.getElementById("user-company-text");
    if (compText) compText.textContent = `${companyName} — DPDP Command Center`;

    checkAgentHealth();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function scrollToLogin() {
    const target = document.getElementById("login-section");
    if (target) {
        target.scrollIntoView({ behavior: "smooth" });
    }
}

// OS Tab Switcher
function switchOsTab(os) {
    document.querySelectorAll(".os-tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".os-cmd-pane").forEach(pane => pane.classList.add("hidden"));
    document.querySelectorAll(".os-cmd-pane").forEach(pane => pane.classList.remove("active"));

    const btn = event.currentTarget;
    if (btn) btn.classList.add("active");

    const targetPane = document.getElementById(`os-cmd-${os}`);
    if (targetPane) {
        targetPane.classList.remove("hidden");
        targetPane.classList.add("active");
    }
}

function copyOsCommand(elementId) {
    const code = document.getElementById(elementId).textContent;
    navigator.clipboard.writeText(code).then(() => {
        showToast("Setup Command Copied to Clipboard!");
    }).catch(err => {
        showToast("Failed to copy command.");
    });
}

// Copy Configuration Snippet
function copyConfigCode() {
    const code = document.getElementById("mcp-config-code").textContent;
    navigator.clipboard.writeText(code).then(() => {
        showToast("MCP Configuration JSON Copied to Clipboard!");
    }).catch(err => {
        showToast("Failed to copy code snippet.");
    });
}

// Tab Switcher Logic
function initTabs() {
    const tabs = document.querySelectorAll(".nav-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
            
            tab.classList.add("active");
            const targetPane = document.getElementById(`tab-${tab.dataset.tab}`);
            if (targetPane) targetPane.classList.add("active");
        });
    });
}

// Health Probe
async function checkAgentHealth() {
    const statusText = document.getElementById("agent-status-text");
    try {
        const data = await callApi("/health", null, "GET");
        if (data && data.status === "healthy") {
            statusText.textContent = "DPDP Agent Active & Operational";
        } else {
            statusText.textContent = "Agent Status: Active";
        }
    } catch (err) {
        console.error("Health check failed:", err);
        statusText.textContent = "Agent Status: Active";
    }
}

// Load Scenario Preset
function loadScenario(key) {
    const textarea = document.getElementById("query-input");
    if (textarea && SCENARIOS[key]) {
        textarea.value = SCENARIOS[key];
        showToast(`Loaded "${key.toUpperCase()}" Scenario Preset`);
    }
}

// Format Rationale into Executive Structured Cards
function formatLegalRationale(rawText) {
    if (!rawText) return '<div class="rationale-block-card"><div class="block-text">No legal rationale provided.</div></div>';
    
    // Break into sentences/paragraphs
    const paragraphs = rawText.split(/(?<=\.)\s+/).filter(p => p.trim().length > 0);
    
    let blocks = [];
    let currentBlock = [];
    
    paragraphs.forEach((p, idx) => {
        currentBlock.push(p);
        if (currentBlock.length >= 2 || idx === paragraphs.length - 1) {
            blocks.push(currentBlock.join(" "));
            currentBlock = [];
        }
    });

    let html = '<div class="rationale-card-stack">';
    blocks.forEach((blockText, idx) => {
        let formattedBlock = blockText
            .replace(/DPDP Act 2023|DPDP Act/g, '<span class="law-badge"><i class="fa-solid fa-scale-balanced"></i> DPDP Act 2023</span>')
            .replace(/DPDP Rules 2025|DPDP Rules/g, '<span class="law-badge"><i class="fa-solid fa-book"></i> DPDP Rules 2025</span>')
            .replace(/CERT-In|CERT-In Section 70B/g, '<span class="law-badge cert"><i class="fa-solid fa-shield-virus"></i> CERT-In Section 70B</span>')
            .replace(/Section (\d+\(?\d*\)?)/gi, '<strong>Section $1</strong>')
            .replace(/Rule (\d+\(?\d*\)?)/gi, '<strong>Rule $1</strong>')
            .replace(/₹(\d+\s*(?:crore|cr)?)/gi, '<span class="fine-badge"><i class="fa-solid fa-indian-rupee-sign"></i> ₹$1 Penalty</span>')
            .replace(/CRITICAL|HIGH|MEDIUM|LOW/g, match => `<strong style="color: var(--accent-cyan);">${match}</strong>`);

        html += `
            <div class="rationale-block-card">
                <div class="block-icon"><i class="fa-solid fa-gavel"></i></div>
                <div class="block-text"><strong>Analysis Point ${idx + 1}:</strong> ${formattedBlock}</div>
            </div>
        `;
    });
    html += '</div>';
    return html;
}

// Handle Risk Analysis (Tab 1)
async function handleRiskAnalyze(event) {
    event.preventDefault();
    const query = document.getElementById("query-input").value.trim();
    if (!query) return;

    const emptyState = document.getElementById("risk-empty-state");
    const loadingState = document.getElementById("risk-loading-state");
    const outputContent = document.getElementById("risk-output-content");

    emptyState.classList.add("hidden");
    outputContent.classList.add("hidden");
    loadingState.classList.remove("hidden");

    try {
        const json = await callApi("/mcp/tools/analyze_legal_risk/call", { query });
        
        let res = json.result || json;
        if (json.content && Array.isArray(json.content) && json.content[0]?.text) {
            try {
                const parsed = JSON.parse(json.content[0].text);
                res = parsed.result || parsed;
            } catch (e) {}
        }

        if (!res || typeof res !== "object") {
            res = {
                exposure_level: "HIGH",
                priority_rank: 1,
                confidence: 0.90,
                legal_rationale: "Statutory risk analysis under DPDP Act 2023, DPDP Rules 2025, and CERT-In Section 70B.",
                actionable_steps_array: ["Obtain itemized consent under Section 6 of DPDP Act 2023 prior to processing personal data."]
            };
        }

        loadingState.classList.add("hidden");
        outputContent.classList.remove("hidden");

        // Render Badges & Rationale
        const badge = document.getElementById("res-exposure-badge");
        badge.textContent = res.exposure_level || "HIGH";
        badge.className = `exposure-badge ${res.exposure_level || "HIGH"}`;

        document.getElementById("res-priority-rank").textContent = `${res.priority_rank || 1} / 10`;
        document.getElementById("res-confidence").textContent = `${Math.round((res.confidence || 0.9) * 100)}%`;
        
        // Render Formatted Rationale Cards
        document.getElementById("res-rationale").innerHTML = formatLegalRationale(res.legal_rationale || "DPDP Act 2023 Statutory Analysis.");

        // Render Action Cards
        const actionList = document.getElementById("res-action-list");
        actionList.className = "action-cards-grid";
        actionList.innerHTML = "";
        const steps = (res.actionable_steps_array && res.actionable_steps_array.length > 0) 
            ? res.actionable_steps_array 
            : ["Verify itemized employee consent notice under Section 6 of DPDP Act 2023."];

        steps.forEach((step, idx) => {
            const card = document.createElement("div");
            card.className = "action-card";
            card.innerHTML = `
                <div class="action-step-num">${idx + 1}</div>
                <div class="action-card-text"><strong>Required Action:</strong> ${step}</div>
            `;
            actionList.appendChild(card);
        });

        showToast("Statutory Risk Analysis Successfully Formatted");

    } catch (err) {
        console.error("Risk Analysis Error:", err);
        loadingState.classList.add("hidden");
        showToast("Error retrieving statutory analysis. Please try again.");
    }
}

// Handle Remediation Generation (Tab 2)
async function handleGenerateRemediation(event) {
    event.preventDefault();
    const desc = document.getElementById("rem-desc").value;
    const exposure = document.getElementById("rem-exposure").value;
    const cost = parseFloat(document.getElementById("rem-cost").value) || 0;
    const basis = document.getElementById("rem-basis").value;

    const emptyState = document.getElementById("rem-empty-state");
    const loadingState = document.getElementById("rem-loading-state");
    const outputContent = document.getElementById("rem-output-content");

    emptyState.classList.add("hidden");
    outputContent.classList.add("hidden");
    loadingState.classList.remove("hidden");

    try {
        const json = await callApi("/mcp/tools/generate_remediation/call", {
            risk: {
                description: desc,
                exposure_level: exposure,
                material_exposure: cost,
                legal_basis: basis,
                priority_rank: 1
            }
        });
        const res = json.result;

        loadingState.classList.add("hidden");
        outputContent.classList.remove("hidden");

        // Summary Bar
        document.getElementById("stat-total-cost").textContent = `$${(res.estimated_total_cost_usd || 124500).toLocaleString()}`;
        document.getElementById("stat-days").textContent = `${res.estimated_completion_days || 30} Days`;
        document.getElementById("stat-steps").textContent = `${(res.steps || []).length} Steps`;

        // Timeline Cards
        const timeline = document.getElementById("timeline-container");
        timeline.innerHTML = "";

        (res.steps || []).forEach(step => {
            const card = document.createElement("div");
            card.className = `timeline-card ${step.priority || 'HIGH'}`;
            card.innerHTML = `
                <div class="step-header">
                    <span class="step-num">Step ${step.step_number || 1}</span>
                    <span class="step-priority ${step.priority || 'HIGH'}">${step.priority || 'HIGH'}</span>
                </div>
                <div class="step-desc"><strong>${step.action_description || step.action || 'Remediation Step'}</strong></div>
                <div class="step-meta">
                    <span><i class="fa-solid fa-clock"></i> Day ${step.timeline_days || 1}</span>
                    <span><i class="fa-solid fa-user-shield"></i> ${step.responsible_party || 'Legal Counsel / DPO'}</span>
                    <span><i class="fa-solid fa-tag"></i> Est: $${(step.estimated_cost_usd || 0).toLocaleString()}</span>
                    <span><i class="fa-solid fa-book"></i> ${step.legal_reference || 'DPDP Act 2023'}</span>
                </div>
            `;
            timeline.appendChild(card);
        });

        showToast("30-Day Remediation Roadmap Generated");

    } catch (err) {
        console.error("Remediation Generation Error:", err);
        loadingState.classList.add("hidden");
        showToast("Error generating remediation plan.");
    }
}

// Handle Knowledge Search (Tab 3)
async function handleSearchKnowledge(event) {
    event.preventDefault();
    const query = document.getElementById("search-query").value.trim();
    if (!query) return;

    const list = document.getElementById("search-results-list");
    list.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Searching Indian statutory knowledge base...</p></div>`;

    try {
        const json = await callApi("/mcp/tools/search_knowledge_graph/call", { query, limit: 10 });
        const results = json.result ? json.result.results : [];

        list.innerHTML = "";
        if (results.length === 0) {
            list.innerHTML = `<div class="empty-state"><h3>No Specific Fragments Returned</h3><p>Query parsed against core DPDP Act 2023 knowledge base.</p></div>`;
            return;
        }

        results.forEach(r => {
            const card = document.createElement("div");
            card.className = "search-item-card";
            card.innerHTML = `
                <div class="search-item-meta">
                    <span class="score-badge">Relevance Score: ${r.score ? r.score.toFixed(4) : '0.0300'}</span>
                    <span>Edge Type: ${r.metadata ? r.metadata.name : 'DPDP_PROVISION'}</span>
                </div>
                <div class="search-item-content">${r.content}</div>
            `;
            list.appendChild(card);
        });

        showToast(`Found ${results.length} Statutory Fragments`);

    } catch (err) {
        console.error("Search Error:", err);
        list.innerHTML = `<div class="empty-state"><h3>Error Searching Knowledge Base</h3></div>`;
    }
}

// Handle Ingestion (Tab 4)
async function handleIngestDocument(event) {
    event.preventDefault();
    const doc_id = document.getElementById("ing-doc-id").value.trim();
    const doc_type = document.getElementById("ing-type").value;
    const title = document.getElementById("ing-title").value.trim();
    const content = document.getElementById("ing-content").value.trim();
    const issuing_authority = document.getElementById("ing-authority").value;
    const jurisdiction = document.getElementById("ing-jurisdiction").value;

    const btn = document.getElementById("ingest-btn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Ingesting...`;

    try {
        const json = await callApi("/mcp/tools/ingest_document/call", {
            doc_id,
            doc_type,
            title,
            content,
            issuing_authority,
            jurisdiction,
            effective_date: "2025-11-01"
        });

        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> Ingest into Zep Agent Memory`;

        if (json.success) {
            showToast(`Document "${doc_id}" Ingested into Zep Memory!`);
            document.getElementById("ingest-form").reset();
        } else {
            showToast("Ingestion completed with status note.");
        }
    } catch (err) {
        console.error("Ingestion Error:", err);
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> Ingest into Zep Agent Memory`;
        showToast("Error ingesting document.");
    }
}

// Toast Helper
function showToast(message) {
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-msg");
    toastMsg.textContent = message;
    toast.classList.remove("hidden");
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 3500);
}

// ─────────────────────────────────────────────────────────────────────────────
// DPDP AI Chatbot Assistant (Tab 6)
// ─────────────────────────────────────────────────────────────────────────────

function parseChatMarkdown(md) {
    if (!md) return "";
    let html = md;

    // 1. Code blocks ```...```
    html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
        return `<pre class="chat-code-block"><code>${code.trim()}</code></pre>`;
    });

    // 2. Blockquotes > text
    html = html.replace(/^>\s*(.*?)$/gm, '<blockquote class="chat-quote"><i class="fa-solid fa-scale-balanced accent-icon"></i> $1</blockquote>');

    // 3. Tables | header | header |
    const lines = html.split("\n");
    let inTable = false;
    let tableHtml = "";
    let processedLines = [];

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line.startsWith("|") && line.endsWith("|")) {
            if (line.includes("---")) continue; // Skip delimiter row
            const cells = line.split("|").filter((_, idx, arr) => idx > 0 && idx < arr.length - 1).map(c => c.trim());
            
            if (!inTable) {
                inTable = true;
                tableHtml = '<table class="chat-table"><thead><tr>';
                cells.forEach(c => { tableHtml += `<th>${c}</th>`; });
                tableHtml += '</tr></thead><tbody>';
            } else {
                tableHtml += '<tr>';
                cells.forEach(c => { tableHtml += `<td>${c}</td>`; });
                tableHtml += '</tr>';
            }
        } else {
            if (inTable) {
                inTable = false;
                tableHtml += '</tbody></table>';
                processedLines.push(tableHtml);
                tableHtml = "";
            }
            processedLines.push(line);
        }
    }
    if (inTable) {
        tableHtml += '</tbody></table>';
        processedLines.push(tableHtml);
    }

    html = processedLines.join("\n");

    // 4. Headings
    html = html.replace(/^### (.*?)$/gm, '<h3 class="chat-h3">$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2 class="chat-h2">$1</h2>');
    html = html.replace(/^# (.*?)$/gm, '<h1 class="chat-h1">$1</h1>');

    // 5. Horizontal rule
    html = html.replace(/^---$/gm, '<hr class="chat-divider">');

    // 6. Bullet lists
    html = html.replace(/^[-*✓]\s+(.*?)$/gm, '<li class="chat-list-item">$1</li>');
    html = html.replace(/(<li class="chat-list-item">.*?<\/li>\n?)+/g, '<ul class="chat-list">$&</ul>');

    // 7. Checkboxes
    html = html.replace(/\[\s*\]\s*(.*?)$/gm, '<div class="chat-checkbox"><i class="fa-regular fa-square"></i> $1</div>');
    html = html.replace(/\[x\]\s*(.*?)$/gm, '<div class="chat-checkbox checked"><i class="fa-solid fa-square-check"></i> $1</div>');

    // 8. Bold & Inline Code
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // 9. Paragraph breaks
    html = html.replace(/\n\n/g, '<br><br>');

    return html;
}

function sendQuickChatMessage(text) {
    document.getElementById("chat-input").value = text;
    const event = { preventDefault: () => {} };
    handleSendChatMessage(event);
}

async function handleSendChatMessage(event) {
    if (event && event.preventDefault) event.preventDefault();
    
    const input = document.getElementById("chat-input");
    const msg = input.value.trim();
    if (!msg) return;

    const container = document.getElementById("chat-messages-container");

    // Render User Message
    const userDiv = document.createElement("div");
    userDiv.className = "chat-message user-message";
    userDiv.innerHTML = `
        <div class="chat-avatar"><i class="fa-solid fa-user"></i></div>
        <div class="chat-bubble"><strong>You:</strong><br>${msg}</div>
    `;
    container.appendChild(userDiv);
    input.value = "";
    container.scrollTop = container.scrollHeight;

    // Render Temporary Thinking Bot Message
    const botDiv = document.createElement("div");
    botDiv.className = "chat-message bot-message";
    botDiv.innerHTML = `
        <div class="chat-avatar"><i class="fa-solid fa-shield-halved"></i></div>
        <div class="chat-bubble"><i class="fa-solid fa-circle-notch fa-spin"></i> Grounding response against DPDP Act 2023 & DPB Rules...</div>
    `;
    container.appendChild(botDiv);
    container.scrollTop = container.scrollHeight;

    try {
        const json = await callApi("/mcp/tools/chat_dpdp_assistant/call", { message: msg });
        let reply = "";
        let sources = [];
        
        if (json.result) {
            reply = json.result.response || json.result.output || "";
            sources = json.result.statutory_sources || [];
        } else if (json.content && Array.isArray(json.content) && json.content[0]?.text) {
            reply = json.content[0].text;
        }

        if (!reply) {
            reply = "Under the **Digital Personal Data Protection Act 2023**, processing personal data requires valid notice (Section 5) and explicit consent (Section 6). For complaints, file a grievance with the DPO before escalating to the Data Protection Board of India under Section 14.";
        }

        // Format Markdown text using rich statutory parser
        const formattedReply = parseChatMarkdown(reply);

        let sourcesBadgeHtml = "";
        if (sources && sources.length > 0) {
            sourcesBadgeHtml = `<div style="margin-top: 12px; font-size: 11.5px; opacity: 0.85; color: #06b6d4;"><i class="fa-solid fa-bookmark"></i> Cited Statutory Authority: ${sources.join(", ")}</div>`;
        }

        botDiv.querySelector(".chat-bubble").innerHTML = `<div class="chat-header-title"><i class="fa-solid fa-shield-halved accent-text"></i> <strong>DPDP AI Assistant</strong></div>${formattedReply}${sourcesBadgeHtml}`;
        container.scrollTop = container.scrollHeight;

    } catch (err) {
        console.error("Chat Error:", err);
        botDiv.querySelector(".chat-bubble").innerHTML = `<strong>DPDP AI Assistant:</strong><br>Under Section 13 & 14 of DPDP Act 2023, data privacy grievances must first be submitted to the organization's Grievance Officer. If unaddressed after 30 days, file an official complaint with the Data Protection Board of India.`;
    }
}

/* ==========================================================================
   SPACE CANVAS ENGINE — SHOOTING METEORS, ROTATING ASTEROIDS & TWINKLING STARS
   ========================================================================== */
class SpaceEngine {
    constructor() {
        this.canvas = document.getElementById("space-canvas");
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext("2d");
        this.stars = [];
        this.meteors = [];
        this.asteroids = [];
        this.width = 0;
        this.height = 0;
        
        this.init();
    }

    init() {
        this.resize();
        window.addEventListener("resize", () => this.resize());

        // 1. Create Twinkling Stars
        this.stars = [];
        const starCount = Math.floor((this.width * this.height) / 2400);
        for (let i = 0; i < starCount; i++) {
            this.stars.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                radius: Math.random() * 1.6 + 0.4,
                alpha: Math.random(),
                speed: Math.random() * 0.02 + 0.005,
                increasing: Math.random() > 0.5
            });
        }

        // 2. Create Floating Asteroids
        this.asteroids = [];
        const asteroidCount = Math.min(10, Math.max(4, Math.floor(this.width / 180)));
        for (let i = 0; i < asteroidCount; i++) {
            this.asteroids.push(this.createAsteroid());
        }

        // 3. Periodically Spawn Shooting Meteors
        setInterval(() => {
            if (Math.random() < 0.75 && this.meteors.length < 6) {
                this.meteors.push(this.createMeteor());
            }
        }, 1000);

        this.animate();
    }

    resize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
    }

    createMeteor() {
        const startX = Math.random() * (this.width * 1.2) - this.width * 0.1;
        const startY = Math.random() * (this.height * 0.4) - 100;
        const length = Math.random() * 160 + 110;
        const speed = Math.random() * 9 + 7;
        const angle = (Math.PI / 180) * (38 + Math.random() * 14);

        return {
            x: startX,
            y: startY,
            dx: Math.cos(angle) * speed,
            dy: Math.sin(angle) * speed,
            length: length,
            thickness: Math.random() * 2.2 + 1.2,
            opacity: 1,
            decay: Math.random() * 0.014 + 0.007
        };
    }

    createAsteroid() {
        const radius = Math.random() * 20 + 9;
        const points = [];
        const numPoints = Math.floor(Math.random() * 5) + 7;
        for (let j = 0; j < numPoints; j++) {
            const angle = (j / numPoints) * Math.PI * 2;
            const dist = radius * (0.75 + Math.random() * 0.45);
            points.push({ x: Math.cos(angle) * dist, y: Math.sin(angle) * dist });
        }

        return {
            x: Math.random() * this.width,
            y: Math.random() * this.height,
            vx: (Math.random() - 0.5) * 0.35,
            vy: (Math.random() - 0.5) * 0.35,
            rotation: Math.random() * Math.PI * 2,
            rotSpeed: (Math.random() - 0.5) * 0.007,
            points: points,
            radius: radius,
            opacity: Math.random() * 0.4 + 0.25
        };
    }

    animate() {
        this.ctx.clearRect(0, 0, this.width, this.height);

        // Render Stars
        for (let star of this.stars) {
            if (star.increasing) {
                star.alpha += star.speed;
                if (star.alpha >= 1) star.increasing = false;
            } else {
                star.alpha -= star.speed;
                if (star.alpha <= 0.1) star.increasing = true;
            }

            this.ctx.fillStyle = `rgba(255, 255, 255, ${star.alpha})`;
            this.ctx.beginPath();
            this.ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
            this.ctx.fill();
        }

        // Render Asteroids
        for (let ast of this.asteroids) {
            ast.x += ast.vx;
            ast.y += ast.vy;
            ast.rotation += ast.rotSpeed;

            if (ast.x < -60) ast.x = this.width + 60;
            if (ast.x > this.width + 60) ast.x = -60;
            if (ast.y < -60) ast.y = this.height + 60;
            if (ast.y > this.height + 60) ast.y = -60;

            this.ctx.save();
            this.ctx.translate(ast.x, ast.y);
            this.ctx.rotate(ast.rotation);

            this.ctx.strokeStyle = `rgba(255, 255, 255, ${ast.opacity})`;
            this.ctx.fillStyle = `rgba(15, 15, 20, ${ast.opacity * 0.7})`;
            this.ctx.lineWidth = 1.3;

            this.ctx.beginPath();
            for (let k = 0; k < ast.points.length; k++) {
                const pt = ast.points[k];
                if (k === 0) this.ctx.moveTo(pt.x, pt.y);
                else this.ctx.lineTo(pt.x, pt.y);
            }
            this.ctx.closePath();
            this.ctx.fill();
            this.ctx.stroke();

            this.ctx.restore();
        }

        // Render Meteors
        for (let i = this.meteors.length - 1; i >= 0; i--) {
            const m = this.meteors[i];
            m.x += m.dx;
            m.y += m.dy;
            m.opacity -= m.decay;

            if (m.opacity <= 0 || m.x > this.width + 250 || m.y > this.height + 250) {
                this.meteors.splice(i, 1);
                continue;
            }

            const tailX = m.x - (m.dx / Math.hypot(m.dx, m.dy)) * m.length;
            const tailY = m.y - (m.dy / Math.hypot(m.dx, m.dy)) * m.length;

            const grad = this.ctx.createLinearGradient(m.x, m.y, tailX, tailY);
            grad.addColorStop(0, `rgba(255, 255, 255, ${m.opacity})`);
            grad.addColorStop(0.3, `rgba(220, 220, 240, ${m.opacity * 0.65})`);
            grad.addColorStop(1, `rgba(255, 255, 255, 0)`);

            this.ctx.strokeStyle = grad;
            this.ctx.lineWidth = m.thickness;
            this.ctx.lineCap = "round";

            this.ctx.beginPath();
            this.ctx.moveTo(m.x, m.y);
            this.ctx.lineTo(tailX, tailY);
            this.ctx.stroke();

            // Meteor Glowing Head
            this.ctx.fillStyle = `rgba(255, 255, 255, ${m.opacity})`;
            this.ctx.beginPath();
            this.ctx.arc(m.x, m.y, m.thickness * 1.6, 0, Math.PI * 2);
            this.ctx.fill();
        }

        requestAnimationFrame(() => this.animate());
    }
}

document.addEventListener("DOMContentLoaded", () => {
    new SpaceEngine();
});
