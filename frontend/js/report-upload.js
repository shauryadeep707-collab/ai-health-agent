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

    const testTypeSelect = document.getElementById("report-test-type");
    const testType = testTypeSelect ? testTypeSelect.value.trim() : "";
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

    const analysis = data.ai_analysis || {};
    const reportTitle = data.test_type || "Diagnostic Investigation";
    const reportDate = data.report_date ? data.report_date.split('T')[0] : "Not Specified";
    const summaryText = analysis.summary_plain_en || "Medical report processed successfully.";

    container.innerHTML = `
      <div class="panel" style="border-top: 4px solid var(--primary); box-shadow:0 4px 18px rgba(0,0,0,0.08); margin-top:1.5rem;">
        <div class="panel-header" style="flex-wrap:wrap; gap:1rem; align-items:flex-start;">
          <div>
            <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; margin-bottom:0.35rem;">
              <span class="badge" style="background:#e0f2fe; color:#0284c7; font-weight:700; font-size:0.85rem; border:1px solid #bae6fd;">
                🔬 ${reportTitle}
              </span>
              ${reportDate && reportDate !== 'Not Specified' ? `
                <span class="badge" style="background:#f1f5f9; color:#475569; font-weight:600; font-size:0.8rem;">
                  🗓️ Test Date: ${reportDate}
                </span>
              ` : ''}
              <span class="badge" style="background:#f0fdf4; color:#16a34a; font-weight:700; font-size:0.8rem; border:1px solid #bbf7d0;">
                ✓ AI Analyzed
              </span>
            </div>
            <h3 class="panel-title" style="font-size:1.35rem; font-weight:800; color:var(--dark); margin:0.35rem 0;">
              ${reportTitle}
            </h3>
            <div style="font-size:0.85rem; color:var(--slate-500);">
              📄 <em>Uploaded File:</em> ${data.original_filename}
            </div>
          </div>
          <div>
            ${data.report_id ? `
              <button onclick="ReportUpload.openOriginalFile('${data.report_id}')" class="btn btn-primary" style="display:inline-flex; align-items:center; gap:0.4rem; padding:0.6rem 1.2rem; font-weight:700;">
                👁️ View Uploaded Report
              </button>
            ` : ''}
          </div>
        </div>

        <!-- 3 Extracted Auto-Fill Fields Display Card -->
        <div style="background:#ffffff; border:1px solid var(--slate-200); border-radius:10px; padding:1.25rem; margin-top:1rem;">
          <h4 style="font-size:1.05rem; font-weight:800; color:var(--dark); margin-bottom:1rem; display:flex; align-items:center; gap:0.4rem;">
            📋 Extracted Report Details
          </h4>
          
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:1rem; margin-bottom:1.25rem;">
            <div style="background:#f8fafc; padding:0.85rem 1rem; border-radius:8px; border:1px solid #e2e8f0;">
              <span style="font-size:0.78rem; text-transform:uppercase; font-weight:700; color:var(--slate-500); display:block; margin-bottom:0.25rem;">
                1. Report Konsi Wali Hai (Test Name)
              </span>
              <strong style="color:var(--dark); font-size:1.05rem;">${reportTitle}</strong>
            </div>

            <div style="background:#f8fafc; padding:0.85rem 1rem; border-radius:8px; border:1px solid #e2e8f0;">
              <span style="font-size:0.78rem; text-transform:uppercase; font-weight:700; color:var(--slate-500); display:block; margin-bottom:0.25rem;">
                2. Date of Test (Test Date)
              </span>
              <strong style="color:var(--dark); font-size:1.05rem;">${reportDate}</strong>
            </div>
          </div>

          <div style="background:#eff6ff; padding:1.1rem; border-radius:8px; border:1px solid #bfdbfe;">
            <span style="font-size:0.8rem; text-transform:uppercase; font-weight:800; color:#1e40af; display:block; margin-bottom:0.35rem;">
              3. Summary (Clinical Findings & Condition)
            </span>
            <p style="margin:0; font-size:0.95rem; line-height:1.6; color:#1e3a8a; font-weight:500;">
              ${summaryText}
            </p>
          </div>
        </div>

        <div style="margin-top:1.25rem; text-align:right;">
          ${data.report_id ? `
            <button onclick="ReportUpload.openOriginalFile('${data.report_id}')" class="btn btn-outline" style="display:inline-flex; align-items:center; gap:0.35rem;">
              🔍 Open Full Document Viewer
            </button>
          ` : ''}
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

  async loadHistory(sortBy = null) {
    const listContainer = document.getElementById("reports-history-list");
    if (!listContainer) return;

    if (!sortBy) {
      const selectEl = document.getElementById("reports-sort-select");
      sortBy = selectEl ? selectEl.value : "date_desc";
    }

    listContainer.innerHTML = `<p style="color:var(--slate-500); padding:1rem 0;">⏳ Loading provided medical reports...</p>`;

    try {
      const res = await Auth.fetchWithAuth(`/api/patient/reports?sort=${encodeURIComponent(sortBy)}`);
      if (!res) return;
      const data = await res.json();

      if (data.success && data.reports && data.reports.length > 0) {
        listContainer.innerHTML = data.reports.map(r => {
          const testDateDisplay = r.report_date ? r.report_date.split('T')[0] : 'Not specified';
          const reportTitle = r.test_type || "Diagnostic Lab Report";
          const summaryDisplay = r.summary_plain_en || "Medical report uploaded and cataloged.";

          return `
          <div class="panel" style="margin-bottom:1.25rem; padding:1.25rem; border-left:4px solid var(--primary); box-shadow:0 2px 10px rgba(0,0,0,0.04);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1rem;">
              <div style="flex:1; min-width:260px;">
                <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem; flex-wrap:wrap;">
                  <span class="badge" style="background:#e0f2fe; color:#0284c7; font-weight:700; font-size:0.85rem; border:1px solid #bae6fd;">
                    🔬 ${reportTitle}
                  </span>
                  ${testDateDisplay && testDateDisplay !== 'Not specified' ? `
                    <span class="badge" style="background:#f1f5f9; color:#475569; font-weight:600; font-size:0.8rem;">
                      🗓️ Test Date: ${testDateDisplay}
                    </span>
                  ` : ''}
                </div>

                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:0.85rem 1rem; margin:0.75rem 0;">
                  <div style="font-size:0.78rem; text-transform:uppercase; font-weight:700; color:var(--slate-500); margin-bottom:0.25rem;">
                    📋 Summary:
                  </div>
                  <div style="font-size:0.92rem; color:var(--slate-700); line-height:1.5;">
                    ${summaryDisplay.replace(/\n\n/g, '<br><br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}
                  </div>
                </div>

                <div style="font-size:0.82rem; color:var(--slate-400);">
                  📄 <em>Source File:</em> ${r.original_filename}
                </div>
              </div>

              <div>
                <button onclick="ReportUpload.openOriginalFile('${r.report_id}')" class="btn btn-primary" style="display:inline-flex; align-items:center; gap:0.4rem; padding:0.55rem 1.1rem; font-weight:700;">
                  👁️ View Uploaded Report
                </button>
              </div>
            </div>
          </div>
        `;
        }).join("");
      } else {
        listContainer.innerHTML = `
          <div style="text-align:center; padding:2.5rem 1rem; background:#f8fafc; border-radius:8px; border:1px dashed #cbd5e1;">
            <div style="font-size:2rem; margin-bottom:0.5rem;">📁</div>
            <h4 style="color:var(--dark); margin-bottom:0.25rem;">No Medical Reports Provided Yet</h4>
            <p style="color:var(--slate-500); font-size:0.9rem; max-width:400px; margin:0 auto 1rem;">
              Upload your blood test or diagnostic report above. It will be analyzed and cataloged here by test date.
            </p>
          </div>
        `;
      }
    } catch (err) {
      console.error("Failed to load report history:", err);
      listContainer.innerHTML = `<div class="alert alert-danger">Error loading reports: ${err.message}</div>`;
    }
  },

  discussWithAI(testName, testDate) {
    if (typeof switchTab === "function") {
      switchTab("ai-assistant");
    }
    const input = document.getElementById("chat-user-input");
    if (input) {
      input.value = `Can you explain the findings of my ${testName} dated ${testDate}?`;
      input.focus();
    }
  },

  async viewReportDetail(reportId) {
    try {
      const res = await Auth.fetchWithAuth(`/api/patient/reports/${reportId}`);
      if (!res) return;
      const data = await res.json();
      if (data.success && data.report) {
        this.renderAnalysisResult({
          report_id: data.report.report_id,
          original_filename: data.report.original_filename,
          test_type: data.report.test_type,
          report_date: data.report.report_date,
          test_values: data.test_values,
          ai_analysis: data.analysis,
          ocr_raw_text: data.report.ocr_raw_text
        });
        window.scrollTo({ top: 300, behavior: 'smooth' });
      }
    } catch (err) {
      alert("Error loading report: " + err.message);
    }
  },

  async openOriginalFile(reportId) {
    if (!reportId) return;
    const modal = document.getElementById("report-file-viewer-modal");
    const content = document.getElementById("report-file-viewer-content");
    const titleEl = document.getElementById("report-file-viewer-title");
    const downloadLink = document.getElementById("report-file-download-btn");

    const token = localStorage.getItem("token") || "";
    const fileUrl = `/api/patient/reports/${reportId}/file?token=${encodeURIComponent(token)}`;

    if (!modal || !content) {
      window.open(fileUrl, "_blank");
      return;
    }

    content.innerHTML = `
      <div style="text-align:center; padding:3.5rem 1rem;">
        <div class="spinner" style="margin:0 auto 1rem;"></div>
        <p style="color:var(--slate-600); font-size:1rem; font-weight:600;">Loading original hospital document...</p>
      </div>
    `;
    modal.classList.add("active");

    if (downloadLink) {
      downloadLink.href = fileUrl;
      downloadLink.target = "_blank";
    }

    try {
      const metaRes = await Auth.fetchWithAuth(`/api/patient/reports/${reportId}`);
      let reportName = "Medical Report";
      let isPdf = false;
      if (metaRes) {
        const metaData = await metaRes.json();
        if (metaData && metaData.report) {
          reportName = metaData.report.test_type || metaData.report.original_filename;
          const fn = (metaData.report.original_filename || "").toLowerCase();
          const ft = (metaData.report.file_type || "").toLowerCase();
          isPdf = fn.endsWith(".pdf") || ft.includes("pdf");
        }
      }
      if (titleEl) titleEl.innerText = `📄 ${reportName}`;

      if (isPdf) {
        content.innerHTML = `
          <div style="width:100%; height:75vh; border-radius:8px; overflow:hidden; border:1px solid var(--slate-200);">
            <iframe src="${fileUrl}" style="width:100%; height:100%; border:none;"></iframe>
          </div>
        `;
      } else {
        content.innerHTML = `
          <div style="text-align:center; background:#0b1120; border-radius:12px; padding:1.25rem; max-height:76vh; overflow:auto; display:flex; justify-content:center; align-items:center;">
            <img src="${fileUrl}" alt="Original Lab Report" style="max-width:100%; max-height:72vh; object-fit:contain; border-radius:8px; box-shadow:0 8px 30px rgba(0,0,0,0.6);" />
          </div>
        `;
      }
    } catch (err) {
      content.innerHTML = `
        <div class="alert alert-danger" style="margin:2rem 0;">
          Failed to load preview: ${err.message}. 
          <a href="${fileUrl}" target="_blank" class="btn btn-outline btn-sm" style="margin-left:1rem;">Open in New Tab</a>
        </div>
      `;
    }
  },

  closeFileViewer() {
    const modal = document.getElementById("report-file-viewer-modal");
    if (modal) modal.classList.remove("active");
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
