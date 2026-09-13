# DocShield AI — SIH Final Demo Build

## What is included
- Professional Flask web application
- SQLite case/audit database
- OCR preprocessing
- Automatic document-type classification
- QR extraction
- Image quality assessment
- Error Level Analysis (ELA) heuristic
- Edge/texture anomaly heuristic
- OCR field-pattern consistency checks
- Face-region detection
- Explainable risk scoring
- Screening history dashboard
- Case IDs and SHA-256 audit hash
- Printable report page
- REST API: `/api/screenings`

## Architecture
Frontend -> Flask API -> Screening Pipeline -> SQLite
                         |-> OCR
                         |-> Computer Vision
                         |-> Image Forensics
                         |-> QR
                         |-> Consistency
                         |-> Risk Engine
                         -> Explainable Report

## Windows setup

Recommended: Python 3.11 or 3.12.

1. Open this folder in VS Code.
2. Open Terminal.
3. Create environment:
   `python -m venv venv`
4. Activate:
   `.\venv\Scripts\Activate.ps1`
5. If activation is blocked:
   `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
   then activate again.
6. Install packages:
   `pip install -r requirements.txt`
7. Install Tesseract OCR for Windows.
8. If Tesseract is not in PATH, edit the commented Tesseract line in `app.py`.
9. Run:
   `python app.py`
10. Open:
   `http://127.0.0.1:5000`

Dashboard:
`http://127.0.0.1:5000/dashboard`

API:
`http://127.0.0.1:5000/api/screenings`

## SIH-level enhancement roadmap already reflected in the design
The architecture is intentionally modular so the prototype can replace heuristics with trained models:
1. Replace ELA heuristic with a trained manipulation detector.
2. Add MRZ parser + checksum validation for passports.
3. Add document-layout model for field localization.
4. Add consent-based face verification + liveness module.
5. Add issuer API / digital-signature verification where an authorized API exists.
6. Add anomaly model trained on synthetic tampering data.
7. Add role-based authentication, encryption and retention policies for deployment.
8. Add an explainability heatmap from the trained vision model.

## Responsible AI
Never claim that the current prototype proves a document is genuine/fake. The score is a triage signal for authorized human review. Use synthetic documents for demonstrations and obtain consent for any face data.

## Demo flow
1. Open Screen.
2. Upload synthetic original document.
3. Show LOW/MEDIUM risk and extracted information.
4. Upload a deliberately edited synthetic copy.
5. Show changed risk/reasons.
6. Open Dashboard.
7. Open the case report.
8. Explain how authoritative verification would be added for production.
