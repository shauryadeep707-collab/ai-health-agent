/* =============================================================================
   AI HEALTH AGENT — APPOINTMENTS & DOCTOR SEARCH (appointments.js)
   ============================================================================= */

const Appointments = {
  selectedDoctorId: null,

  async searchDoctors() {
    const query = document.getElementById("doc-search-query")?.value || "";
    const specialty = document.getElementById("doc-search-specialty")?.value || "";
    const jurisdiction = document.getElementById("doc-search-location")?.value || "";
    const resultsContainer = document.getElementById("doctors-results-grid");
    if (!resultsContainer) return;

    resultsContainer.innerHTML = `<p style="text-align:center; padding:2rem; color:var(--slate-400);">Searching verified doctors...</p>`;

    try {
      const params = new URLSearchParams({
        query,
        specialty,
        jurisdiction,
        verified_only: "false"
      });
      const res = await fetch(`/api/appointments/doctors?${params}`);
      const data = await res.json();

      if (data.success && data.doctors.length > 0) {
        resultsContainer.innerHTML = data.doctors.map(d => {
          const isVerified = d.verification_status === "VERIFIED";
          return `
            <div class="panel" style="display:flex; flex-direction:column; justify-content:space-between;">
              <div>
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
                  <div>
                    <h3 style="font-size:1.15rem; font-weight:700; color:var(--dark);">
                      ${d.full_name}
                    </h3>
                    <p style="color:var(--primary); font-weight:600; font-size:0.9rem;">
                      ${d.specialty}
                    </p>
                  </div>
                  <span class="badge ${isVerified ? 'badge-verified' : 'badge-pending'}">
                    ${isVerified ? '✓ DigiLocker Verified' : 'Pending Verification'}
                  </span>
                </div>

                <p style="font-size:0.875rem; color:var(--slate-600); margin-bottom:0.75rem; line-height:1.4;">
                  🎓 ${d.qualification}<br>
                  🏥 ${d.clinic_address || 'Clinic not specified'}<br>
                  ⏱️ ${d.experience_years} years experience | Fee: ₹${d.consultation_fee}
                </p>

                ${d.bio ? `<p style="font-size:0.825rem; color:var(--slate-400); font-style:italic; margin-bottom:1rem;">"${d.bio}"</p>` : ''}
              </div>

              <div>
                ${isVerified ? `
                  <button onclick="Appointments.openBookModal('${d.doctor_id}', '${d.full_name.replace(/'/g, "\\'")}', ${d.consultation_fee})" class="btn btn-primary btn-block btn-sm">
                    📅 Book Appointment
                  </button>
                ` : `
                  <button disabled class="btn btn-outline btn-block btn-sm" title="Only verified doctors can accept appointments">
                    ⏳ Verification In Progress
                  </button>
                `}
              </div>
            </div>
          `;
        }).join("");
      } else {
        resultsContainer.innerHTML = `<p style="text-align:center; padding:2rem; color:var(--slate-400); grid-column:1/-1;">No doctors found matching your criteria.</p>`;
      }
    } catch (err) {
      resultsContainer.innerHTML = `<p style="color:var(--danger); text-align:center; padding:2rem;">Failed to fetch doctors: ${err.message}</p>`;
    }
  },

  openBookModal(doctorId, doctorName, fee) {
    this.selectedDoctorId = doctorId;
    const modal = document.getElementById("book-apt-modal");
    const nameEl = document.getElementById("modal-doc-name");
    const feeEl = document.getElementById("modal-doc-fee");

    if (nameEl) nameEl.innerText = doctorName;
    if (feeEl) feeEl.innerText = `₹${fee}`;
    if (modal) modal.classList.add("active");
  },

  closeBookModal() {
    const modal = document.getElementById("book-apt-modal");
    if (modal) modal.classList.remove("active");
  },

  async submitBooking(event) {
    if (event) event.preventDefault();
    if (!this.selectedDoctorId) return;

    const date = document.getElementById("apt-date")?.value;
    const time = document.getElementById("apt-slot")?.value;
    const reason = document.getElementById("apt-reason")?.value;

    if (!date || !time) {
      alert("Please select appointment date and time.");
      return;
    }

    try {
      const res = await Auth.fetchWithAuth("/api/appointments/book", {
        method: "POST",
        body: JSON.stringify({
          doctor_id: this.selectedDoctorId,
          appointment_date: date,
          slot_time: time,
          reason
        })
      });
      if (!res) return;
      const data = await res.json();

      if (data.success) {
        alert(data.message);
        this.closeBookModal();
        this.loadMyAppointments();
      } else {
        alert(data.error || "Booking failed.");
      }
    } catch (err) {
      alert("Booking error: " + err.message);
    }
  },

  activeChatAptId: null,
  activeChatIsAiDoctor: false,
  activeChatDoctorName: "Doctor",

  async loadMyAppointments() {
    const container = document.getElementById("my-appointments-container");
    if (!container) return;

    try {
      const res = await Auth.fetchWithAuth("/api/appointments/my");
      if (!res) return;
      const data = await res.json();

      if (data.success && data.appointments.length > 0) {
        container.innerHTML = `
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Date & Time</th>
                  <th>Doctor / Patient</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${data.appointments.map(a => {
                  let cleanDocName = (a.doctor_name || "").replace(/^(?:dr\.?\s*)+/i, "").trim();
                  const displayName = cleanDocName ? `Dr. ${cleanDocName}` : (a.patient_name || 'Patient');
                  let badge = "badge-pending";
                  if (a.status === "CONFIRMED") badge = "badge-verified";
                  if (a.status === "CANCELLED") badge = "badge-rejected";
                  if (a.status === "COMPLETED") badge = "badge-verified";

                  const aiTag = a.is_ai_doctor
                    ? `<span class="badge badge-verified" style="margin-left:0.35rem; font-size:0.7rem; background:#e0f2fe; color:#0369a1; border:1px solid #bae6fd;">🤖 AI Instant Chat</span>`
                    : "";

                  return `
                    <tr>
                      <td><strong>${a.appointment_date}</strong><br><small>${a.slot_time}</small></td>
                      <td>${displayName}${aiTag}<br><small style="color:var(--slate-400);">${a.specialty || ''}</small></td>
                      <td>${a.reason_for_visit || 'Routine Consultation'}</td>
                      <td><span class="badge ${badge}">${a.status}</span></td>
                      <td>
                        <div style="display:flex; gap:0.35rem; align-items:center; flex-wrap:wrap;">
                          ${a.status === 'CONFIRMED' ? `
                            <button onclick="Appointments.openChatModal('${a.appointment_id}')" class="btn btn-primary btn-sm" style="display:inline-flex; align-items:center; gap:0.3rem; font-weight:700; background:#0284c7;">
                              💬 ${a.is_ai_doctor ? 'Chat with AI Doctor' : 'Open Doctor Chat'}
                            </button>
                            <button onclick="Appointments.cancelAppointment('${a.appointment_id}')" class="btn btn-outline btn-sm" style="color:var(--danger); border-color:var(--danger-light);">
                              Cancel
                            </button>
                          ` : (a.status === 'COMPLETED' ? `
                            <button onclick="Appointments.openChatModal('${a.appointment_id}', true)" class="btn btn-outline btn-sm">
                              💬 View Chat
                            </button>
                          ` : (a.status === 'BOOKED' || a.status === 'PENDING' ? `
                            <span class="badge badge-pending" style="display:inline-flex; align-items:center; gap:0.3rem; padding:0.4rem 0.65rem; font-size:0.78rem;">
                              ⏳ Awaiting Doctor Acceptance
                            </span>
                            <button onclick="Appointments.cancelAppointment('${a.appointment_id}')" class="btn btn-outline btn-sm" style="color:var(--danger); border-color:var(--danger-light);">
                              Cancel
                            </button>
                          ` : `<span style="font-size:0.8rem; color:var(--slate-400);">-</span>`))}
                        </div>
                      </td>
                    </tr>
                  `;
                }).join("")}
              </tbody>
            </table>
          </div>
        `;
      } else {
        container.innerHTML = `<p style="color:var(--slate-400); text-align:center; padding:2rem;">No appointments scheduled.</p>`;
      }
    } catch (err) {
      console.error("Failed to load appointments:", err);
    }
  },

  ensureChatModalExists() {
    if (document.getElementById("apt-chat-modal")) return;
    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.id = "apt-chat-modal";
    modal.innerHTML = `
      <div class="modal-card" style="max-width:780px; width:95%; height:84vh; display:flex; flex-direction:column; padding:0; overflow:hidden;">
        <div class="modal-header" style="padding:1rem 1.25rem; border-bottom:1px solid var(--slate-200); background:#f8fafc; margin-bottom:0;">
          <div>
            <h3 class="modal-title" id="apt-chat-title" style="margin:0; font-size:1.1rem; display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
              💬 Consultation Chat
            </h3>
            <p id="apt-chat-subtitle" style="margin:0.2rem 0 0 0; font-size:0.82rem; color:var(--slate-500);">
              Direct clinical consultation chat
            </p>
          </div>
          <button onclick="Appointments.closeChatModal()" class="modal-close" title="Close">&times;</button>
        </div>

        <div id="apt-chat-emergency-banner" class="emergency-banner" style="display:none; margin:0; border-radius:0;">
          🚨 POTENTIAL EMERGENCY DETECTED: PLEASE CALL EMERGENCY SERVICES (112 / 911) OR VISIT AN EMERGENCY ROOM IMMEDIATELY.
        </div>

        <div id="apt-chat-messages" style="flex:1; overflow-y:auto; padding:1.25rem; background:#ffffff; display:flex; flex-direction:column; gap:0.85rem;">
          <p style="text-align:center; color:var(--slate-400); padding:2rem;">Loading consultation chat...</p>
        </div>

        <div id="apt-chat-chips" style="display:flex; gap:0.45rem; flex-wrap:wrap; padding:0.5rem 1.25rem; background:#f8fafc; border-top:1px solid var(--slate-200);"></div>

        <div id="apt-chat-composer" style="padding:0.85rem 1.25rem; border-top:1px solid var(--slate-200); background:#f8fafc; display:flex; gap:0.65rem; align-items:center;">
          <input type="text" id="apt-chat-input" class="form-control" placeholder="Type your symptoms, medicines, or questions..." style="flex:1;" autocomplete="off">
          <button type="button" id="apt-chat-send-btn" onclick="Appointments.sendChatMessage()" class="btn btn-primary" style="white-space:nowrap;">
            Send
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const input = document.getElementById("apt-chat-input");
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          Appointments.sendChatMessage();
        }
      });
    }
  },

  formatMessageHtml(rawText) {
    if (!rawText) return "";
    if (typeof HealthChat !== "undefined" && typeof HealthChat.formatDoctorMessage === "function") {
      return HealthChat.formatDoctorMessage(rawText);
    }
    let processed = rawText;
    const tableRegex = /(\|[^\n]+\|\r?\n\|[-:\s|]+\|\r?\n(?:\|[^\n]+\|\r?\n?)+)/g;
    processed = processed.replace(tableRegex, (match) => {
      const lines = match.trim().split(/\r?\n/).filter(l => l.trim().startsWith("|") && l.trim().endsWith("|"));
      if (lines.length < 3) return match;
      const parseCells = (line) => line.split("|").slice(1, -1).map(c => c.trim());
      const headers = parseCells(lines[0]);
      const dataRows = lines.slice(2).map(parseCells);
      const thHtml = headers.map(h => `<th style="padding:0.5rem 0.65rem; text-align:left; font-weight:700; border-bottom:2px solid #bae6fd; font-size:0.83rem;">${h.replace(/\*\*(.*?)\*\*/g, "$1")}</th>`).join("");
      const trHtml = dataRows.map((row, idx) => {
        const bg = idx % 2 === 0 ? "#ffffff" : "#f8fafc";
        const tdHtml = row.map(cell => `<td style="padding:0.5rem 0.65rem; border-bottom:1px solid #e2e8f0; font-size:0.82rem; color:#1e293b;">${cell.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")}</td>`).join("");
        return `<tr style="background:${bg};">${tdHtml}</tr>`;
      }).join("");
      return `
        <div class="prescription-box-card" style="margin:0.85rem 0; background:#f0f9ff; border:2px solid #0284c7; border-radius:10px; overflow:hidden; box-shadow:0 4px 14px rgba(2,132,199,0.12);">
          <div style="background:linear-gradient(135deg, #0284c7, #0369a1); color:#fff; padding:0.55rem 0.85rem; display:flex; justify-content:space-between; align-items:center; font-weight:700; font-size:0.88rem;">
            <span>🩺 Prescription Box (Rx)</span>
            <span style="background:rgba(255,255,255,0.25); font-size:0.75rem; padding:0.15rem 0.5rem; border-radius:4px; font-weight:600;">Safe Supportive Care</span>
          </div>
          <div style="overflow-x:auto; padding:0.25rem;">
            <table style="width:100%; border-collapse:collapse; min-width:460px;">
              <thead><tr style="background:#e0f2fe; color:#0369a1;">${thHtml}</tr></thead>
              <tbody>${trHtml}</tbody>
            </table>
          </div>
        </div>
      `;
    });
    processed = processed
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/(?:^|\n)[*•]\s+([^\n]+)/g, "<br>• $1")
      .replace(/\n\n+/g, "<br><br>")
      .replace(/\n/g, "<br>");
    return processed;
  },

  appendChatBubble(senderRole, text, disclaimer = "", learnedMemory = null, isPersisted = false) {
    const container = document.getElementById("apt-chat-messages");
    if (!container) return;

    const currentUser = typeof Auth !== "undefined" ? Auth.getUser() : null;
    const isDoctorViewer = currentUser && currentUser.role === "DOCTOR";
    const isSelf = isDoctorViewer ? (senderRole === "DOCTOR" || senderRole === "AI_ASSISTANT") : (senderRole === "PATIENT");

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-msg ${isSelf ? "patient" : "ai"}`;

    const avatarText = isSelf ? (isDoctorViewer ? "Dr." : "ME") : (isDoctorViewer ? "PT" : "Dr.");
    const avatarClass = isSelf ? "avatar-patient" : "avatar-ai";

    let memoryBadgeHtml = "";
    if (learnedMemory && (learnedMemory.allergies?.length || learnedMemory.conditions?.length)) {
      const items = [
        ...(learnedMemory.allergies || []).map(a => `Allergy: ${a}`),
        ...(learnedMemory.conditions || []).map(c => `Condition: ${c}`)
      ].join(", ");
      memoryBadgeHtml = `
        <div style="margin-top:0.6rem; padding:0.4rem 0.75rem; background:#ecfdf5; border:1px solid #a7f3d0; border-radius:6px; font-size:0.82rem; color:#065f46; display:flex; align-items:center; gap:0.4rem;">
          <span>🧠</span>
          <span><strong>Clinical Memory Saved:</strong> ${items}${isPersisted ? " (Synced to Patient Profile)" : ""}</span>
        </div>
      `;
    }

    msgDiv.innerHTML = `
      <div class="chat-avatar ${avatarClass}">${avatarText}</div>
      <div class="chat-bubble">
        <div>${this.formatMessageHtml(text)}</div>
        ${memoryBadgeHtml}
        ${disclaimer ? `<div class="chat-disclaimer">ℹ️ ${disclaimer}</div>` : ""}
      </div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  },

  renderChatChips(questions) {
    const chipsBox = document.getElementById("apt-chat-chips");
    if (!chipsBox) return;
    if (!questions || questions.length === 0) {
      chipsBox.innerHTML = "";
      chipsBox.style.display = "none";
      return;
    }
    chipsBox.style.display = "flex";
    chipsBox.innerHTML = questions.map(q => {
      const safeQ = q.replace(/'/g, "\\'");
      return `<button type="button" onclick="Appointments.sendChatMessage('${safeQ}')" class="quick-chip">👉 ${q}</button>`;
    }).join("");
  },

  async openChatModal(aptId, readOnly = false) {
    this.ensureChatModalExists();
    this.activeChatAptId = aptId;

    const modal = document.getElementById("apt-chat-modal");
    const titleEl = document.getElementById("apt-chat-title");
    const subEl = document.getElementById("apt-chat-subtitle");
    const msgBox = document.getElementById("apt-chat-messages");
    const composer = document.getElementById("apt-chat-composer");
    const emergencyBanner = document.getElementById("apt-chat-emergency-banner");

    if (emergencyBanner) emergencyBanner.style.display = "none";
    this.renderChatChips([]);
    if (composer) composer.style.display = readOnly ? "none" : "flex";
    if (msgBox) msgBox.innerHTML = `<p style="text-align:center; color:var(--slate-400); padding:2rem;">Loading consultation chat...</p>`;
    if (modal) modal.classList.add("active");

    try {
      const res = await Auth.fetchWithAuth(`/api/appointments/${aptId}/chat`);
      if (!res) return;
      const data = await res.json();

      if (!data.success) {
        if (msgBox) msgBox.innerHTML = `<div class="alert alert-danger">${data.error || "Could not load consultation chat."}</div>`;
        return;
      }

      this.activeChatIsAiDoctor = Boolean(data.is_ai_doctor);
      this.activeChatDoctorName = data.doctor?.full_name || "Doctor";

      const currentUser = typeof Auth !== "undefined" ? Auth.getUser() : null;
      const isDoctorViewer = currentUser && currentUser.role === "DOCTOR";

      if (titleEl) {
        const badgeHtml = this.activeChatIsAiDoctor
          ? `<span class="badge badge-verified" style="background:#e0f2fe; color:#0369a1; border:1px solid #bae6fd; font-size:0.75rem;">🤖 AI Clinical Specialist Connected</span>`
          : `<span class="badge badge-verified" style="font-size:0.75rem;">✓ Verified Doctor</span>`;
        titleEl.innerHTML = isDoctorViewer
          ? `💬 Chat with ${data.patient_name || "Patient"}`
          : `💬 Chat with ${this.activeChatDoctorName} ${badgeHtml}`;
      }
      if (subEl && data.appointment) {
        subEl.innerText = `${data.doctor?.specialty || "Consultation"} • ${data.appointment.appointment_date} at ${data.appointment.slot_time} • Status: ${data.appointment.status}`;
      }

      if (msgBox) msgBox.innerHTML = "";
      (data.messages || []).forEach(m => {
        this.appendChatBubble(m.sender_type, m.message_text, m.disclaimer_note || "");
      });

      if (!readOnly && !isDoctorViewer && this.activeChatIsAiDoctor) {
        if ((data.messages || []).length <= 1) {
          this.renderChatChips(["I have chest discomfort", "Acidity & bloating", "Headache & mild fever"]);
        }
      }
    } catch (err) {
      if (msgBox) msgBox.innerHTML = `<div class="alert alert-danger">Error loading chat: ${err.message}</div>`;
    }
  },

  closeChatModal() {
    const modal = document.getElementById("apt-chat-modal");
    if (modal) modal.classList.remove("active");
  },

  async sendChatMessage(customText = null) {
    if (!this.activeChatAptId) return;
    const input = document.getElementById("apt-chat-input");
    const sendBtn = document.getElementById("apt-chat-send-btn");
    const msgBox = document.getElementById("apt-chat-messages");
    const text = (customText || (input ? input.value : "")).trim();
    if (!text) return;

    if (input && !customText) input.value = "";
    if (sendBtn) sendBtn.disabled = true;

    const currentUser = typeof Auth !== "undefined" ? Auth.getUser() : null;
    const isDoctorViewer = currentUser && currentUser.role === "DOCTOR";
    this.appendChatBubble(isDoctorViewer ? "DOCTOR" : "PATIENT", text);

    let typingEl = null;
    if (!isDoctorViewer && this.activeChatIsAiDoctor && msgBox) {
      typingEl = document.createElement("div");
      typingEl.className = "chat-msg ai";
      typingEl.innerHTML = `
        <div class="chat-avatar avatar-ai">Dr.</div>
        <div class="chat-bubble" style="color:var(--slate-500); font-style:italic; display:flex; align-items:center; gap:0.5rem;">
          <span class="loading-spinner" style="width:14px; height:14px; border:2px solid #cbd5e1; border-top-color:#0284c7; border-radius:50%; animation:spin 0.8s linear infinite;"></span>
          ${this.activeChatDoctorName} (AI) is preparing your clinical advice...
        </div>
      `;
      msgBox.appendChild(typingEl);
      msgBox.scrollTop = msgBox.scrollHeight;
    }

    try {
      const res = await Auth.fetchWithAuth(`/api/appointments/${this.activeChatAptId}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: text })
      });
      if (typingEl) typingEl.remove();
      if (!res) return;
      const data = await res.json();

      if (data.success) {
        if (data.ai_replied && data.reply) {
          this.appendChatBubble(
            "DOCTOR",
            data.reply,
            data.disclaimer || "",
            data.learned_memory,
            data.profile_memory_updated
          );
          if (data.red_flag_alert) {
            const emergencyBanner = document.getElementById("apt-chat-emergency-banner");
            if (emergencyBanner) emergencyBanner.style.display = "block";
          }
          if (data.follow_up_questions && data.follow_up_questions.length > 0) {
            this.renderChatChips(data.follow_up_questions);
          }
        } else if (!isDoctorViewer && data.message) {
          this.appendChatBubble("SYSTEM", data.message);
        }
      } else {
        this.appendChatBubble("SYSTEM", "Could not send message: " + (data.error || "Please try again."));
      }
    } catch (err) {
      if (typingEl) typingEl.remove();
      this.appendChatBubble("SYSTEM", "Network error: " + err.message);
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (input) input.focus();
    }
  },

  async cancelAppointment(aptId) {
    if (!confirm("Are you sure you want to cancel this appointment?")) return;

    try {
      const res = await Auth.fetchWithAuth(`/api/appointments/${aptId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: "CANCELLED" })
      });
      if (!res) return;
      const data = await res.json();
      if (data.success) {
        alert("Appointment cancelled.");
        this.loadMyAppointments();
      }
    } catch (err) {
      alert("Error: " + err.message);
    }
  }
};
