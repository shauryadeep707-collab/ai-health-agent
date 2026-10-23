/* =============================================================================
   AI HEALTH AGENT — MEDICAL REPORT UPLOAD & ANALYSIS (report-upload.js)
   ============================================================================= */

const ReportUpload = {
  selectedFile: null,

  initDropzone(dropzoneId, fileInputId) {
    const dropzone = document.getElementById(dropzoneId);
    const fileInput = document.getElementById(fileInputId);
    if (!dropzone || !fileInput) return;

    dropzone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        this.handleFileSelected(e.target.files[0]);
      }
    });

    ["dragenter", "dragover"].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length > 0) {
        this.handleFileSelected(e.dataTransfer.files[0]);
      }
    });
  },

  handleFileSelected(file) {
    this.selectedFile = file;
    const previewEl = document.getElementById("file-selected-preview");
    if (previewEl) {
      previewEl.innerHTML = `
        <div class="alert alert-info" style="margin-top:1rem;">
          📄 Selected file: <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)
        </div>
      `;
    }
  },

  async submitUpload(event) {
    if (event) event.preventDefault();
    if (!this.selectedFile) {
      alert("Please select a medical report file (PDF, PNG, JPG).");
      return;
    }

    const testType = document.getElementById("report-test-type")?.value || "General Lab Report";
    const reportDate = document.getElementById("report-test-date")?.value || "";

    const formData = new FormData();
    formData.append("file", this.selectedFile);
    formData.append("test_type", testType);
    if (reportDate) formData.append("report_date", reportDate);

    const btn = document.getElementById("upload-submit-btn");
    const originalText = btn ? btn.innerText : "";
    if (btn) {
      btn.innerText = "Analyzing Report with AI...";
      btn.disabled = true;
    }

    try {
      const res = await Auth.fetchWithAuth("/api/patient/reports/upload", {
        method: "POST",
        body: formData
      });
      if (!res) return;
      const data = await res.json();

      if (data.success) {
        this.renderAnalysisResult(data);
        this.loadHistory();
      } else {
        alert(data.error || "Failed to process report.");
      }
    } catch (err) {
      alert("Upload error: " + err.message);
    } finally {
      if (btn) {
        btn.innerText = originalText;
        btn.disabled = false;
      }
    }
  },

  renderAnalysisResult(data) {
    const container = document.getElementById("analysis-result-container");
    if (!container) return;

    const values = data.test_values || [];
    const analysis = data.ai_analysis || {};

    let tableRows = values.map(v => {
      let badgeClass = "badge-verified";
      if (v.flag === "HIGH") badgeClass = "badge-rejected";
      if (v.flag === "LOW") badgeClass = "badge-pending";
      if (v.flag === "CRITICAL") badgeClass = "badge-rejected";

      return `
        <tr>
          <td><strong>${v.parameter_name}</strong></td>
          <td><strong>${v.measured_value}</strong> ${v.unit}</td>
          <td>${v.ref_range_text || '-'}</td>
          <td><span class="badge ${badgeClass}">${v.flag}</span></td>
        </tr>
      `;
    }).join("");

    container.innerHTML = `
      <div class="panel" style="border-top: 4px solid var(--primary);">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">🔬 Extracted Findings: ${data.original_filename}</h3>
            <span style="font-size:0.85rem; color:var(--slate-400);">AI Provider: ${analysis.ai_provider}</span>
          </div>
          <button onclick="ReportUpload.confirmReport('${data.report_id}')" id="confirm-btn-${data.report_id}" class="btn btn-secondary btn-sm">
            ✅ Confirm Extracted Facts
          </button>
        </div>

        <div class="table-responsive" style="margin-bottom:1.5rem;">
          <table class="data-table">
            <thead>
              <tr>
                <th>Parameter Name</th>
                <th>Measured Value</th>
                <th>Standard Reference Interval</th>
                <th>Status Flag</th>
              </tr>
            </thead>
            <tbody>
              ${tableRows || '<tr><td colspan="4">No specific parameters isolated.</td></tr>'}
            </tbody>
          </table>
        </div>

        <div style="background-color:var(--slate-100); border-radius:var(--radius-md); padding:1.25rem; margin-bottom:1.25rem;">
          <h4 style="font-size:1.05rem; font-weight:700; color:var(--dark); margin-bottom:0.5rem;">
            🤖 AI Plain English Explanation
          </h4>
          <p style="white-space:pre-line; line-height:1.6; font-size:0.95rem; color:var(--slate-700);">
            ${analysis.summary_plain_en}
          </p>
        </div>

        ${analysis.urgent_flags ? `
          <div class="alert alert-warning" style="margin-bottom:1rem;">
            ⚠️ <strong>Clinical Note:</strong> ${analysis.urgent_flags}
          </div>
        ` : ''}

        <div class="disclaimer-card">
          <div class="disclaimer-title">⚖️ Medical Safety Notice</div>
          <div class="disclaimer-text">
            Abnormal test values do NOT automatically establish a diagnosis. Laboratory metrics must always be evaluated in the clinical context of your physical condition, symptoms, and medical history by a licensed healthcare professional.
          </div>
        </div>
      </div>
    `;

    container.scrollIntoView({ behavior: "smooth" });
  },

  async confirmReport(reportId) {
    try {
      const res = await Auth.fetchWithAuth(`/api/patient/reports/${reportId}/confirm`, { method: "POST" });
      if (!res) return;
      const data = await res.json();
      if (data.success) {
        const btn = document.getElementById(`confirm-btn-${reportId}`);
        if (btn) {
          btn.innerText = "Confirmed ✓";
          btn.disabled = true;
          btn.classList.remove("btn-secondary");
          btn.classList.add("btn-outline");
        }
        alert("Report findings confirmed by patient.");
      }
    } catch (err) {
      alert("Error confirming: " + err.message);
    }
  },

  async loadHistory() {
    const listContainer = document.getElementById("reports-history-list");
    if (!listContainer) return;

    try {
      const res = await Auth.fetchWithAuth("/api/patient/reports");
      if (!res) return;
      const data = await res.json();

      if (data.success && data.reports.length > 0) {
        listContainer.innerHTML = data.reports.map(r => `
          <div class="panel" style="margin-bottom:1rem; padding:1.25rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
              <div>
                <h4 style="font-size:1rem; font-weight:700; color:var(--dark); margin-bottom:0.25rem;">
                  📄 ${r.original_filename}
                </h4>
                <span style="font-size:0.8rem; color:var(--slate-400);">
                  Uploaded on ${r.upload_timestamp.split('T')[0] || r.upload_timestamp} | Test: ${r.test_type || 'General'}
                </span>
              </div>
              <div style="display:flex; align-items:center; gap:0.5rem;">
                <span class="badge ${r.risk_level === 'LOW' ? 'badge-verified' : (r.risk_level === 'MODERATE' ? 'badge-pending' : 'badge-rejected')}">
                  ${r.risk_level || 'ANALYZED'}
                </span>
                <button onclick="ReportUpload.viewReportDetail('${r.report_id}')" class="btn btn-outline btn-sm">
                  View Analysis
                </button>
              </div>
            </div>
          </div>
        `).join("");
      } else {
        listContainer.innerHTML = `<p style="color:var(--slate-400); text-align:center; padding:2rem;">No previous medical reports uploaded.</p>`;
      }
    } catch (err) {
      console.error("Failed to load report history:", err);
    }
  },

  async viewReportDetail(reportId) {
    try {
      const res = await Auth.fetchWithAuth(`/api/patient/reports/${reportId}`);
      if (!res) return;
      const data = await res.json();
      if (data.success) {
        this.renderAnalysisResult({
          report_id: data.report.report_id,
          original_filename: data.report.original_filename,
          test_values: data.test_values,
          ai_analysis: data.analysis
        });
      }
    } catch (err) {
      alert("Error loading report: " + err.message);
    }
  },

  async compareParameter() {
    const paramInput = document.getElementById("compare-param-input");
    const container = document.getElementById("comparison-results");
    if (!paramInput || !container) return;

    const param = paramInput.value.trim();
    if (!param) {
      alert("Please enter a parameter name (e.g. 'Total Cholesterol' or 'Hemoglobin').");
      return;
    }

    try {
      const res = await Auth.fetchWithAuth(`/api/patient/reports/compare?parameter=${encodeURIComponent(param)}`);
      if (!res) return;
      const data = await res.json();

      if (data.success && data.data_points.length > 0) {
        container.innerHTML = `
          <h4 style="font-size:1.05rem; font-weight:700; margin:1rem 0 0.5rem;">
            Trend for "${param}":
          </h4>
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Report Date</th>
                  <th>Source Document</th>
                  <th>Measured Value</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${data.data_points.map(pt => `
                  <tr>
                    <td>${pt.report_date || 'Recent'}</td>
                    <td>${pt.original_filename}</td>
                    <td><strong>${pt.measured_value}</strong> ${pt.unit || ''}</td>
                    <td><span class="badge ${pt.flag === 'NORMAL' ? 'badge-verified' : 'badge-rejected'}">${pt.flag}</span></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        `;
      } else {
        container.innerHTML = `<p style="color:var(--slate-400); margin-top:1rem;">No historical records found for parameter "${param}".</p>`;
      }
    } catch (err) {
      alert("Comparison error: " + err.message);
    }
  }
};
