import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

os.makedirs("sample_tenders", exist_ok=True)
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "GovTitle",
    parent=styles["Heading1"],
    fontSize=14,
    leading=18,
    alignment=1,
    textColor=colors.navy,
)
h2_style = ParagraphStyle(
    "GovH2",
    parent=styles["Heading2"],
    fontSize=11,
    leading=14,
    textColor=colors.black,
)
body_style = ParagraphStyle(
    "GovBody",
    parent=styles["Normal"],
    fontSize=9,
    leading=12,
)

tenders_spec = [
    {
        "filename": "mtd_goods_nic.pdf",
        "title": "GOVERNMENT OF INDIA - MODEL TENDER DOCUMENT FOR PROCUREMENT OF GOODS",
        "dept": "Department of Expenditure, Ministry of Finance",
        "pages": 18,
        "content": [
            ("SECTION I: NOTICE INVITING TENDER (NIT)", "Ref: MTD/GOODS/2021/V01. This Notice Inviting Tender does not purport to contain all relevant details for bid submission. Bidders must examine the complete Tender Document."),
            ("SECTION II: TENDER INFORMATION SUMMARY (TIS)", "Estimated Value: Rs. 50,00,000. EMD Amount: Rs. 1,00,000. Bid submission closing date: 24-10-2026. Micro and Small Enterprises (MSEs) registered with Udyam are exempt from payment of EMD."),
            ("SECTION III: INSTRUCTIONS TO BIDDERS (ITB)", "Clause 4.1: Eligibility. Minimum average annual turnover of Rs. 25,00,000 during the last three financial years. Valid Class 3 DSC mandatory."),
            ("ANNEXURE IV: BID SECURITY DECLARATION", "MSE bidders claiming exemption must furnish signed Bid Security Declaration as per format prescribed under GFR 2017 Rule 170."),
        ],
    },
    {
        "filename": "up_pwd_road_works.pdf",
        "title": "OFFICE OF THE EXECUTIVE ENGINEER, PWD DIVISION 1, LUCKNOW",
        "dept": "Public Works Department, Government of Uttar Pradesh",
        "pages": 14,
        "content": [
            ("NIT NO. 142/EE/PWD/2026", "Notice Inviting Tender for Special Repairs and Resurfacing of Rural Road Links in Lucknow District. Estimated Cost: Rs. 75,00,000."),
            ("CRITICAL DATES & EMD", "EMD amount: Rs. 1,50,000 as FDR/Bank Guarantee. Submission deadline: 18-10-2026. Bids must be submitted online on upetender.gov.in."),
            ("ELIGIBILITY & TURNOVER", "Clause 8: The bidder must have achieved a minimum annual turnover of Rs. 45,00,000 in any of the last three financial years. Must have executed 3 similar road works."),
            ("EXEMPTIONS", "Clause 14(b): Micro and Small Enterprises registered under Udyam in manufacturing/civil works category are exempt from EMD upon submission of BSD."),
        ],
    },
    {
        "filename": "karnataka_jjm_water.pdf",
        "title": "RURAL DRINKING WATER AND SANITATION DEPARTMENT, BENGALURU",
        "dept": "Jal Jeevan Mission, Government of Karnataka",
        "pages": 16,
        "content": [
            ("TENDER NOTIFICATION JJM/RDWSD/2026/089", "Implementation of Retrofitting Multi-Village Scheme Pipeline Works. Contract Value: Rs. 1,20,00,000."),
            ("BID SECURITY & DATES", "Earnest Money Deposit: Rs. 2,00,000 payable via e-Payment. Bid submission closing date: 15-10-2026."),
            ("QUALIFICATION CRITERIA", "Contractor must have class-1 civil registration and minimum turnover of Rs. 60,00,000. Experience of having completed minimum 2 water supply schemes."),
            ("STATUTORY EXEMPTIONS", "MSE exemption as per Karnataka Transparency in Public Procurements (KTPP) and MSMED Act 2006 applicable for local manufacturing units."),
        ],
    },
    {
        "filename": "bccl_coal_handling.pdf",
        "title": "BHARAT COKING COAL LIMITED - DHANBAD",
        "dept": "A Subsidiary of Coal India Limited / Ministry of Coal",
        "pages": 24,
        "content": [
            ("OPEN TENDER NOTICE BCCL/CMC/2026/04", "Civil and structural foundation work for Coal Handling Plant expansion. Estimated tender value: Rs. 2,50,00,000."),
            ("EMD & SECURITY CLAUSE", "EMD: Rs. 5,00,000. Online deposit through Coal India e-Procurement Portal. Bid validity: 180 days."),
            ("TECHNICAL CRITERIA", "Clause 12: Experience of having successfully completed 3 similar civil works each costing not less than Rs. 80,00,000 in past 5 years. Annual turnover: Rs. 1,00,00,000."),
            ("MSE EXEMPTION CLAUSE", "Clause 19: DPIIT recognized Startups and MSEs eligible for exemption from EMD as per GFR 2017 Rule 170 and 173 upon submitting proof of registration."),
        ],
    },
    {
        "filename": "upneda_solar_lights.pdf",
        "title": "UTTAR PRADESH NEW AND RENEWABLE ENERGY DEVELOPMENT AGENCY (UPNEDA)",
        "dept": "Government of Uttar Pradesh, Lucknow",
        "pages": 15,
        "content": [
            ("TENDER NO. 02/UPNEDA/SOLAR/2026", "Design, Supply, Installation & Commissioning of 2,000 Solar LED Street Lighting Systems in Tier-3 Panchayats."),
            ("TENDER PARTICULARS", "Estimated Cost: Rs. 40,00,000. Earnest Money Deposit: Rs. 80,000. Last date of bid submission: 22-10-2026 15:00."),
            ("FINANCIAL ELIGIBILITY", "Minimum average turnover of Rs. 20,00,000 during the last 3 financial years. Bidder must be MNRE or ISO 9001 certified solar integrator."),
            ("MSME POLICY CLAUSE", "UP Micro and Small Enterprises holding valid Udyam certificate are 100% exempt from EMD. Medium enterprises must deposit full EMD."),
        ],
    },
    {
        "filename": "aiims_ppe_supply.pdf",
        "title": "ALL INDIA INSTITUTE OF MEDICAL SCIENCES, NEW DELHI",
        "dept": "Store Section (Hospital), Ansari Nagar",
        "pages": 12,
        "content": [
            ("TENDER REF: AIIMS/HOSP/PPE/2026/11", "Annual Rate Contract for supply of Certified Sterile Medical PPE Kits, Examination Gloves, and N95 Masks."),
            ("EARNEST MONEY & FEES", "EMD: Rs. 40,00,000. Fixed EMD: Rs. 40,000. Submission deadline: 19-10-2026. Only online bids via CPPP."),
            ("QUALITY STANDARDS", "Mandatory ISO 13485 certification and CE/BIS compliance. Minimum annual turnover of Rs. 15,00,000."),
            ("SPECIAL MSE PROVISION", "Micro and Small enterprises exempted from EMD and tender fee as per Central Public Procurement Policy. Traders strictly not eligible for exemption."),
        ],
    },
    {
        "filename": "smart_classroom_displays.pdf",
        "title": "STATE EDUCATION INFRASTRUCTURE DEVELOPMENT CORPORATION",
        "dept": "Department of School Education",
        "pages": 18,
        "content": [
            ("NIT NO: SEIDC/EQUIP/2026/07", "Procurement and setup of 4K Interactive Flat Panels for Government Senior Secondary Schools."),
            ("EMD & DEADLINE", "Earnest Money Deposit: Rs. 1,20,000. Submission deadline: 28-10-2026. Two-cover system (Technical & Financial)."),
            ("REQUIREMENTS", "Minimum turnover of Rs. 50,00,000. OEM Authorization Form (MAF) required. Class 3 DSC token mandatory."),
            ("EXEMPTION CLAUSE", "Registered MSE manufacturers exempt from EMD under GFR Rule 170 with valid Udyam certificate on bid opening date."),
        ],
    },
    {
        "filename": "cpwd_facility_management.pdf",
        "title": "CENTRAL PUBLIC WORKS DEPARTMENT - NORTHERN REGION",
        "dept": "Ministry of Housing and Urban Affairs",
        "pages": 20,
        "content": [
            ("PRESS NOTICE INVITING TENDER", "Comprehensive Integrated Facility Management and Mechanized Housekeeping Services at Kendriya Sadan Complex."),
            ("CRITICAL PARTICULARS", "Estimated tender value: Rs. 30,00,000. EMD Amount: Rs. 60,000. Closing Date: 25-10-2026."),
            ("EXPERIENCE & TURNOVER", "Annual turnover Rs. 30,00,000 in past 3 financial years. Experience: 3 years in commercial facility management."),
            ("EXEMPTIONS & DSC", "Exemption for Micro and Small Enterprises as per MSME procurement policy 2012. Class 3 DSC required for eprocure.gov.in."),
        ],
    },
    {
        "filename": "nicsi_cloud_maintenance.pdf",
        "title": "NATIONAL INFORMATICS CENTRE SERVICES INC. (NICSI)",
        "dept": "Ministry of Electronics and Information Technology",
        "pages": 22,
        "content": [
            ("RFP REF: NICSI/DATA-CTR/2026/41", "Request for Proposal for 24x7 Infrastructure Operations and Managed Services for State Cloud Data Centers."),
            ("BID SPECIFICATIONS", "Estimated Value: Rs. 85,00,000. EMD: Rs. 1,00,000. Submission deadline: 30-10-2026. Portal: eprocure.gov.in."),
            ("CERTIFICATIONS & TURNOVER", "ISO 27001 (Information Security) and ISO 9001 mandatory. Average turnover: Rs. 40,00,000 in last 3 financial years."),
            ("STARTUP & MSE RELAXATIONS", "DPIIT recognized Startups and MSEs eligible for relaxation in prior experience and EMD under GFR 170 and 173."),
        ],
    },
    {
        "filename": "up_jal_nigam_hindi.pdf",
        "title": "उत्तर प्रदेश जल निगम (ग्रामीण) - निविदा आमंत्रण सूचना",
        "dept": "नमामि गंगे एवं ग्रामीण जलापूर्ति विभाग, उत्तर प्रदेश",
        "pages": 14,
        "content": [
            ("निविदा सूचना संख्या: 18/ज.नि./2026", "ग्राम पेयजल योजना अंतर्गत ओवरहेड टैंक एवं वितरण प्रणाली निर्माण कार्य। अनुमानित लागत: ₹45,00,000।"),
            ("बयाना राशि एवं महत्वपूर्ण तिथियां", "बयाना राशि (EMD): ₹50,000 राष्ट्रीयकृत बैंक की एफडीआर/बैंक गारंटी के रूप में। निविदा प्रस्तुत करने की अंतिम तिथि: 21-10-2026।"),
            ("पात्रता एवं वार्षिक कारोबार", "बोलीदाता का पिछले 3 वित्तीय वर्षों में न्यूनतम औसत वार्षिक कारोबार ₹25,00,000 होना अनिवार्य है।"),
            ("एमएसएमई छूट प्रावधान", "सूक्ष्म एवं लघु उद्यमों (MSEs) को जीएफआर नियम 170 के अनुसार बयाना राशि से पूर्ण छूट प्रदान की जाएगी।"),
        ],
    },
    {
        "filename": "scanned_police_housing.pdf",
        "title": "STATE POLICE HOUSING CORPORATION LIMITED",
        "dept": "Police Headquarters, Administrative Wing",
        "pages": 10,
        "content": [
            ("NOTICE INVITING TENDER NO. 54", "Construction of Barracks and Administrative Block at District Police Line."),
            ("COMMERCIAL CLAUSES", "EMD: Rs. 75,000 payable by Demand Draft. Tender submission deadline: 16-10-2026."),
            ("PRE-QUALIFICATION", "Minimum turnover: Rs. 35,00,000. Class 2 or 3 Civil Contractor registration certificate."),
            ("DISCLAIMER", "Departmental scanned copy. Micro/Small enterprises exempted from EMD subject to Udyam certificate verification."),
        ],
    },
    {
        "filename": "nhai_highway_toll.pdf",
        "title": "NATIONAL HIGHWAYS AUTHORITY OF INDIA (NHAI)",
        "dept": "Ministry of Road Transport and Highways",
        "pages": 52,
        "content": [
            ("RFP FOR USER FEE COLLECTION AT TOLL PLAZA", "Operation and Maintenance of Toll Plaza on NH-24. Contract Period: 1 Year. Estimated Value: Rs. 8,00,00,000."),
            ("BID SECURITY REQUIREMENTS", "EMD Amount: Rs. 10,00,000 in the form of Bank Guarantee. Bid submission closing: 02-11-2026."),
            ("FINANCIAL THRESHOLD", "Minimum Net Worth of Rs. 1,50,00,000 and minimum annual turnover of Rs. 2,00,00,000 in past 3 financial years."),
            ("CONDITIONS OF BIDDING", "Clause 42: Bidders must possess Class 3 DSC. MSE exemption applies only to manufacturing/service providers, not fee-collection concessionaires."),
        ],
    },
    {
        "filename": "tn_highways_short_deadline.pdf",
        "title": "HIGHWAYS DEPARTMENT, GOVERNMENT OF TAMIL NADU",
        "dept": "Construction and Maintenance Wing, Chennai",
        "pages": 14,
        "content": [
            ("SHORT TENDER NOTICE NO. TN-HW/2026/09", "Urgent Restoration and Bridge Culvert Reconstruction after Monsoon Inundation. Urgent Window."),
            ("CRITICAL TIMING BARRIER", "EMD Amount: Rs. 30,000. Tender published: 04-10-2026. Bid submission deadline: 09-10-2026 (5 Days Window)."),
            ("DSC & REGISTRATION", "Mandatory Class 3 Digital Signature Certificate. Note: Prospective bidders lacking active DSC cannot obtain token within 5 days."),
            ("MSE EXEMPTION", "Exemption for Micro and Small Enterprises as per Tamil Nadu Transparency in Tenders Act. Bid Security Declaration accepted."),
        ],
    },
]

for spec in tenders_spec:
    filepath = os.path.join("sample_tenders", spec["filename"])
    doc = SimpleDocTemplate(filepath, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    story.append(Paragraph(spec["title"], title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Issuing Authority:</b> {spec['dept']}", body_style))
    story.append(Spacer(1, 14))

    for header, text in spec["content"]:
        story.append(Paragraph(header, h2_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 10))

    # Add filler pages to meet target page count
    target_pages = spec.get("pages", 12)
    for p in range(1, target_pages):
        story.append(PageBreak())
        story.append(Paragraph(f"<b>{spec['title']} — Page {p+1} of {target_pages}</b>", h2_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"General Conditions and Standard Contract Clauses. Detailed specifications, bill of quantities (BOQ), "
            f"and compliance schedules continued. All clauses governed by GFR 2017 and procurement guidelines.",
            body_style
        ))
        story.append(Spacer(1, 15))

    doc.build(story)
    print(f"Generated {filepath} ({target_pages} pages)")

print("All 13 sample tender PDFs generated successfully in sample_tenders/.")
