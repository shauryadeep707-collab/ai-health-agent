/* =============================================================================
   AI HEALTH AGENT — DIGILOCKER DOCTOR VERIFICATION (doctor-verification.js)
   ============================================================================= */

const DoctorVerification = {
  async initiateDigiLockerFlow(isDemo = false) {
    try {
      const url = `/api/doctor/digilocker/initiate?demo=${isDemo ? "1" : "0"}`;
      const res = await Auth.fetchWithAuth(url, { method: "POST" });
      if (!res) return;
      const data = await res.json();

      if (data.success && data.auth_url) {
        // Redirect to authorization URL (live DigiLocker portal or Sandbox gateway)
        window.location.href = data.auth_url;
      } else {
        alert(data.error || "Failed to initiate DigiLocker verification.");
      }
    } catch (err) {
      alert("Error contacting DigiLocker verification service: " + err.message);
    }
  },

  async triggerSandboxScenario(scenario) {
    try {
      const res = await Auth.fetchWithAuth("/api/doctor/digilocker/sandbox-verify", {
        method: "POST",
        body: JSON.stringify({ scenario })
      });
      if (!res) return;
      const data = await res.json();
      if (data.success) {
        this.loadVerificationStatus();
        this.showModalFeedback(data.scenario_tested, data.verification_result);
      } else {
        alert(data.error || "Verification test failed.");
      }
    } catch (err) {
      alert("Error running simulation: " + err.message);
    }
  },

  async loadVerificationStatus() {
    const container = document.getElementById("verification-status-container");
    if (!container) return;

    try {
      const res = await Auth.fetchWithAuth("/api/doctor/verification/status");
      if (!res) return;
      const data = await res.json();

      if (data.success) {
        this.renderStatusBanner(container, data);
      }
    } catch (err) {
      console.error("Failed to load doctor verification status:", err);
    }
  },

  renderStatusBanner(container, data) {
    const status = data.verification_status || "PENDING";
    const vRec = data.verification_record || {};
    const reg = data.registration_details || {};

    let bannerClass = "banner-pending";
    let badgeClass = "badge-pending";
    let icon = "⏳";
    let statusHeading = "Medical Credential Verification: PENDING";
    let statusDesc = "Your medical registration has not been verified yet. Click 'Verify with DigiLocker' to pull your official council certificate.";

    if (status === "VERIFIED") {
      bannerClass = "banner-verified";
      badgeClass = "badge-verified";
      icon = "✅";
      statusHeading = "DigiLocker Verified Medical Practitioner";
      statusDesc = `Your medical license (#${reg.registration_number}) with the ${reg.registration_council} has been officially authenticated via DigiLocker. Verified doctor privileges are active.`;
    } else if (status === "REVIEW_REQUIRED") {
      bannerClass = "banner-review";
      badgeClass = "badge-review";
      icon = "🔍";
      statusHeading = "Verification Status: REVIEW REQUIRED";
      statusDesc = vRec.review_notes || "A document, council jurisdiction, or name variation requires secondary administrative confirmation. Your credentials remain safe and under review.";
    } else if (status === "REJECTED") {
      bannerClass = "banner-rejected";
      badgeClass = "badge-rejected";
      icon = "❌";
      statusHeading = "Verification Status: REJECTED";
      statusDesc = vRec.rejection_reason || "The credential submitted through DigiLocker failed defined verification checks. Please check your registration details.";
    }

    container.innerHTML = `
      <div class="doc-verify-banner ${bannerClass}">
        <div>
          <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
            <span style="font-size:1.5rem;">${icon}</span>
            <h3 style="font-size:1.25rem; font-weight:700;">${statusHeading}</h3>
            <span class="badge ${badgeClass}">${status}</span>
          </div>
          <p style="font-size:0.95rem; max-width:750px; line-height:1.5;">${statusDesc}</p>
          ${vRec.name_match_score ? `<p style="font-size:0.85rem; margin-top:0.4rem; opacity:0.9;"><strong>Identity Match Score:</strong> ${vRec.name_match_score}% | <strong>Issuer:</strong> ${vRec.issuer_id || 'NMC / DigiLocker Setu'}</p>` : ''}
        </div>
        <div style="display:flex; flex-direction:column; gap:0.5rem; min-width:200px;">
          ${status !== 'VERIFIED' ? `
            <button onclick="DoctorVerification.initiateDigiLockerFlow()" class="btn-digilocker">
              <span class="digilocker-emblem">DL</span> Verify with DigiLocker
            </button>
            <button onclick="DoctorVerification.openSandboxModal()" class="btn btn-outline btn-sm">
              🧪 Test DigiLocker Sandbox
            </button>
            <button onclick="DoctorVerification.requestManualReview()" class="btn btn-outline btn-sm">
              📝 Request Council Review
            </button>
          ` : `
            <div style="text-align:right;">
              <span style="font-size:0.85rem; font-weight:600; color:var(--success);">Verified on ${data.verified_at || 'DigiLocker Gateway'}</span>
            </div>
          `}
        </div>
      </div>
    `;
  },

  async requestManualReview() {
    const notes = prompt("Please provide notes regarding your registration council or credential for administrative review:");
    if (!notes) return;

    try {
      const res = await Auth.fetchWithAuth("/api/doctor/verification/request-review", {
        method: "POST",
        body: JSON.stringify({ notes })
      });
      if (!res) return;
      const data = await res.json();
      if (data.success) {
        alert("Manual review request submitted. Status updated to REVIEW_REQUIRED.");
        this.loadVerificationStatus();
      }
    } catch (err) {
      alert("Error requesting manual review: " + err.message);
    }
  },

  openSandboxModal() {
    const modal = document.getElementById("sandbox-modal");
    if (modal) modal.classList.add("active");
  },

  closeSandboxModal() {
    const modal = document.getElementById("sandbox-modal");
    if (modal) modal.classList.remove("active");
  },

  showModalFeedback(scenario, result) {
    this.closeSandboxModal();
    alert(`Sandbox Simulation Result for [${scenario}]:\nStatus: ${result.status}\nMatch Score: ${result.name_match_score}%\nDetails: ${result.review_notes || result.rejection_reason || 'Verified'}`);
  }
};
