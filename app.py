from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import sqlite3, json, hashlib, re, uuid
from datetime import datetime
import cv2, numpy as np, pytesseract
from PIL import Image, ImageChops, ImageEnhance
from agent import run_agent
from document_analyzer import analyze_document
BASE = Path(__file__).resolve().parent
DB = BASE / "screening.db"
UPLOADS, REPORTS = BASE/"uploads", BASE/"reports"
UPLOADS.mkdir(exist_ok=True); REPORTS.mkdir(exist_ok=True)
app = Flask(__name__)
app.secret_key = "change-this-secret-key"
ALLOWED = {"png","jpg","jpeg","webp"}

# If Tesseract is installed but not in PATH on Windows, set:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS screenings(
      id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT UNIQUE, filename TEXT,
      doc_type TEXT, risk INTEGER, level TEXT, status TEXT, created_at TEXT,
      sha256 TEXT, result_json TEXT)""")
    c.commit(); c.close()

def allowed(n): return "." in n and n.rsplit(".",1)[1].lower() in ALLOWED

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(65536), b""): h.update(b)
    return h.hexdigest()

def preprocess(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    gray=cv2.resize(gray,None,fx=1.7,fy=1.7,interpolation=cv2.INTER_CUBIC)
    gray=cv2.bilateralFilter(gray,7,50,50)
    return cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]

def ocr(img):
    return pytesseract.image_to_string(preprocess(img), config="--psm 6").strip()

def detect_qr(img):
    data, pts, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return data.strip() if data else ""

def classify(text, img):
    t=text.lower()
    if "passport" in t or "nationality" in t or "date of expiry" in t or "mrz" in t:
        return "Passport / Travel Document"
    if "visa" in t or "entry permit" in t:
        return "Visa / Permit"
    if "certificate" in t or "university" in t or "degree" in t:
        return "Certificate"
    if "identity" in t or "date of birth" in t or "dob" in t:
        return "Identity Document"
    h,w=img.shape[:2]
    ratio=w/h if h else 0
    return "Identity / Official Document" if ratio>1.25 else "Official Document"

def image_quality(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    sharp=float(cv2.Laplacian(gray,cv2.CV_64F).var())
    bright=float(gray.mean())
    q=100; reasons=[]
    if sharp<70: q-=25; reasons.append("Low sharpness / possible blur.")
    elif sharp<150: q-=8
    if bright<45 or bright>220: q-=15; reasons.append("Unusual brightness or exposure.")
    return max(0,round(q)),reasons

def ela(path):
    a=Image.open(path).convert("RGB")
    tmp=REPORTS/f"ela_{uuid.uuid4().hex}.jpg"
    a.save(tmp,quality=90)
    b=Image.open(tmp).convert("RGB")
    d=ImageChops.difference(a,b)
    d=ImageEnhance.Brightness(d).enhance(10)
    s=float(np.asarray(d,dtype=np.float32).mean())
    tmp.unlink(missing_ok=True)
    return round(s,2)

def texture_signal(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,80,180)
    density=float(np.mean(edges>0))
    if density<.006 or density>.28: return 10,"Unusual edge/texture distribution."
    return 0,""

def text_checks(text):
    t=text.lower(); penalty=0; checks=[]
    patterns=[
      ("Date",r"\b(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.](?:19|20)\d{2}\b"),
      ("Phone",r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"),
      ("Email",r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
      ("ID-like number",r"\b[A-Z0-9]{6,20}\b")
    ]
    for label,p in patterns:
        m=re.findall(p,text,re.I)
        checks.append({"name":label,"status":"Found" if m else "Not found","detail":f"{len(m)} match(es)"})
    if len(text)<20:
        penalty+=10
        checks.append({"name":"OCR completeness","status":"Review","detail":"Very little readable text extracted."})
    if re.search(r"[^\x00-\x7F]{3,}",text):
        penalty+=4
        checks.append({"name":"Character anomaly","status":"Review","detail":"Unexpected character sequence."})
    return penalty,checks

def face_presence(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    cascade=cv2.CascadeClassifier(str(Path(cv2.data.haarcascades)/"haarcascade_frontalface_default.xml"))
    faces=cascade.detectMultiScale(gray,1.1,5,minSize=(50,50))
    return len(faces)

def analyze(path):
    img=cv2.imread(str(path))
    if img is None: raise ValueError("Unsupported or unreadable image.")
    text=ocr(img)
    doc_type=classify(text,img)
    q,qreasons=image_quality(img)
    qr=detect_qr(img)
    e=ela(path)
    tp,tr=texture_signal(img)
    fp,checks=text_checks(text)
    faces=face_presence(img)

    risk=0; reasons=[]
    if e>18: risk+=25; reasons.append("Elevated image-forensics (ELA) signal.")
    elif e>10: risk+=10; reasons.append("Moderate image-forensics signal; manual review recommended.")
    risk+=tp
    if tr: reasons.append(tr)
    risk+=fp
    if q<70: risk+=10; reasons += qreasons
    if not text: risk+=15; reasons.append("OCR could not extract meaningful text.")
    if faces==0: reasons.append("No detectable face region; verify document type manually.")
    elif faces>1: risk+=8; reasons.append("Multiple face regions detected; review identity context.")
    if qr: reasons.append("Machine-readable QR data detected and extracted for cross-check.")
    else: reasons.append("No readable QR code detected.")

    risk=min(100,int(risk))
    level="HIGH" if risk>=60 else ("MEDIUM" if risk>=30 else "LOW")
    status="REVIEW REQUIRED" if level!="LOW" else "SCREENING PASSED"
    if not reasons: reasons=["No strong prototype-level anomaly signal detected."]
    return {
      "doc_type":doc_type,"risk":risk,"level":level,"status":status,
      "text":text,"qr":qr,"quality":q,"ela":e,"faces":int(faces),
      "checks":checks,"reasons":reasons,"dimensions":f"{img.shape[1]} × {img.shape[0]}",
      "sha256":sha256(path),"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "limitations":[
        "AI screening is an assistive signal, not proof that a document is genuine or forged.",
        "Official authenticity must be confirmed through authorized issuer/government systems.",
        "Face verification and liveness require a separate consent-based identity capture module."
      ]
    }

def save_case(filename,result):
    case="CASE-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:5].upper()
    c=db()
    c.execute("""INSERT INTO screenings(case_id,filename,doc_type,risk,level,status,created_at,sha256,result_json)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
              (case,filename,result["doc_type"],result["risk"],result["level"],result["status"],
               result["timestamp"],result["sha256"],json.dumps(result)))
    c.commit(); c.close()
    return case

@app.route("/",methods=["GET","POST"])
def index():
    if request.method=="POST":
        f=request.files.get("document")
        if not f or not f.filename: flash("Select a document image."); return redirect(url_for("index"))
        if not allowed(f.filename): flash("Use PNG, JPG, JPEG or WEBP."); return redirect(url_for("index"))
        name=secure_filename(f.filename)
        path=UPLOADS/(uuid.uuid4().hex+"_"+name); f.save(path)
        try:
            result=analyze(path); case=save_case(name,result)
        except Exception as ex:
            path.unlink(missing_ok=True); flash("Analysis error: "+str(ex)); return redirect(url_for("index"))
        return render_template("result.html",result=result,case=case,filename=name)
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    c=db(); rows=c.execute("SELECT * FROM screenings ORDER BY id DESC").fetchall()
    stats={
      "total":len(rows),"high":sum(r["level"]=="HIGH" for r in rows),
      "medium":sum(r["level"]=="MEDIUM" for r in rows),
      "low":sum(r["level"]=="LOW" for r in rows)
    }
    return render_template("dashboard.html",rows=rows,stats=stats)

@app.route("/api/screenings")
def api_screenings():
    c=db(); rows=c.execute("SELECT case_id,filename,doc_type,risk,level,status,created_at FROM screenings ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/report/<case_id>")
def report(case_id):
    c=db(); row=c.execute("SELECT * FROM screenings WHERE case_id=?",(case_id,)).fetchone()
    if not row: return "Case not found",404
    result=json.loads(row["result_json"])
    return render_template("report.html",result=result,case=row["case_id"],filename=row["filename"])

init_db()
if __name__=="__main__":
    app.run(host="127.0.0.1",port=5000,debug=True)
