/* =============================================================================
   AI HEALTH AGENT — CONVERSATIONAL AI HEALTH ASSISTANT (health-chat.js)
   ============================================================================= */

const HealthChat = {
  currentConsultationId: null,
  historyMemory: [],

  initChat() {
    const input = document.getElementById("chat-user-input");
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }
  },

  async sendMessage(customText = null) {
    const input = document.getElementById("chat-user-input");
    const text = (customText || (input ? input.value : "")).trim();
    if (!text) return;

    if (input && !customText) input.value = "";

    this.appendMessage("patient", text);

    const typingId = this.showTypingIndicator();

    try {
      let res;
      const payload = {
        message: text,
        consultation_id: this.currentConsultationId,
        history: this.historyMemory
      };

      if (typeof Auth !== "undefined" && Auth.isLoggedIn && Auth.isLoggedIn()) {
        res = await Auth.fetchWithAuth("/api/ai/chat", {
          method: "POST",
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch("/api/ai/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      }

      this.removeTypingIndicator(typingId);

      if (!res) return;
      const data = await res.json();

      if (data.success) {
        this.currentConsultationId = data.consultation_id;
        
        // Record in client history for step-by-step turns
        this.historyMemory.push({ sender_type: "PATIENT", message_text: text });
        this.historyMemory.push({ sender_type: "AI_ASSISTANT", message_text: data.response });

        this.appendMessage("ai", data.response, data.disclaimer, data.learned_memory, data.profile_memory_updated);

        if (data.red_flag_alert) {
          this.showEmergencyBanner();
        }

        if (data.follow_up_questions && data.follow_up_questions.length > 0) {
          this.renderFollowUpChips(data.follow_up_questions);
        }

        // Show share with doctor button only if logged in
        const shareBtn = document.getElementById("share-consultation-btn");
        if (shareBtn && typeof Auth !== "undefined" && Auth.isLoggedIn && Auth.isLoggedIn()) {
          shareBtn.style.display = "inline-flex";
        }
      } else {
        this.appendMessage("ai", "I apologize, but I could not process your query at this moment: " + (data.error || "Please try again."));
      }
    } catch (err) {
      this.removeTypingIndicator(typingId);
      this.appendMessage("ai", "Network connection error. Please ensure the backend server is running.");
    }
  },

  formatDoctorMessage(rawText) {
    if (!rawText) return "";

    let processed = rawText;

    // 1. Detect Markdown Table (Prescription Box) and transform to rich styled card
    const tableRegex = /(\|[^\n]+\|\r?\n\|[-:\s|]+\|\r?\n(?:\|[^\n]+\|\r?\n?)+)/g;
    processed = processed.replace(tableRegex, (match) => {
      const lines = match.trim().split(/\r?\n/).filter(l => l.trim().startsWith("|") && l.trim().endsWith("|"));
      if (lines.length < 3) return match;

      const parseCells = (line) => line.split("|").slice(1, -1).map(c => c.trim());
      const headers = parseCells(lines[0]);
      const dataRows = lines.slice(2).map(parseCells);

      const thHtml = headers.map(h => {
        let cleanH = h.replace(/\*\*(.*?)\*\*/g, "$1");
        return `<th style="padding:0.5rem 0.65rem; text-align:left; font-weight:700; border-bottom:2px solid #bae6fd; font-size:0.83rem;">${cleanH}</th>`;
      }).join("");

      const trHtml = dataRows.map((row, idx) => {
        const bg = idx % 2 === 0 ? "#ffffff" : "#f8fafc";
        const tdHtml = row.map(cell => {
          let cleanCell = cell.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
          return `<td style="padding:0.5rem 0.65rem; border-bottom:1px solid #e2e8f0; font-size:0.82rem; color:#1e293b;">${cleanCell}</td>`;
        }).join("");
        return `<tr style="background:${bg};">${tdHtml}</tr>`;
      }).join("");

      return `
        <div class="prescription-box-card" style="margin:0.85rem 0; background:#f0f9ff; border:2px solid #0284c7; border-radius:10px; overflow:hidden; box-shadow:0 4px 14px rgba(2,132,199,0.12);">
          <div style="background:linear-gradient(135deg, #0284c7, #0369a1); color:#fff; padding:0.55rem 0.85rem; display:flex; justify-content:space-between; align-items:center; font-weight:700; font-size:0.88rem;">
            <div style="display:flex; align-items:center; gap:0.45rem;">
              <span>🩺</span> <span>Dr. Aanya's Prescription Box (Rx)</span>
            </div>
            <span style="background:rgba(255,255,255,0.25); font-size:0.75rem; padding:0.15rem 0.5rem; border-radius:4px; font-weight:600;">Safe Supportive Care</span>
          </div>
          <div style="overflow-x:auto; padding:0.25rem;">
            <table style="width:100%; border-collapse:collapse; min-width:480px;">
              <thead>
                <tr style="background:#e0f2fe; color:#0369a1;">
                  ${thHtml}
                </tr>
              </thead>
              <tbody>
                ${trHtml}
              </tbody>
            </table>
          </div>
        </div>
      `;
    });

    // 2. Format Bold & Italic
    processed = processed
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>");

    // 3. Clean bullet points
    processed = processed.replace(/(?:^|\n)[*•]\s+([^\n]+)/g, "<br>• $1");

    // 4. Line breaks
    processed = processed.replace(/\n\n+/g, "<br><br>").replace(/\n/g, "<br>");

    // 5. Clean up any excess breaks around card
    processed = processed.replace(/<br>\s*(<div class="prescription-box-card")/g, "$1");
    processed = processed.replace(/(<\/div>\s*<\/div>)\s*<br>/g, "$1");

    return processed;
  },

  appendMessage(sender, text, disclaimer = "", learnedMemory = null, isPersisted = false) {
    const container = document.getElementById("chat-messages-container");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-msg ${sender}`;

    const avatarText = sender === "patient" ? "ME" : "Dr.";
    const avatarClass = sender === "patient" ? "avatar-patient" : "avatar-ai";

    // Format rich text with Prescription Box
    const formattedText = this.formatDoctorMessage(text);

    // Memory badge if learned facts occurred
    let memoryBadgeHtml = "";
    if (learnedMemory && (learnedMemory.allergies?.length || learnedMemory.conditions?.length)) {
      const items = [
        ...(learnedMemory.allergies || []).map(a => `Allergy: ${a}`),
        ...(learnedMemory.conditions || []).map(c => `Condition: ${c}`)
      ].join(", ");

      memoryBadgeHtml = `
        <div style="margin-top:0.6rem; padding:0.4rem 0.75rem; background:#ecfdf5; border:1px solid #a7f3d0; border-radius:6px; font-size:0.82rem; color:#065f46; display:flex; align-items:center; gap:0.4rem;">
          <span>🧠</span>
          <span><strong>Doctor's Memory Saved:</strong> ${items}${isPersisted ? " (Synced to Patient Database)" : ""}</span>
        </div>
      `;
    }

    msgDiv.innerHTML = `
      <div class="chat-avatar ${avatarClass}">${avatarText}</div>
      <div class="chat-bubble">
        <div>${formattedText}</div>
        ${memoryBadgeHtml}
        ${disclaimer ? `<div class="chat-disclaimer">ℹ️ ${disclaimer}</div>` : ""}
      </div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  },

  showTypingIndicator() {
    const container = document.getElementById("chat-messages-container");
    if (!container) return null;

    const id = "typing-" + Date.now();
    const div = document.createElement("div");
    div.id = id;
    div.className = "chat-msg ai";
    div.innerHTML = `
      <div class="chat-avatar avatar-ai">Dr.</div>
      <div class="chat-bubble" style="color:var(--slate-500); font-style:italic; display:flex; align-items:center; gap:0.5rem;">
        <span class="loading-spinner" style="width:14px; height:14px; border:2px solid #cbd5e1; border-top-color:#0284c7; border-radius:50%; animation:spin 0.8s linear infinite;"></span>
        Dr. Aanya is reviewing your symptoms & clinical memory...
      </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
  },

  removeTypingIndicator(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  },

  showEmergencyBanner() {
    let banner = document.getElementById("chat-emergency-alert-banner");
    if (!banner) {
      const container = document.getElementById("chat-container-card");
      if (container) {
        banner = document.createElement("div");
        banner.id = "chat-emergency-alert-banner";
        banner.className = "emergency-banner";
        banner.innerHTML = "🚨 POTENTIAL EMERGENCY DETECTED: PLEASE CALL EMERGENCY SERVICES (112 / 911) OR VISIT AN EMERGENCY ROOM IMMEDIATELY.";
        container.prepend(banner);
      }
    }
  },

  renderFollowUpChips(questions) {
    const chipsContainer = document.getElementById("chat-quick-chips-bar");
    if (!chipsContainer || !questions || questions.length === 0) return;

    chipsContainer.innerHTML = questions.map(q => {
      const cleanQ = q.replace(/'/g, "\\'");
      const lowerQ = q.toLowerCase();
      if (lowerQ.includes("find") && lowerQ.includes("doctor")) {
        return `<a href="doctor-search.html" class="quick-chip" style="background:#e0f2fe; color:#0284c7; font-weight:700;">🩺 ${q}</a>`;
      }
      if (lowerQ.includes("medicine database")) {
        return `<a href="medicine-search.html" class="quick-chip" style="background:#f3e8ff; color:#7c3aed; font-weight:700;">💊 ${q}</a>`;
      }
      return `<button onclick="HealthChat.sendMessage('${cleanQ}')" class="quick-chip">👉 ${q}</button>`;
    }).join("");
  },

  async openShareModal() {
    if (!this.currentConsultationId) {
      alert("Start a consultation first before sharing with a doctor.");
      return;
    }

    const select = document.getElementById("share-doctor-select");
    const modal = document.getElementById("share-modal");
    if (!select || !modal) return;

    try {
      const res = await fetch("/api/appointments/doctors?verified_only=true");
      const data = await res.json();
      if (data.success && data.doctors.length > 0) {
        select.innerHTML = data.doctors.map(d => `
          <option value="${d.doctor_id}">Dr. ${d.full_name} (${d.specialty})</option>
        `).join("");
      } else {
        select.innerHTML = `<option value="">No verified doctors currently available</option>`;
      }
      modal.classList.add("active");
    } catch (e) {
      alert("Failed to load verified doctors: " + e.message);
    }
  },

  closeShareModal() {
    const modal = document.getElementById("share-modal");
    if (modal) modal.classList.remove("active");
  },

  async submitShareWithDoctor() {
    const select = document.getElementById("share-doctor-select");
    const doctorId = select ? select.value : null;

    if (!doctorId) {
      alert("Please select a verified doctor.");
      return;
    }

    try {
      const res = await Auth.fetchWithAuth(`/api/ai/consultations/${this.currentConsultationId}/share`, {
        method: "POST",
        body: JSON.stringify({ doctor_id: doctorId })
      });
      if (!res) return;
      const data = await res.json();

      if (data.success) {
        alert("Consultation securely shared with doctor!");
        this.closeShareModal();
      } else {
        alert(data.error || "Failed to share.");
      }
    } catch (err) {
      alert("Error sharing: " + err.message);
    }
  }
};
