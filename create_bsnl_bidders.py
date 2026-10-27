"""
BSNL Tender Bidder Dataset Generator
Creates complete, authentic Bidder Submissions (A, B, C) matching the real
BSNL maintenance tender (19/NIT/EE(C)/BSNL/HLW/2026-27) downloaded from eprocure.gov.in.
"""

import os
import shutil
import zipfile
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
TEMP_ZIP_DIR = BASE_DIR / "temp_inspect_zip"
DATASET_DIR = BASE_DIR / "data" / "bsnl_tender_dataset"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

TENDER_DIR = DATASET_DIR / "Common_Tender"
BIDDER_A_DIR = DATASET_DIR / "Bidder_A_Shiva_Construction"
BIDDER_B_DIR = DATASET_DIR / "Bidder_B_Haldwani_Infra"
BIDDER_C_DIR = DATASET_DIR / "Bidder_C_Kumaon_Buildcon"

for d in [TENDER_DIR, BIDDER_A_DIR, BIDDER_B_DIR, BIDDER_C_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 1. Copy Common Tender PDF & BOQ
nit_src = TEMP_ZIP_DIR / "nit19hlw.pdf"
boq_src = TEMP_ZIP_DIR / "BOQ_344777.xls"

if nit_src.exists():
    shutil.copy(nit_src, TENDER_DIR / "BSNL_Tender_Document.pdf")
    print(f"Copied {nit_src.name} -> {TENDER_DIR / 'BSNL_Tender_Document.pdf'}")

if boq_src.exists():
    shutil.copy(boq_src, TENDER_DIR / "BSNL_Tender_BOQ.xls")
    print(f"Copied {boq_src.name} -> {TENDER_DIR / 'BSNL_Tender_BOQ.xls'}")


# Helper to create clean PDF using PyMuPDF if available, or minimal PDF writer
def create_pdf(output_path, title, pages_text_list):
    try:
        import pymupdf
        doc = pymupdf.open()
        for page_text in pages_text_list:
            page = doc.new_page(width=595, height=842) # A4
            # Draw header bar
            rect = pymupdf.Rect(40, 30, 555, 60)
            page.draw_rect(rect, color=(0.1, 0.3, 0.6), fill=(0.1, 0.3, 0.6))
            page.insert_text((50, 50), title.upper(), fontsize=12, color=(1, 1, 1))

            # Insert body text line by line
            y = 80
            for line in page_text.split("\n"):
                if y > 790:
                    break
                line_str = line.strip()
                if line_str.startswith("# "):
                    page.insert_text((50, y), line_str[2:], fontsize=13, color=(0.1, 0.2, 0.5))
                    y += 22
                elif line_str.startswith("## "):
                    page.insert_text((50, y), line_str[3:], fontsize=11, color=(0.2, 0.3, 0.4))
                    y += 18
                elif line_str.startswith("- ") or line_str.startswith("• "):
                    page.insert_text((60, y), line_str, fontsize=10, color=(0.15, 0.15, 0.15))
                    y += 16
                elif ":" in line_str and len(line_str.split(":")[0]) < 30:
                    k, v = line_str.split(":", 1)
                    page.insert_text((50, y), f"{k}:", fontsize=10, color=(0.1, 0.2, 0.4))
                    page.insert_text((220, y), v.strip(), fontsize=10, color=(0, 0, 0))
                    y += 16
                else:
                    page.insert_text((50, y), line_str, fontsize=10, color=(0.15, 0.15, 0.15))
                    y += 15

            # Footer
            page.insert_text((50, 810), f"Confidential Tender Submission — Ref: 19/NIT/EE(C)/BSNL/HLW/2026-27", fontsize=8, color=(0.5, 0.5, 0.5))

        doc.save(str(output_path))
        doc.close()
        print(f"Created PDF: {output_path.name}")
        return True
    except Exception as e:
        print(f"Error creating PDF {output_path}: {e}")
        return False


# Helper to create clean standard XML .xlsx workbook
def create_xlsx(filepath, headers, rows):
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets>
        <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
    </sheets>
</workbook>'''

    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>'''

    sheet_rows = []
    # Header row
    h_cells = []
    for col_idx, h in enumerate(headers, 1):
        col_letter = chr(64 + col_idx) if col_idx <= 26 else f"A{chr(64 + col_idx - 26)}"
        h_cells.append(f'<c r="{col_letter}1" t="inlineStr"><is><t>{h}</t></is></c>')
    sheet_rows.append(f'<row r="1">{"".join(h_cells)}</row>')

    for row_idx, r in enumerate(rows, 2):
        r_cells = []
        for col_idx, val in enumerate(r, 1):
            col_letter = chr(64 + col_idx) if col_idx <= 26 else f"A{chr(64 + col_idx - 26)}"
            if isinstance(val, (int, float)):
                r_cells.append(f'<c r="{col_letter}{row_idx}"><v>{val}</v></c>')
            elif str(val).startswith("="):
                formula_str = str(val).lstrip("=")
                r_cells.append(f'<c r="{col_letter}{row_idx}"><f>{formula_str}</f></c>')
            else:
                r_cells.append(f'<c r="{col_letter}{row_idx}" t="inlineStr"><is><t>{val}</t></is></c>')
        sheet_rows.append(f'<row r="{row_idx}">{"".join(r_cells)}</row>')

    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData>
        {''.join(sheet_rows)}
    </sheetData>
</worksheet>'''

    with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    print(f"Created BOQ: {filepath.name}")


# -------------------------------------------------------------
# Common Tender BOQ (Converted clean .xlsx template)
# -------------------------------------------------------------
tender_boq_headers = ["Item No", "Description of Item", "Quantity", "Unit", "Estimated Rate (INR)", "Estimated Amount (INR)"]
tender_boq_items = [
    ["1.01", "Demolishing cement concrete manually/mechanical means", 1.0, "cum", 1540.0, 1540.0],
    ["1.02", "Demolishing brick work in cement mortar", 2.5, "cum", 980.0, 2450.0],
    ["1.03", "Providing and laying specified grade RCC 1:2:4 up to plinth", 0.5, "cum", 6850.0, 3425.0],
    ["1.04", "Steel reinforcement for RCC work Fe-500D bars", 28.0, "kg", 85.0, 2380.0],
    ["1.05", "Brick work with common burnt clay bricks in 1:6 cement mortar", 3.0, "cum", 5400.0, 16200.0],
    ["1.06", "Repairs to plaster 12mm to 20mm in patches with cement mortar 1:4", 35.0, "sqm", 320.0, 11200.0],
    ["1.07", "Distempering with 1st quality acrylic distemper on old work", 25.0, "sqm", 115.0, 2875.0],
    ["1.08", "Painting with synthetic enamel paint of approved brand on old work", 18.0, "sqm", 145.0, 2610.0],
    ["1.09", "Providing and applying fibre reinforced elastomeric liquid waterproofing", 12.0, "sqm", 480.0, 5760.0],
    ["1.10", "Providing and fixing G.I. pipes 15mm dia with fittings and clamps", 6.0, "metre", 295.0, 1770.0],
    ["1.11", "Providing and fixing gun metal gate valve 25mm nominal bore", 2.0, "each", 620.0, 1240.0],
    ["1.12", "Day to day routine civil maintenance operations and plumbing upkeep", 4.0, "months", 48045.25, 192181.0]
]
create_xlsx(TENDER_DIR / "BSNL_Tender_BOQ.xlsx", tender_boq_headers, tender_boq_items)


# -------------------------------------------------------------
# BIDDER A: Shiva Construction Co. (Compliant, Rank 1)
# -------------------------------------------------------------
bidder_a_tech_text = """# TECHNICAL BID SUBMISSION
## TENDER REFERENCE: 19/NIT/EE(C)/BSNL/HLW/2026-27
CLIENT: Executive Engineer (Civil), BSNL Civil Division, Haldwani

Bidder Name: Shiva Construction Co.
Corporate Office: Circular Road, Kathgodam, Haldwani, Nainital, Uttarakhand - 263126
Registration: Class III Registered Civil Contractor with BSNL / CPWD
GSTIN: 05AAACS9821M1ZX

EVALUATION PARAMETERS & STATUTORY UNDERTAKINGS:
- Project Name: Day to day maintenance works in TE compound at Haldwani, Nainital for four months
- Mandatory Completion Period: 4 months (We unconditionally confirm completion within 4 months)
- Earnest Money Deposit (EMD): INR 4,993 (Deposited via RTGS/NEFT Transaction UTR: BSNL/EMD/2026/89412 on 24-10-2026)
- Tender Fee: INR 590 (Paid via transaction ref UTR: TF/BSNL/99023)
- Performance Security: Unconditional acceptance to submit 5% performance guarantee within 15 days of Letter of Acceptance
- Bid Validity: 180 days from the closing date of tender submission
- Minimum Technical Score Cutoff: 70 marks (Our self-assessed and audited score is 86.0 marks)

TECHNICAL CAPABILITY & PAST PERFORMANCE:
- Experience: Over 11 years of civil maintenance experience with BSNL, CPWD, and Uttarakhand PWD
- Average Annual Financial Turnover: INR 48.5 Lakhs over the last 3 financial years (Minimum requirement: INR 1.25 Lakhs)
- Key Technical Personnel: 1 Graduate Civil Engineer (Project In-Charge) + 2 Diploma Site Supervisors
- Tools & Plants Available: Concrete mixers, needle vibrators, pressure pumps, scaffoldings, testing equipment
- Solvency Certificate: Solvency of INR 10 Lakhs issued by State Bank of India, Haldwani Branch
- Litigation History: Nil. The firm has never been blacklisted or debarred by any government department.
"""

bidder_a_fin_text = """# FINANCIAL BID / COMMERCIAL PROPOSAL
## TENDER REFERENCE: 19/NIT/EE(C)/BSNL/HLW/2026-27
WORK: Day to day maintenance works in TE compound at Haldwani, Nainital for four months.

To,
The Executive Engineer (Civil),
BSNL Civil Division, Haldwani, Nainital.

Dear Sir,
Having examined the Notice Inviting Tender (NIT No. 19/NIT/EE(C)/BSNL/HLW/2026-27), General Conditions of Contract,
Specifications, and Bill of Quantities, we, Shiva Construction Co., hereby offer to execute and complete the said works
in conformity with the conditions of contract.

COMMERCIAL QUOTATION SUMMARY:
- Departmental Estimated Cost: INR 2,49,631.00
- Quoted Total Lump-Sum Amount: INR 2,42,150.00 (Rupees Two Lakh Forty-Two Thousand One Hundred Fifty Only)
- Percentage Quoted: 3.00% Below Departmental Estimated Cost
- Currency: Indian Rupees (INR)
- Taxes Included: All basic rates are quoted inclusive of labor cess, royalties, and freight, with GST payable as per GOI norms.
- Completion Schedule: 4 (Four) Months from 10th day of award.

We understand that you are not bound to accept the lowest or any tender you may receive.

Authorized Signatory,
Shiva Construction Co.
"""

create_pdf(BIDDER_A_DIR / "Technical_Bid.pdf", "Shiva Construction Co. — Technical Bid", [bidder_a_tech_text])
create_pdf(BIDDER_A_DIR / "Financial_Bid.pdf", "Shiva Construction Co. — Financial Bid", [bidder_a_fin_text])

# Bidder A BOQ (Zero errors, valid math, total = 242,150)
bidder_a_boq = [
    ["1.01", "Demolishing cement concrete manually/mechanical means", 1.0, "cum", 1500.0, 1500.0],
    ["1.02", "Demolishing brick work in cement mortar", 2.5, "cum", 950.0, 2375.0],
    ["1.03", "Providing and laying specified grade RCC 1:2:4 up to plinth", 0.5, "cum", 6700.0, 3350.0],
    ["1.04", "Steel reinforcement for RCC work Fe-500D bars", 28.0, "kg", 82.0, 2296.0],
    ["1.05", "Brick work with common burnt clay bricks in 1:6 cement mortar", 3.0, "cum", 5250.0, 15750.0],
    ["1.06", "Repairs to plaster 12mm to 20mm in patches with cement mortar 1:4", 35.0, "sqm", 310.0, 10850.0],
    ["1.07", "Distempering with 1st quality acrylic distemper on old work", 25.0, "sqm", 110.0, 2750.0],
    ["1.08", "Painting with synthetic enamel paint of approved brand on old work", 18.0, "sqm", 140.0, 2520.0],
    ["1.09", "Providing and applying fibre reinforced elastomeric liquid waterproofing", 12.0, "sqm", 470.0, 5640.0],
    ["1.10", "Providing and fixing G.I. pipes 15mm dia with fittings and clamps", 6.0, "metre", 285.0, 1710.0],
    ["1.11", "Providing and fixing gun metal gate valve 25mm nominal bore", 2.0, "each", 605.0, 1210.0],
    ["1.12", "Day to day routine civil maintenance operations and plumbing upkeep", 4.0, "months", 48049.75, 192199.0]
]
create_xlsx(BIDDER_A_DIR / "BOQ.xlsx", ["Item No", "Description of Item", "Quantity", "Unit", "Quoted Rate (INR)", "Quoted Amount (INR)"], bidder_a_boq)


# -------------------------------------------------------------
# BIDDER B: Haldwani Infrastructure Pvt Ltd (Non-compliant, Disqualified)
# -------------------------------------------------------------
bidder_b_tech_text = """# TECHNICAL BID SUBMISSION
## TENDER REFERENCE: 19/NIT/EE(C)/BSNL/HLW/2026-27
CLIENT: Executive Engineer (Civil), BSNL Civil Division, Haldwani

Bidder Name: Haldwani Infrastructure Pvt Ltd
Corporate Office: Nainital Road, Tikonia, Haldwani, Uttarakhand - 263139
Registration: Class II Contractor
GSTIN: 05AAACH4521N1ZY

EVALUATION PARAMETERS & STATUTORY UNDERTAKINGS:
- Project Name: Day to day maintenance works in TE compound at Haldwani, Nainital for four months
- Proposed Completion Period: 6 months (Due to mobilization constraints and monsoon weather, we request 6 months completion)
- Earnest Money Deposit (EMD): INR 4,993 (Submitted via Demand Draft DD-448210 from PNB Haldwani)
- Tender Fee: INR 590 (Paid via transaction ref UTR: TF/BSNL/88219)
- Performance Security: Accepted to provide 5% performance guarantee
- Bid Validity: 180 days
- Minimum Technical Score Cutoff: 70 marks (Our score is 78.0 marks)

TECHNICAL QUALIFICATIONS & INFRASTRUCTURE:
- Past Projects: Maintenance of telecom towers and residential quarters across Kumaon region
- Annual Turnover: INR 32 Lakhs
- Note on Schedule Deviation: We emphasize that 4 months is insufficient for full water-proofing and plumbing repairs, hence we formally submit a 6-month completion schedule.
"""

bidder_b_fin_text = """# FINANCIAL BID / COMMERCIAL PROPOSAL
## TENDER REFERENCE: 19/NIT/EE(C)/BSNL/HLW/2026-27
WORK: Day to day maintenance works in TE compound at Haldwani, Nainital for four months.

To,
The Executive Engineer (Civil),
BSNL Civil Division, Haldwani.

Dear Sir,
Haldwani Infrastructure Pvt Ltd hereby tenders our commercial proposal for the execution of the said maintenance works.

COMMERCIAL QUOTATION SUMMARY:
- Departmental Estimated Cost: INR 2,49,631.00
- Quoted Total Lump-Sum Amount: INR 2,35,000.00 (Rupees Two Lakh Thirty-Five Thousand Only)
- Percentage Quoted: 5.86% Below Estimated Cost (Lowest Aggressive Price)
- Schedule: 6 Months (Subject to schedule relaxation approval).

Authorized Signatory,
Haldwani Infrastructure Pvt Ltd
"""

create_pdf(BIDDER_B_DIR / "Technical_Bid.pdf", "Haldwani Infrastructure — Technical Bid", [bidder_b_tech_text])
create_pdf(BIDDER_B_DIR / "Financial_Bid.pdf", "Haldwani Infrastructure — Financial Bid", [bidder_b_fin_text])

# Bidder B BOQ (Contains deliberate calculation error in Item 1.02 to test BOQ validator)
bidder_b_boq = [
    ["1.01", "Demolishing cement concrete manually/mechanical means", 1.0, "cum", 1450.0, 1450.0],
    ["1.02", "Demolishing brick work in cement mortar", 2.5, "cum", 900.0, 1800.0], # MISMATCH: 2.5 * 900 should be 2250, quoted 1800!
    ["1.03", "Providing and laying specified grade RCC 1:2:4 up to plinth", 0.5, "cum", 6500.0, 3250.0],
    ["1.04", "Steel reinforcement for RCC work Fe-500D bars", 28.0, "kg", 80.0, 2240.0],
    ["1.05", "Brick work with common burnt clay bricks in 1:6 cement mortar", 3.0, "cum", 5100.0, 15300.0],
    ["1.06", "Repairs to plaster 12mm to 20mm in patches with cement mortar 1:4", 35.0, "sqm", 300.0, 10500.0],
    ["1.07", "Distempering with 1st quality acrylic distemper on old work", 25.0, "sqm", 105.0, 2625.0],
    ["1.08", "Painting with synthetic enamel paint of approved brand on old work", 18.0, "sqm", 135.0, 2430.0],
    ["1.09", "Providing and applying fibre reinforced elastomeric liquid waterproofing", 12.0, "sqm", 450.0, 5400.0],
    ["1.10", "Providing and fixing G.I. pipes 15mm dia with fittings and clamps", 6.0, "metre", 270.0, 1620.0],
    ["1.11", "Providing and fixing gun metal gate valve 25mm nominal bore", 2.0, "each", 590.0, 1180.0],
    ["1.12", "Day to day routine civil maintenance operations and plumbing upkeep", 4.0, "months", 46801.25, 187205.0]
]
create_xlsx(BIDDER_B_DIR / "BOQ.xlsx", ["Item No", "Description of Item", "Quantity", "Unit", "Quoted Rate (INR)", "Quoted Amount (INR)"], bidder_b_boq)


# -------------------------------------------------------------
# BIDDER C: Kumaon Buildcon Projects (Compliant, Rank 2 Reserve)
# -------------------------------------------------------------
bidder_c_tech_text = """# TECHNICAL BID SUBMISSION
## TENDER REFERENCE: 19/NIT/EE(C)/BSNL/HLW/2026-27
CLIENT: Executive Engineer (Civil), BSNL Civil Division, Haldwani

Bidder Name: Kumaon Buildcon Projects
Corporate Office: Kaladhungi Road, Kusumkhera, Haldwani, Nainital, Uttarakhand - 263139
Registration: Approved Contractor with BSNL
GSTIN: 05AAACK3109P1ZZ

EVALUATION PARAMETERS & STATUTORY UNDERTAKINGS:
- Project Name: Day to day maintenance works in TE compound at Haldwani, Nainital for four months
- Completion Period: 4 months (We unconditionally confirm completion within 4 months)
- Earnest Money Deposit (EMD): INR 4,993 (Submitted via online RTGS ref BSNL/EMD/2026/9104)
- Tender Fee: INR 590 (Paid via transaction ref UTR: TF/BSNL/77102)
- Performance Security: Unconditional acceptance to submit 5% performance guarantee
- Bid Validity: 180 days
- Minimum Technical Score Cutoff: 70 marks (Our audited technical score is 81.0 marks)

TECHNICAL CREDENTIALS & WORK EXPERIENCE:
- Track Record: 8 years of successful facility and building maintenance works in Uttarakhand
- Financial Turnover: INR 39 Lakhs average over preceding 3 years
- Supervisory Staff: Qualified diploma civil supervisors dedicated full-time to site maintenance
- Plant & Equipment: All necessary scaffolding, testing kits, plumbing apparatus available in-house
- Debarment Status: Never debarred or penalized by BSNL or any government authority
"""

bidder_c_fin_text = """# FINANCIAL BID / COMMERCIAL PROPOSAL
## TENDER REFERENCE: 19/NIT/EE(C)/BSNL/HLW/2026-27
WORK: Day to day maintenance works in TE compound at Haldwani, Nainital for four months.

To,
The Executive Engineer (Civil),
BSNL Civil Division, Haldwani.

Dear Sir,
Kumaon Buildcon Projects hereby submits our commercial quotation for the tender.

COMMERCIAL QUOTATION SUMMARY:
- Departmental Estimated Cost: INR 2,49,631.00
- Quoted Total Lump-Sum Amount: INR 2,48,800.00 (Rupees Two Lakh Forty-Eight Thousand Eight Hundred Only)
- Percentage Quoted: 0.33% Below Estimated Cost
- Completion Schedule: 4 Months.

Authorized Signatory,
Kumaon Buildcon Projects
"""

create_pdf(BIDDER_C_DIR / "Technical_Bid.pdf", "Kumaon Buildcon — Technical Bid", [bidder_c_tech_text])
create_pdf(BIDDER_C_DIR / "Financial_Bid.pdf", "Kumaon Buildcon — Financial Bid", [bidder_c_fin_text])

# Bidder C BOQ (Clean arithmetic, total = 248,800)
bidder_c_boq = [
    ["1.01", "Demolishing cement concrete manually/mechanical means", 1.0, "cum", 1530.0, 1530.0],
    ["1.02", "Demolishing brick work in cement mortar", 2.5, "cum", 970.0, 2425.0],
    ["1.03", "Providing and laying specified grade RCC 1:2:4 up to plinth", 0.5, "cum", 6800.0, 3400.0],
    ["1.04", "Steel reinforcement for RCC work Fe-500D bars", 28.0, "kg", 84.0, 2352.0],
    ["1.05", "Brick work with common burnt clay bricks in 1:6 cement mortar", 3.0, "cum", 5350.0, 16050.0],
    ["1.06", "Repairs to plaster 12mm to 20mm in patches with cement mortar 1:4", 35.0, "sqm", 318.0, 11130.0],
    ["1.07", "Distempering with 1st quality acrylic distemper on old work", 25.0, "sqm", 114.0, 2850.0],
    ["1.08", "Painting with synthetic enamel paint of approved brand on old work", 18.0, "sqm", 144.0, 2592.0],
    ["1.09", "Providing and applying fibre reinforced elastomeric liquid waterproofing", 12.0, "sqm", 475.0, 5700.0],
    ["1.10", "Providing and fixing G.I. pipes 15mm dia with fittings and clamps", 6.0, "metre", 290.0, 1740.0],
    ["1.11", "Providing and fixing gun metal gate valve 25mm nominal bore", 2.0, "each", 615.0, 1230.0],
    ["1.12", "Day to day routine civil maintenance operations and plumbing upkeep", 4.0, "months", 49450.25, 197801.0]
]
create_xlsx(BIDDER_C_DIR / "BOQ.xlsx", ["Item No", "Description of Item", "Quantity", "Unit", "Quoted Rate (INR)", "Quoted Amount (INR)"], bidder_c_boq)

print("\n" + "="*60)
print("BSNL TENDER & MULTI-BIDDER DATASET GENERATED SUCCESSFULLY!")
print(f"Location: {DATASET_DIR.resolve()}")
print("="*60)

