/**
 * TenderAI RAG - Web Single Page Application Logic
 * Master's Dissertation: LLM-Based RAG Assistant for Tender and BOQ Analysis
 */

document.addEventListener('DOMContentLoaded', () => {
  // Global State
  let cachedData = null;
  let activeTab = 'dashboard';

  // DOM Elements
  const navItems = document.querySelectorAll('.nav-item[data-tab]');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const currentTabTitle = document.getElementById('currentTabTitle');
  const currentTabDesc = document.getElementById('currentTabDesc');
  const connectionBadge = document.getElementById('connectionBadge');
  const btnRefreshData = document.getElementById('btnRefreshData');
  const btnClearData = document.getElementById('btnClearData');
  const emptyStateBanner = document.getElementById('emptyStateBanner');
  const btnEmptyUpload = document.getElementById('btnEmptyUpload');

  // Upload Drawer Elements
  const uploadDrawer = document.getElementById('uploadDrawer');
  const btnOpenDrawer = document.getElementById('btnOpenDrawer');
  const btnCloseDrawer = document.getElementById('btnCloseDrawer');
  const numBiddersSelect = document.getElementById('numBiddersSelect');
  const uploadForm = document.getElementById('uploadForm');
  const drawerBiddersContainer = document.getElementById('drawerBiddersContainer');

  // RAG Elements
  const ragQueryInput = document.getElementById('ragQueryInput');
  const btnAskRag = document.getElementById('btnAskRag');
  const ragResponseCard = document.getElementById('ragResponseCard');
  const ragAnswerText = document.getElementById('ragAnswerText');
  const ragSourcesContainer = document.getElementById('ragSourcesContainer');
  const suggestionPills = document.querySelectorAll('.suggestion-pill');

  // Fallback Elements
  const fallbackBidderSelect = document.getElementById('fallbackBidderSelect');
  const fallbackReasonInput = document.getElementById('fallbackReasonInput');
  const btnRunFallback = document.getElementById('btnRunFallback');
  const fallbackResultAlert = document.getElementById('fallbackResultAlert');

  // BOQ Selector
  const boqBidderSelect = document.getElementById('boqBidderSelect');

  // Tab metadata
  const tabMeta = {
    dashboard: {
      title: "Executive Tender & Multi-Bidder Dashboard",
      desc: "Evidence-grounded decision support for procurement and evaluation committees."
    },
    tender: {
      title: "Tender Specification Overview",
      desc: "Verbatim clause extraction, structured tender parameters, and document sections."
    },
    boq: {
      title: "Bill of Quantities (BOQ) Validation & Audit",
      desc: "Itemized rate verification, arithmetic integrity (Qty × Rate = Quoted), and anomaly detection."
    },
    comparison: {
      title: "Bidder Compliance & Comparison Matrix",
      desc: "Side-by-side verification of all vendor submissions against mandatory tender criteria."
    },
    ranking: {
      title: "Multi-Bidder Ranking & Fallback Simulator",
      desc: "QCBS score calculation (80% Tech / 20% Fin), ranking table, and reserve succession planning."
    },
    risk: {
      title: "Contractual & Operational Risk Analysis",
      desc: "Clause-level risk identification, exposure severity, and committee mitigation recommendations."
    },
    rag: {
      title: "Evidence-Grounded RAG Assistant",
      desc: "Interactive question-answering with exact document citations and audit trail validation."
    }
  };

  // ============================================================
  // TAB NAVIGATION
  // ============================================================
  function switchTab(tabId) {
    activeTab = tabId;

    navItems.forEach(item => {
      if (item.getAttribute('data-tab') === tabId) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    tabPanes.forEach(pane => {
      if (pane.id === `tab-${tabId}`) {
        pane.classList.add('active');
      } else {
        pane.classList.remove('active');
      }
    });

    if (tabMeta[tabId]) {
      currentTabTitle.textContent = tabMeta[tabId].title;
      currentTabDesc.textContent = tabMeta[tabId].desc;
    }
  }

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tabId = item.getAttribute('data-tab');
      if (tabId) switchTab(tabId);
    });
  });

  // ============================================================
  // DRAWER TOGGLE & DYNAMIC BIDDER FORM
  // ============================================================
  function openDrawer() {
    uploadDrawer.classList.add('open');
  }

  function closeDrawer() {
    uploadDrawer.classList.remove('open');
  }

  if (btnOpenDrawer) btnOpenDrawer.addEventListener('click', openDrawer);
  if (btnCloseDrawer) btnCloseDrawer.addEventListener('click', closeDrawer);
  if (btnEmptyUpload) btnEmptyUpload.addEventListener('click', openDrawer);

  // Render dynamic bidder forms based on user-selected count (default = 2)
  function renderDrawerBidders(count = 2) {
    if (!drawerBiddersContainer) return;
    const bidders = [];
    for (let i = 0; i < count; i++) {
      const letter = String.fromCharCode(65 + i);
      bidders.push({
        id: `bidder_${letter}`,
        letter: letter,
        num: i + 1
      });
    }

    drawerBiddersContainer.innerHTML = bidders.map(b => `
      <div style="background: rgba(15, 23, 42, 0.6); padding: 12px; border-radius: var(--radius-sm); margin-bottom: 10px; border: 1px solid var(--border);">
        <div style="font-size: 12px; font-weight: 700; color: var(--accent); margin-bottom: 8px; display: flex; justify-content: space-between;">
          <span>Bidder ${b.num} (${b.id})</span>
          <span style="font-size: 11px; color: var(--text-muted);">Vendor Submission</span>
        </div>
        <div class="file-input-wrapper">
          <label>Company Legal Name:</label>
          <input type="text" class="input" id="upBidderName_${b.id}" placeholder="e.g. Bidder ${b.letter} (or enter company name)" value="">
        </div>
        <div class="file-input-wrapper">
          <label>Technical Bid (PDF): <span style="color: #f87171;">*</span></label>
          <input type="file" class="input" id="upBidderTech_${b.id}" accept=".pdf" required>
        </div>
        <div class="file-input-wrapper">
          <label>Financial Bid (PDF): <span style="font-size: 10px; color: var(--text-muted);">(Optional)</span></label>
          <input type="file" class="input" id="upBidderFin_${b.id}" accept=".pdf">
        </div>
        <div class="file-input-wrapper">
          <label>Financial BOQ (Excel): <span style="color: #f87171;">*</span></label>
          <input type="file" class="input" id="upBidderBoq_${b.id}" accept=".xlsx,.xls" required>
        </div>
      </div>
    `).join('');
  }

  // Handle number of bidders change
  if (numBiddersSelect) {
    numBiddersSelect.addEventListener('change', () => {
      const count = parseInt(numBiddersSelect.value, 10) || 2;
      renderDrawerBidders(count);
    });
  }

  // Initialize drawer with default 2 bidders
  renderDrawerBidders(2);

  // ============================================================
  // FETCH & RENDER DASHBOARD DATA
  // ============================================================
  async function loadDashboardData() {
    connectionBadge.textContent = '⏳ Checking Data...';
    connectionBadge.className = 'badge badge-warning';

    try {
      const res = await fetch('/api/data');
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load data`);
      const data = await res.json();
      cachedData = data;

      const hasValidData = Boolean(
        data.tender &&
        data.tender.tender_fields &&
        Object.keys(data.tender.tender_fields).length > 0 &&
        data.ranking
      );

      // Handle Empty State Banner & Connection Badge
      if (!hasValidData) {
        if (emptyStateBanner) emptyStateBanner.style.display = 'block';
        connectionBadge.textContent = '○ Awaiting Documents';
        connectionBadge.className = 'badge badge-warning';
      } else {
        if (emptyStateBanner) emptyStateBanner.style.display = 'none';
        connectionBadge.textContent = '● Evaluation Live';
        connectionBadge.className = 'badge badge-success';
      }

      // Update UI components
      renderKPIs(data, hasValidData);
      renderBaselineTable(data, hasValidData);
      renderTenderOverview(data, hasValidData);
      renderBOQ(data, hasValidData);
      renderComplianceMatrix(data, hasValidData);
      renderRanking(data, hasValidData);
      renderRisks(data, hasValidData);

    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      connectionBadge.textContent = '⚠️ Data Disconnected';
      connectionBadge.className = 'badge badge-danger';
    }
  }

  // ============================================================
  // TAB 1: EXECUTIVE DASHBOARD RENDERER
  // ============================================================
  function renderKPIs(data, hasData) {
    const tender = data.tender || {};
    const fields = tender.tender_fields || {};
    const ranking = data.ranking || {};
    const bidders = data.bidders || {};

    const tenderNo = fields.tender_number?.value || (hasData ? 'N/A' : 'Not Loaded');
    const org = fields.organisation?.value || (hasData ? 'N/A' : 'No documents evaluated yet');
    const bCount = Object.keys(bidders).length || ranking.ranking_table?.length || 0;
    const qualCount = ranking.qualified_bidders?.length || 0;
    const disqCount = ranking.disqualified_bidders?.length || 0;
    const recommended = ranking.recommended_bidder || (hasData ? 'None' : 'Pending Upload');
    const reserve = ranking.next_eligible_bidder || 'None';

    document.getElementById('kpiTenderId').textContent = tenderNo;
    document.getElementById('kpiOrg').textContent = org;
    document.getElementById('kpiBiddersCount').textContent = bCount;
    document.getElementById('kpiQualCount').textContent = `${qualCount} / ${disqCount}`;
    document.getElementById('kpiRecommended').textContent = recommended;

    // Hero Recommendation Card
    const heroTitle = document.getElementById('heroRecTitle');
    const heroText = document.getElementById('heroRecText');
    const heroReserve = document.getElementById('heroReserveText');

    if (heroTitle) {
      heroTitle.textContent = hasData 
        ? `🏆 Rank 1 — Recommended: ${recommended}` 
        : '📋 Awaiting Evaluation';
    }
    if (heroText) {
      heroText.textContent = ranking.recommendation_statement ||
        (hasData 
          ? `${recommended} is recommended for contract consideration.`
          : 'No tender documents have been processed yet. Upload common tender specifications and bidder proposals to generate evidence-grounded recommendations.');
    }
    if (heroReserve) {
      heroReserve.textContent = reserve && reserve !== 'None' 
        ? `${reserve} (Rank 2 Candidate)` 
        : (hasData ? 'None' : 'Awaiting Bids');
    }
  }

  function renderBaselineTable(data, hasData) {
    const tbody = document.querySelector('#dashboardBaselineTable tbody');
    if (!tbody) return;

    if (!hasData) {
      tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 24px;">No tender specifications loaded. Upload your tender files to begin evaluation.</td></tr>`;
      return;
    }

    const tender = data.tender || {};
    const fields = tender.tender_fields || {};

    const rows = [
      { param: 'Tender Identifier', field: 'tender_number' },
      { param: 'Procuring Organisation', field: 'organisation' },
      { param: 'Project / Scope of Work', field: 'project_name' },
      { param: 'Earnest Money Deposit (EMD)', field: 'emd' },
      { param: 'Performance Guarantee', field: 'performance_security' },
      { param: 'Mandatory Completion Schedule', field: 'completion_period' },
      { param: 'Estimated Project Cost', field: 'estimated_value' },
      { param: 'Proposal Submission Deadline', field: 'submission_deadline' }
    ];

    tbody.innerHTML = rows.map(r => {
      const f = fields[r.field];
      const val = f?.value || 'N/A';
      const page = f?.page ? `<span class="badge badge-info">Page ${f.page}</span>` : '';
      const evidence = f?.evidence ? `<span style="font-size: 11.5px; color: var(--text-muted); font-style: italic;">"${f.evidence}"</span>` : '';
      return `
        <tr>
          <td><strong>${r.param}</strong></td>
          <td style="color: var(--text-primary); font-weight: 500;">${val}</td>
          <td>${page} ${evidence}</td>
        </tr>
      `;
    }).join('');
  }

  // ============================================================
  // TAB 2: TENDER OVERVIEW RENDERER
  // ============================================================
  function renderTenderOverview(data, hasData) {
    const tender = data.tender || {};
    const fields = tender.tender_fields || {};
    const sections = tender.sections || [];

    const completionEl = document.getElementById('tOverviewCompletion');
    const emdEl = document.getElementById('tOverviewEMD');
    const secEl = document.getElementById('tOverviewSecurity');
    const valEl = document.getElementById('tOverviewValidity');

    if (completionEl) completionEl.textContent = fields.completion_period?.value || (hasData ? 'N/A' : '-');
    if (emdEl) emdEl.textContent = fields.emd?.value || (hasData ? 'N/A' : '-');
    if (secEl) secEl.textContent = fields.performance_security?.value || (hasData ? 'N/A' : '-');
    if (valEl) valEl.textContent = hasData ? '30 Days' : '-';

    // Extracted Fields Table
    const fieldsTbody = document.querySelector('#tenderFieldsTable tbody');
    if (fieldsTbody) {
      const fieldKeys = Object.keys(fields);
      if (!hasData || fieldKeys.length === 0) {
        fieldsTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 20px;">No extracted tender fields. Upload tender documents to extract requirements.</td></tr>`;
      } else {
        fieldsTbody.innerHTML = fieldKeys.map(k => {
          const item = fields[k];
          const label = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          return `
            <tr>
              <td><strong>${label}</strong></td>
              <td style="color: var(--accent); font-weight: 600;">${item.value || 'N/A'}</td>
              <td><span class="badge badge-info">Page ${item.page || '1'}</span></td>
              <td style="font-size: 12px; color: var(--text-secondary);">${item.evidence || '-'}</td>
            </tr>
          `;
        }).join('');
      }
    }

    // Detected Sections Table
    const sectionsTbody = document.querySelector('#tenderSectionsTable tbody');
    if (sectionsTbody) {
      if (!hasData || sections.length === 0) {
        sectionsTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 20px;">No sections detected.</td></tr>`;
      } else {
        sectionsTbody.innerHTML = sections.map((s, idx) => {
          const secNum = s.section_number || (idx + 1);
          const secTitle = s.section_title || s.title || `Section ${idx + 1}`;
          const pageNum = s.start_page || s.page_number || s.page || 1;
          const endPage = s.end_page && s.end_page !== pageNum ? `–${s.end_page}` : '';
          const charLen = s.char_count || (s.text ? s.text.length : (s.content ? s.content.length : 0));
          return `
            <tr>
              <td><span class="badge badge-info">§ ${secNum}</span></td>
              <td><strong>${secTitle}</strong></td>
              <td>Page ${pageNum}${endPage}</td>
              <td style="font-family: monospace; color: var(--accent); font-weight: 500;">${Number(charLen).toLocaleString()} chars</td>
            </tr>
          `;
        }).join('');
      }
    }
  }

  // ============================================================
  // TAB 3: BOQ ANALYSIS & VALIDATION RENDERER
  // ============================================================
  function renderBOQ(data, hasData) {
    const tenderBoq = data.tender_boq || [];
    const bidders = data.bidders || {};

    // 1. Tender Baseline BOQ Table
    const tBoqTbody = document.querySelector('#tenderBoqTable tbody');
    if (tBoqTbody) {
      if (!hasData || tenderBoq.length === 0) {
        tBoqTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">No baseline BOQ items loaded.</td></tr>`;
      } else {
        tBoqTbody.innerHTML = tenderBoq.map(item => {
          const rateStr = item.rate != null ? `₹${Number(item.rate).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : 'N/A';
          const amtStr = item.quoted_amount != null ? `₹${Number(item.quoted_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : 'N/A';
          return `
            <tr>
              <td><span class="badge badge-info">${item.item_no || '-'}</span></td>
              <td style="max-width: 380px;">${item.description || '-'}</td>
              <td style="text-align: right;">${item.quantity ?? '-'}</td>
              <td>${item.unit || 'Each / Item'}</td>
              <td style="text-align: right; font-family: monospace;">${rateStr}</td>
              <td style="text-align: right; font-weight: 600; font-family: monospace;">${amtStr}</td>
            </tr>
          `;
        }).join('');
      }
    }

    // 2. Populate Bidder Select
    if (boqBidderSelect) {
      const bidderIds = Object.keys(bidders);
      if (!hasData || bidderIds.length === 0) {
        boqBidderSelect.innerHTML = `<option value="">No Bidders Loaded</option>`;
        const bBoqTbody = document.querySelector('#bidderBoqTable tbody');
        if (bBoqTbody) bBoqTbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">No bidder proposals uploaded yet.</td></tr>`;
      } else {
        boqBidderSelect.innerHTML = bidderIds.map(bId => {
          const b = bidders[bId];
          const name = b.bidder_name || bId;
          return `<option value="${bId}">${name} (${bId})</option>`;
        }).join('');

        boqBidderSelect.onchange = () => {
          renderBidderBoqTable(boqBidderSelect.value, bidders);
        };

        if (bidderIds.length > 0) {
          renderBidderBoqTable(bidderIds[0], bidders);
        }
      }
    }
  }

  function renderBidderBoqTable(bidderId, bidders) {
    const tbody = document.querySelector('#bidderBoqTable tbody');
    if (!tbody) return;

    const bidder = bidders[bidderId];
    if (!bidder || !bidder.boq_validation || bidder.boq_validation.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">No BOQ validation records found for this bidder.</td></tr>`;
      return;
    }

    const items = bidder.boq_validation;
    tbody.innerHTML = items.map(item => {
      const isMismatch = item.status === 'MISMATCH' || (item.issues && item.issues.length > 0);
      const isMissing = item.status === 'MISSING';
      let badgeClass = 'badge-success';
      let statusText = 'VALID';

      if (isMismatch) {
        badgeClass = 'badge-danger';
        statusText = 'ARITHMETIC MISMATCH';
      } else if (isMissing) {
        badgeClass = 'badge-warning';
        statusText = 'MISSING VALUE';
      }

      const qRate = item.rate != null ? `₹${Number(item.rate).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : 'N/A';
      const qAmt = item.quoted_amount != null ? `₹${Number(item.quoted_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : 'N/A';
      const expAmt = item.expected_amount != null ? `₹${Number(item.expected_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : 'N/A';
      const issuesText = item.issues && item.issues.length > 0 ? item.issues.join('; ') : '✓ Verified (Qty × Rate = Quoted)';

      return `
        <tr>
          <td><span class="badge badge-info">${item.item_no || '-'}</span></td>
          <td style="max-width: 280px; font-size: 12px;">${item.description || '-'}</td>
          <td style="text-align: right;">${item.quantity ?? '-'}</td>
          <td style="text-align: right; font-family: monospace;">${qRate}</td>
          <td style="text-align: right; font-weight: 600; font-family: monospace;">${qAmt}</td>
          <td style="text-align: right; font-family: monospace; color: var(--text-muted);">${expAmt}</td>
          <td><span class="badge ${badgeClass}">${statusText}</span></td>
          <td style="font-size: 11.5px; color: ${isMismatch ? '#f87171' : 'var(--text-secondary)'};">${issuesText}</td>
        </tr>
      `;
    }).join('');
  }

  // ============================================================
  // TAB 4: BIDDER COMPLIANCE & COMPARISON MATRIX RENDERER
  // ============================================================
  function renderComplianceMatrix(data, hasData) {
    const comp = data.comparison || {};
    const fieldComparisons = comp.field_comparisons || [];
    const biddersSummary = comp.summary?.bidders || {};
    const diffs = comp.differences || [];

    const headerTr = document.getElementById('complianceMatrixHeader');
    const tbody = document.getElementById('complianceMatrixBody');

    if (!headerTr || !tbody) return;

    if (!hasData) {
      headerTr.innerHTML = `<th>Requirement</th><th>Baseline Specification</th><th>Bidder Compliance</th>`;
      tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 24px;">No compliance matrix available. Upload tender and bidder proposals to compare.</td></tr>`;
      const diffsContainer = document.getElementById('substantiveDiffsContainer');
      if (diffsContainer) diffsContainer.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No substantive deviations evaluated yet.</div>`;
      return;
    }

    const bidderKeys = Object.keys(biddersSummary);
    if (bidderKeys.length === 0 && fieldComparisons.length > 0 && fieldComparisons[0].bidders) {
      Object.keys(fieldComparisons[0].bidders).forEach(k => bidderKeys.push(k));
    }

    headerTr.innerHTML = `
      <th style="min-width: 170px;">Tender Requirement</th>
      <th style="min-width: 150px;">Baseline Specification</th>
      ${bidderKeys.map(k => {
        const name = biddersSummary[k]?.name || k;
        return `<th style="min-width: 200px;">${name}</th>`;
      }).join('')}
    `;

    if (fieldComparisons.length === 0) {
      tbody.innerHTML = `<tr><td colspan="${2 + bidderKeys.length}" style="text-align: center; color: var(--text-muted);">No compliance comparisons available.</td></tr>`;
    } else {
      tbody.innerHTML = fieldComparisons.map(item => {
        const fieldName = (item.field || '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const tenderReq = item.tender_requirement || 'N/A';

        const bidderCells = bidderKeys.map(k => {
          const bInfo = (item.bidders && item.bidders[k]) || {};
          const val = bInfo.value || 'N/A';
          const status = (bInfo.status || 'UNKNOWN').toUpperCase();
          const isCompliant = status === 'COMPLIANT';
          const badgeClass = isCompliant ? 'badge-success' : 'badge-danger';
          const msg = bInfo.message ? `<div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">${bInfo.message}</div>` : '';

          return `
            <td>
              <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 3px;">${val}</div>
              <span class="badge ${badgeClass}">${status}</span>
              ${msg}
            </td>
          `;
        }).join('');

        return `
          <tr>
            <td><strong>${fieldName}</strong></td>
            <td style="color: var(--accent); font-weight: 500;">${tenderReq}</td>
            ${bidderCells}
          </tr>
        `;
      }).join('');
    }

    // Substantive Differences
    const diffsContainer = document.getElementById('substantiveDiffsContainer');
    if (diffsContainer) {
      if (diffs.length === 0) {
        diffsContainer.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No substantive operational deviations detected across bidders.</div>`;
      } else {
        diffsContainer.innerHTML = diffs.map(d => {
          const fName = (d.field || '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          return `
            <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: var(--radius-sm); padding: 14px 18px;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                <div style="font-size: 13px; font-weight: 700; color: #f87171;">⚠️ ${fName} — Operational Impact: ${d.impact || 'High'}</div>
                <span class="badge badge-danger">SUBSTANTIVE DEVIATION</span>
              </div>
              <div style="font-size: 12.5px; color: var(--text-secondary);">${d.message || 'Deviation from mandatory tender baseline specifications.'}</div>
            </div>
          `;
        }).join('');
      }
    }
  }

  // ============================================================
  // TAB 5: MULTI-BIDDER RANKING & FALLBACK RENDERER
  // ============================================================
  function renderRanking(data, hasData) {
    const ranking = data.ranking || {};
    const rankingTable = ranking.ranking_table || [];
    const auditTrail = ranking.audit_trail || [];
    const evalParams = ranking.evaluation_parameters || {};

    const techW = document.getElementById('rkTechWeight');
    const finW = document.getElementById('rkFinWeight');
    const cutoff = document.getElementById('rkCutoff');
    const l1Quote = document.getElementById('rkL1Quote');

    if (techW) techW.textContent = hasData ? `${Math.round((evalParams.technical_weight || 0.8) * 100)}%` : '-';
    if (finW) finW.textContent = hasData ? `${Math.round((evalParams.financial_weight || 0.2) * 100)}%` : '-';
    if (cutoff) cutoff.textContent = hasData ? (evalParams.min_technical_score || 70.0).toFixed(1) : '-';
    if (l1Quote) {
      const l1Val = evalParams.lowest_qualified_bid_l1;
      l1Quote.textContent = l1Val ? `₹${Number(l1Val).toLocaleString('en-IN')}` : (hasData ? 'None' : '-');
    }

    renderRankingTableOnly(rankingTable, hasData);

    if (fallbackBidderSelect) {
      const qualified = rankingTable.filter(r => (r.qualification_status || r.qualification) === 'QUALIFIED');
      if (qualified.length === 0) {
        fallbackBidderSelect.innerHTML = `<option value="">No qualified candidates</option>`;
      } else {
        fallbackBidderSelect.innerHTML = qualified.map(b => `
          <option value="${b.bidder_id}">${b.bidder_name} (Rank ${b.rank})</option>
        `).join('');
      }
    }

    renderAuditTrail(auditTrail, hasData);
  }

  function renderRankingTableOnly(rankingTable, hasData = true) {
    const tbody = document.querySelector('#rankingTable tbody');
    if (!tbody) return;

    if (!hasData || rankingTable.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">No ranking data available. Upload bidder proposals to generate evaluation rankings.</td></tr>`;
      return;
    }

    tbody.innerHTML = rankingTable.map(row => {
      const isQualified = (row.qualification_status || row.qualification) === 'QUALIFIED';
      const badgeClass = isQualified ? 'badge-success' : 'badge-danger';
      const rankBadge = isQualified && row.rank === 1
        ? `<span class="badge badge-success" style="font-size: 13px; font-weight: 700;">🥇 Rank 1</span>`
        : isQualified
        ? `<span class="badge badge-info">Rank ${row.rank}</span>`
        : `<span class="badge badge-danger">Disqualified</span>`;

      const techScoreStr = typeof row.technical_score === 'number' ? row.technical_score.toFixed(1) : (row.technical_score || 'N/A');
      const finScoreStr = typeof row.financial_score === 'number' ? row.financial_score.toFixed(2) : (row.financial_score || 'N/A');
      const overallStr = typeof row.overall_score === 'number' ? `<strong>${row.overall_score.toFixed(2)}</strong>` : (row.overall_score || 'N/A');

      return `
        <tr style="${isQualified && row.rank === 1 ? 'background: rgba(16, 185, 129, 0.05);' : ''}">
          <td>${rankBadge}</td>
          <td><strong style="color: var(--text-primary);">${row.bidder_name || row.bidder_id}</strong></td>
          <td><span class="badge ${badgeClass}">${row.qualification_status || row.qualification}</span></td>
          <td style="text-align: right; font-family: monospace;">${techScoreStr}</td>
          <td style="text-align: right; font-family: monospace; font-weight: 600;">${row.quoted_amount || 'N/A'}</td>
          <td style="text-align: right; font-family: monospace;">${finScoreStr}</td>
          <td style="text-align: right; font-family: monospace; color: var(--accent);">${overallStr}</td>
          <td style="font-size: 12px; color: ${isQualified ? 'var(--text-secondary)' : '#f87171'};">${row.status_reason || '-'}</td>
        </tr>
      `;
    }).join('');
  }

  function renderAuditTrail(auditTrail, hasData = true) {
    const tbody = document.querySelector('#auditTrailTable tbody');
    if (!tbody) return;

    if (!hasData || auditTrail.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">No audit log records recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = auditTrail.map(event => {
      const timeStr = event.timestamp ? new Date(event.timestamp).toLocaleString() : 'N/A';
      return `
        <tr>
          <td style="font-family: monospace; font-size: 11.5px; color: var(--text-muted);">${timeStr}</td>
          <td><span class="badge badge-info">${event.action || 'EVALUATION'}</span></td>
          <td style="color: #34d399; font-weight: 600;">${event.recommended_bidder || 'None'}</td>
          <td style="color: var(--accent); font-weight: 500;">${event.next_eligible_bidder || 'None'}</td>
          <td style="font-size: 12px; color: var(--text-secondary);">${event.notes || event.reason || '-'}</td>
        </tr>
      `;
    }).join('');
  }

  // Fallback Simulator Click Handler
  if (btnRunFallback) {
    btnRunFallback.addEventListener('click', async () => {
      const selectedBidder = fallbackBidderSelect ? fallbackBidderSelect.value : null;
      const reason = fallbackReasonInput ? fallbackReasonInput.value.trim() : 'Post-qualification verification failed';

      if (!selectedBidder) {
        alert('Please select a qualified candidate to simulate fallback.');
        return;
      }

      btnRunFallback.disabled = true;
      btnRunFallback.textContent = '⏳ Recalculating...';

      try {
        const res = await fetch('/api/ranking/fallback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bidder_id: selectedBidder, reason })
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}: Fallback failed`);
        const updated = await res.json();

        if (cachedData) {
          cachedData.ranking = updated;
          renderKPIs(cachedData, true);
        }

        renderRankingTableOnly(updated.ranking_table || [], true);
        renderAuditTrail(updated.audit_trail || [], true);

        if (fallbackResultAlert) {
          fallbackResultAlert.style.display = 'block';
          fallbackResultAlert.innerHTML = `
            <strong>⚡ Fallback Recalculation Completed!</strong><br>
            Disqualified: <em>${selectedBidder}</em> (${reason})<br>
            <strong>New Provisional Recommendation:</strong> <span style="color: #34d399; font-weight: 700;">${updated.recommended_bidder || 'None'}</span><br>
            <strong>New Reserve Alternative:</strong> ${updated.next_eligible_bidder || 'None'}
          `;
        }
      } catch (err) {
        alert(`Fallback simulation error: ${err.message}`);
      } finally {
        btnRunFallback.disabled = false;
        btnRunFallback.textContent = '⚡ Recalculate Ranking';
      }
    });
  }

  // ============================================================
  // TAB 6: RISK ANALYSIS RENDERER
  // ============================================================
  function renderRisks(data, hasData) {
    const risks = data.risks || [];
    const container = document.getElementById('tenderRisksList');
    if (!container) return;

    if (!hasData || risks.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 24px;">No contractual risks analyzed. Upload tender specifications to inspect clauses.</div>`;
      return;
    }

    container.innerHTML = risks.map(r => {
      const sev = (r.severity || 'MEDIUM').toUpperCase();
      let badgeClass = 'badge-warning';
      let sevColor = '#fbbf24';

      if (sev === 'HIGH' || sev === 'CRITICAL') {
        badgeClass = 'badge-danger';
        sevColor = '#f87171';
      } else if (sev === 'LOW') {
        badgeClass = 'badge-info';
        sevColor = '#38bdf8';
      }

      return `
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-left: 4px solid ${sevColor}; border-radius: var(--radius-sm); padding: 16px 20px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
              <span>⚠️ ${r.title || r.risk_type || 'Contractual Clause Risk'}</span>
              ${r.page ? `<span class="badge badge-info">Page ${r.page}</span>` : ''}
              ${r.category ? `<span style="font-size: 11px; color: var(--text-muted);">[Category: ${r.category}]</span>` : ''}
            </div>
            <span class="badge ${badgeClass}">${sev} RISK</span>
          </div>

          <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.5;">
            ${r.description || '-'}
          </div>

          ${r.evidence ? `
            <div style="background: rgba(15, 23, 42, 0.6); padding: 8px 12px; border-radius: var(--radius-sm); font-size: 11.5px; color: var(--text-muted); font-style: italic; border: 1px solid rgba(255,255,255,0.05);">
              Verbatim Evidence: "${r.evidence}"
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  // ============================================================
  // TAB 7: RAG EVIDENCE ASSISTANT
  // ============================================================
  async function submitRagQuery(queryText) {
    const q = queryText || (ragQueryInput ? ragQueryInput.value.trim() : '');
    if (!q) {
      alert('Please enter a question regarding the tender or bidder evaluation.');
      return;
    }

    if (ragQueryInput) ragQueryInput.value = q;
    btnAskRag.disabled = true;
    btnAskRag.innerHTML = `<span>⏳ Searching Grounded Evidence...</span>`;

    ragResponseCard.classList.add('active');
    ragResponseCard.classList.add('visible');
    ragResponseCard.style.display = 'block';
    ragAnswerText.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">Analyzing tender document and evaluation audit trail...</div>`;
    ragSourcesContainer.innerHTML = '';

    try {
      const res = await fetch('/api/rag/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, tender_id: 'tender_001' })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to get answer`);
      const result = await res.json();

      const formattedAnswer = formatMarkdownToHtml(result.answer || 'No answer generated.');
      ragAnswerText.innerHTML = formattedAnswer;

      const sources = result.sources || [];
      if (sources.length === 0) {
        ragSourcesContainer.innerHTML = `<div style="font-size: 12px; color: var(--text-muted);">Direct factual resolution via deterministic evaluation audit log.</div>`;
      } else {
        ragSourcesContainer.innerHTML = sources.map((s, idx) => {
          const pageNum = s.page_number || s.page || 1;
          const scoreText = s.similarity_score != null 
            ? `Similarity: ${s.similarity_score.toFixed(3)}` 
            : (s.distance != null ? `Relevance: ${Math.max(0, Math.round((1 - s.distance) * 100))}%` : 'Direct Citation');
          return `
            <div class="source-card">
              <div class="source-card-header">
                <span class="source-title">📄 Source Document [Citation #${idx + 1}] — ${s.section_title || 'Tender Section'}</span>
                <span class="badge badge-info">Page ${pageNum} • ${scoreText}</span>
              </div>
              <div class="source-snippet">"${s.text || s.content || ''}"</div>
            </div>
          `;
        }).join('');
      }
    } catch (err) {
      ragAnswerText.innerHTML = `<div style="color: #f87171; font-size: 13px;">Error: ${err.message}</div>`;
    } finally {
      btnAskRag.disabled = false;
      btnAskRag.innerHTML = `<span>🔎 Ask Assistant</span>`;
    }
  }

  function formatMarkdownToHtml(md) {
    if (!md) return '';
    return md
      .replace(/^### (.*$)/gim, '<h4 style="font-size: 14px; color: #38bdf8; margin: 12px 0 6px;">$1</h4>')
      .replace(/^## (.*$)/gim, '<h3 style="font-size: 15px; color: #38bdf8; margin: 14px 0 8px;">$1</h3>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/`([^`]+)`/gim, '<code style="background: rgba(15,23,42,0.8); padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #34d399;">$1</code>')
      .replace(/\n\n/gim, '<br><br>')
      .replace(/\n/gim, '<br>');
  }

  if (btnAskRag) btnAskRag.addEventListener('click', () => submitRagQuery());

  if (ragQueryInput) {
    ragQueryInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitRagQuery();
      }
    });
  }

  suggestionPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const q = pill.getAttribute('data-query');
      if (q) {
        switchTab('rag');
        submitRagQuery(q);
      }
    });
  });

  // ============================================================
  // CLEAR DATA & RESET HANDLER
  // ============================================================
  if (btnClearData) {
    btnClearData.addEventListener('click', async () => {
      const confirmed = confirm('Are you sure you want to clear all loaded evaluation data? This will reset the dashboard to a completely fresh initial state.');
      if (!confirmed) return;

      btnClearData.disabled = true;
      btnClearData.textContent = '⏳ Clearing...';

      try {
        const res = await fetch('/api/clear', { method: 'POST' });
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to clear data`);
        await loadDashboardData();
        alert('All evaluation data cleared! The dashboard is now in a clean initial state.');
      } catch (err) {
        alert(`Error clearing data: ${err.message}`);
      } finally {
        btnClearData.disabled = false;
        btnClearData.textContent = '🗑️ Clear / Reset';
      }
    });
  }

  if (btnRefreshData) {
    btnRefreshData.addEventListener('click', () => loadDashboardData());
  }

  // ============================================================
  // UPLOAD FORM SUBMIT HANDLER (DYNAMIC N BIDDERS)
  // ============================================================
  if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const tenderPdf = document.getElementById('upTenderPdf')?.files[0];
      const tenderBoq = document.getElementById('upTenderBoq')?.files[0];

      if (!tenderPdf || !tenderBoq) {
        alert('Please select both Common Tender PDF and BOQ Excel files.');
        return;
      }

      const count = parseInt(numBiddersSelect ? numBiddersSelect.value : '2', 10) || 2;
      const formData = new FormData();
      formData.append('tender_pdf', tenderPdf);
      formData.append('tender_boq', tenderBoq);
      formData.append('bidder_count', count);

      const bidderData = [];
      for (let i = 0; i < count; i++) {
        const letter = String.fromCharCode(65 + i);
        const bId = `bidder_${letter}`;
        const nameVal = document.getElementById(`upBidderName_${bId}`)?.value.trim();
        const bName = nameVal || `Bidder ${letter}`;

        const techFile = document.getElementById(`upBidderTech_${bId}`)?.files[0];
        const finFile = document.getElementById(`upBidderFin_${bId}`)?.files[0];
        const boqFile = document.getElementById(`upBidderBoq_${bId}`)?.files[0];

        if (!techFile || !boqFile) {
          alert(`Please upload both Technical Bid PDF and BOQ Excel for Bidder ${i + 1} (${bName}).`);
          return;
        }

        formData.append(`file_${bId}_tech`, techFile);
        if (finFile) {
          formData.append(`file_${bId}_fin`, finFile);
        }
        formData.append(`file_${bId}_boq`, boqFile);

        bidderData.push({ id: bId, name: bName });
      }

      formData.append('bidder_data_json', JSON.stringify(bidderData));

      const submitBtn = document.getElementById('btnSubmitUpload');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>⏳ Evaluating Multi-Bidder Proposals...</span>`;
      }

      try {
        const res = await fetch('/api/analyze', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || errData.log || `HTTP ${res.status}: Upload evaluation failed`);
        }
        const result = await res.json();

        alert('Evaluation pipeline completed successfully!');
        await loadDashboardData();
        closeDrawer();
      } catch (err) {
        alert(`Evaluation error: ${err.message}`);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = `<span>🔍 Start Multi-Bidder Evaluation</span>`;
        }
      }
    });
  }

  // Initial Load
  loadDashboardData();
});
