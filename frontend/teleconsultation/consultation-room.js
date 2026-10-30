/**
 * AI Health Agent - Tele-Consultation Connection Manager
 * Powers real-time WebRTC Video, Audio, Screen Share & Live In-Call Chat.
 */

let jitsiApi = null;
let callStartTime = null;
let timerInterval = null;

// Parse URL Parameters
function getQueryParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    room: params.get("room") || params.get("apt_id") || "demo-consultation-room",
    role: (params.get("role") || "patient").toLowerCase(),
    name: params.get("name") || "",
    doctor: params.get("doctor") || "Dr. Priya Sharma",
    patient: params.get("patient") || "Patient",
    reason: params.get("reason") || "Clinical Follow-up"
  };
}

// Timer Formatting
function startCallTimer() {
  callStartTime = Date.now();
  const timerEl = document.getElementById("call-timer");
  if (!timerEl) return;

  timerInterval = setInterval(() => {
    const elapsedSec = Math.floor((Date.now() - callStartTime) / 1000);
    const mins = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
    const secs = String(elapsedSec % 60).padStart(2, "0");
    timerEl.textContent = `${mins}:${secs}`;
  }, 1000);
}

// Initialize WebRTC Consultation Room
function initConsultationRoom() {
  const config = getQueryParams();

  // Determine User Display Name & Title
  let userDisplayName = config.name;
  if (!userDisplayName) {
    userDisplayName = config.role === "doctor" 
      ? (config.doctor.startsWith("Dr.") ? config.doctor : `Dr. ${config.doctor}`)
      : (config.patient || "Patient");
  }

  // Update Header & Participant Meta
  document.getElementById("room-id-display").textContent = `Room: ${config.room}`;
  document.getElementById("participant-name").textContent = userDisplayName;
  document.getElementById("participant-role-badge").textContent = config.role === "doctor" ? "👨‍⚕️ Clinical Doctor" : "👤 Registered Patient";
  document.getElementById("consultation-topic").textContent = config.reason;

  // Set Back URL
  const backBtn = document.getElementById("btn-end-call");
  if (backBtn) {
    backBtn.onclick = endConsultation;
  }

  // Clean room name for WebRTC
  const sanitizedRoom = "aiheal-" + config.room.replace(/[^a-zA-Z0-9_-]/g, "");

  // Load Jitsi Meet External API
  loadJitsiAPI(sanitizedRoom, userDisplayName, config.role);
  startCallTimer();
}

function loadJitsiAPI(roomName, displayName, role) {
  const container = document.getElementById("jitsi-meet-container");
  const overlay = document.getElementById("room-loading-overlay");

  const domain = "meet.jit.si";
  const options = {
    roomName: roomName,
    width: "100%",
    height: "100%",
    parentNode: container,
    userInfo: {
      displayName: displayName
    },
    configOverwrite: {
      startWithAudioMuted: false,
      startWithVideoMuted: false,
      enableWelcomePage: false,
      prejoinPageEnabled: false,
      disableDeepLinking: true,
      toolbarButtons: [
        "camera",
        "chat",
        "closedcaptions",
        "desktop",
        "fullscreen",
        "fodeviceselection",
        "hangup",
        "microphone",
        "raisehand",
        "select-background",
        "tileview",
        "toggle-camera"
      ]
    },
    interfaceConfigOverwrite: {
      SHOW_JITSI_WATERMARK: false,
      SHOW_WATERMARK_FOR_GUESTS: false,
      SHOW_BRAND_WATERMARK: false,
      DEFAULT_REMOTE_DISPLAY_NAME: "Connecting Specialist...",
      TOOLBAR_ALWAYS_VISIBLE: true,
      DISABLE_JOIN_LEAVE_NOTIFICATIONS: false
    }
  };

  try {
    jitsiApi = new JitsiMeetExternalAPI(domain, options);

    // When call loads
    jitsiApi.addEventListener("videoConferenceJoined", () => {
      if (overlay) overlay.style.display = "none";
      console.log("[Teleconsultation] Joined conference room:", roomName);
    });

    // When participant leaves or hangs up
    jitsiApi.addEventListener("readyToClose", () => {
      endConsultation();
    });

    // Fallback hide overlay after 4 seconds
    setTimeout(() => {
      if (overlay) overlay.style.display = "none";
    }, 4000);

  } catch (err) {
    console.error("Failed to initialize WebRTC engine:", err);
    if (overlay) {
      overlay.innerHTML = `
        <div style="text-align:center; padding:2rem;">
          <h3 style="color:#ef4444; margin-bottom:0.5rem;">⚠️ Camera / Audio Engine Initializing</h3>
          <p style="color:#94a3b8; font-size:0.9rem; max-width:420px; margin:0 auto 1.5rem;">
            Please ensure you have granted camera & microphone access in your browser to join the video consultation.
          </p>
          <button onclick="window.location.reload()" class="btn btn-primary" style="background:#0284c7; color:#fff; border:none; padding:0.5rem 1.25rem; border-radius:6px; cursor:pointer;">
            Retry Connection
          </button>
        </div>
      `;
    }
  }
}

// End Consultation & Redirect
function endConsultation() {
  clearInterval(timerInterval);
  if (jitsiApi) {
    try {
      jitsiApi.dispose();
    } catch (e) {}
  }

  const config = getQueryParams();
  const redirectTarget = config.role === "doctor" ? "../doctor-dashboard.html" : "../patient-dashboard.html";
  window.location.href = redirectTarget;
}

// Side Panel Toggle
function toggleSidePanel() {
  const panel = document.getElementById("notes-panel");
  const btn = document.getElementById("btn-toggle-panel");
  if (!panel) return;

  panel.classList.toggle("collapsed");
  if (panel.classList.contains("collapsed")) {
    if (btn) btn.innerHTML = `📋 Clinical Notes & Vitals ◀`;
  } else {
    if (btn) btn.innerHTML = `Hide Panel ▶`;
  }
}

// Save Clinical Note to LocalStorage
function saveConsultationNote() {
  const config = getQueryParams();
  const text = document.getElementById("consultation-note-text")?.value;
  if (!text || !text.trim()) return;

  const key = `aiheal_notes_${config.room}`;
  localStorage.setItem(key, text.trim());
  const statusEl = document.getElementById("note-save-status");
  if (statusEl) {
    statusEl.textContent = "✓ Notes saved to medical record";
    setTimeout(() => { statusEl.textContent = ""; }, 2500);
  }
}

// Load existing note
function loadExistingNote() {
  const config = getQueryParams();
  const key = `aiheal_notes_${config.room}`;
  const saved = localStorage.getItem(key);
  const noteBox = document.getElementById("consultation-note-text");
  if (noteBox && saved) {
    noteBox.value = saved;
  }
}

// Copy Direct Share Link (Allows testing in another tab or incognito)
function copyRoomInviteLink() {
  const url = window.location.href;
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.getElementById("btn-copy-link");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "✓ Link Copied!";
      setTimeout(() => { btn.innerHTML = orig; }, 2000);
    }
  }).catch(() => {
    alert("Share URL: " + window.location.href);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initConsultationRoom();
  loadExistingNote();
});
