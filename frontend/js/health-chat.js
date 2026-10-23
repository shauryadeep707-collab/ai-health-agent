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

        this.appendMessage("ai", data.response, data.disclaimer);

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

  appendMessage(sender, text, disclaimer = "") {
    const container = document.getElementById("chat-messages-container");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-msg ${sender}`;

    const avatarText = sender === "patient" ? "ME" : "AI";
    const avatarClass = sender === "patient" ? "avatar-patient" : "avatar-ai";

    // Clean markdown-like formatting
    let formattedText = text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/\n/g, "<br>");

    msgDiv.innerHTML = `
      <div class="chat-avatar ${avatarClass}">${avatarText}</div>
      <div class="chat-bubble">
        <div>${formattedText}</div>
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
      <div class="chat-avatar avatar-ai">AI</div>
      <div class="chat-bubble" style="color:var(--slate-400); font-style:italic;">
        Thinking & checking medical safety guidelines...
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
