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
                  const displayName = a.doctor_name ? `Dr. ${a.doctor_name}` : (a.patient_name || 'Patient');
                  let badge = "badge-pending";
                  if (a.status === "CONFIRMED") badge = "badge-verified";
                  if (a.status === "CANCELLED") badge = "badge-rejected";
                  if (a.status === "COMPLETED") badge = "badge-verified";

                  return `
                    <tr>
                      <td><strong>${a.appointment_date}</strong><br><small>${a.slot_time}</small></td>
                      <td>${displayName}<br><small style="color:var(--slate-400);">${a.specialty || ''}</small></td>
                      <td>${a.reason_for_visit || 'Routine Consultation'}</td>
                      <td><span class="badge ${badge}">${a.status}</span></td>
                      <td>
                        ${a.status !== 'CANCELLED' && a.status !== 'COMPLETED' ? `
                          <button onclick="Appointments.cancelAppointment('${a.appointment_id}')" class="btn btn-outline btn-sm" style="color:var(--danger); border-color:var(--danger-light);">
                            Cancel
                          </button>
                        ` : `<span style="font-size:0.8rem; color:var(--slate-400);">-</span>`}
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
