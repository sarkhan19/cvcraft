"""
app.py — CVcraft
Cookie-based sessions, multiple CVs per user.
DATA_DIR env variable points to persistent storage (Railway volume).
"""

from flask import (Flask, render_template, request,
                   redirect, url_for, send_file, flash,
                   make_response)
import json, os, tempfile, uuid, base64
from pdf_generator import generate_pdf

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cvcraft-dev-secret")

# On Railway: set DATA_DIR=/data in environment variables
# Locally: defaults to ./data folder next to app.py
DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.join(os.path.dirname(__file__), "data")
)
os.makedirs(DATA_DIR, exist_ok=True)


# ── EMPTY CV TEMPLATE ─────────────────────────────────────────────────────────
def empty_cv(title="My CV"):
    return {
        "meta": {
            "title":    title,
            "template": "modern",
            "color":    "#2f6b4f",
            "lang":     "en",
            "photo":    "",
            "public":   False,
        },
        "personal": {
            "name": "", "title": "", "email": "", "phone": "",
            "location": "", "linkedin": "", "github": "", "summary": ""
        },
        "experience":     [],
        "education":      [],
        "skills":         {"technical": [], "soft": []},
        "languages":      [],
        "certifications": []
    }


# ── FILE HELPERS ──────────────────────────────────────────────────────────────
def get_user_id():
    return request.cookies.get("user_id")

def user_dir(user_id):
    path = os.path.join(DATA_DIR, user_id)
    os.makedirs(path, exist_ok=True)
    return path

def index_path(user_id):
    return os.path.join(user_dir(user_id), "index.json")

def cv_path(user_id, cv_id):
    return os.path.join(user_dir(user_id), f"{cv_id}.json")

def load_index(user_id):
    p = index_path(user_id)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return []

def save_index(user_id, idx):
    with open(index_path(user_id), "w") as f:
        json.dump(idx, f, indent=2)

def load_cv(user_id, cv_id):
    p = cv_path(user_id, cv_id)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None

def save_cv(user_id, cv_id, data):
    with open(cv_path(user_id, cv_id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── FORM PARSER ───────────────────────────────────────────────────────────────
def parse_form(f, existing):
    data = existing.copy()

    # Keep existing meta, then update from form
    meta = existing.get("meta") or {}
    meta["template"] = f.get("template", "modern")
    meta["color"]    = f.get("color", "#2f6b4f")
    meta["lang"]     = f.get("lang", "en")
    meta["public"]   = f.get("public") == "on"
    data["meta"] = meta

    # Photo upload
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        img_bytes = photo_file.read()
        ext  = photo_file.filename.rsplit(".", 1)[-1].lower()
        mime = "image/png" if ext == "png" else "image/jpeg"
        data["meta"]["photo"] = f"data:{mime};base64," + base64.b64encode(img_bytes).decode()
    elif f.get("remove_photo") == "1":
        data["meta"]["photo"] = ""

    data["personal"] = {
        "name":     f.get("name",     "").strip(),
        "title":    f.get("title",    "").strip(),
        "email":    f.get("email",    "").strip(),
        "phone":    f.get("phone",    "").strip(),
        "location": f.get("location", "").strip(),
        "linkedin": f.get("linkedin", "").strip(),
        "github":   f.get("github",   "").strip(),
        "summary":      f.get("summary",      "").strip(),
        "website_name": f.get("website_name", "").strip(),
        "website_url":  f.get("website_url",  "").strip(),
    }

    companies  = f.getlist("exp_company")
    positions  = f.getlist("exp_position")
    locations  = f.getlist("exp_location")
    starts     = f.getlist("exp_start")
    ends       = f.getlist("exp_end")
    descs      = f.getlist("exp_description")
    data["experience"] = [
        {"id": i+1, "company": companies[i], "position": positions[i],
         "location": locations[i] if i < len(locations) else "",
         "start_date": starts[i], "end_date": ends[i], "description": descs[i]}
        for i in range(len(companies)) if companies[i].strip()
    ]

    institutions = f.getlist("edu_institution")
    degrees      = f.getlist("edu_degree")
    fields       = f.getlist("edu_field")
    edu_starts   = f.getlist("edu_start")
    edu_ends     = f.getlist("edu_end")
    gpas         = f.getlist("edu_gpa")
    data["education"] = [
        {"id": i+1, "institution": institutions[i], "degree": degrees[i],
         "field": fields[i], "start_date": edu_starts[i],
         "end_date": edu_ends[i], "gpa": gpas[i]}
        for i in range(len(institutions)) if institutions[i].strip()
    ]

    data["skills"] = {
        "technical": [s.strip() for s in f.get("tech_skills","").split(",") if s.strip()],
        "soft":      [s.strip() for s in f.get("soft_skills","").split(",") if s.strip()],
    }

    lang_names  = f.getlist("lang_name")
    lang_levels = f.getlist("lang_level")
    data["languages"] = [
        {"language": lang_names[i], "level": lang_levels[i]}
        for i in range(len(lang_names)) if lang_names[i].strip()
    ]

    cert_names   = f.getlist("cert_name")
    cert_issuers = f.getlist("cert_issuer")
    cert_years   = f.getlist("cert_year")
    data["certifications"] = [
        {"name": cert_names[i], "issuer": cert_issuers[i], "year": cert_years[i]}
        for i in range(len(cert_names)) if cert_names[i].strip()
    ]

    return data


# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    user_id  = get_user_id()
    new_user = not user_id
    if new_user:
        user_id = str(uuid.uuid4())

    cvs  = load_index(user_id)
    resp = make_response(render_template("index.html", cvs=cvs, user_id=user_id))
    if new_user:
        resp.set_cookie("user_id", user_id, max_age=60*60*24*365,
                        httponly=True, samesite="Lax")
    return resp


@app.route("/new")
def new_cv():
    user_id = get_user_id()
    if not user_id:
        return redirect(url_for("index"))

    cv_id = str(uuid.uuid4())[:8]
    title = request.args.get("title", "My CV")
    save_cv(user_id, cv_id, empty_cv(title))

    idx = load_index(user_id)
    idx.append({"id": cv_id, "title": title})
    save_index(user_id, idx)

    return redirect(url_for("edit_cv", cv_id=cv_id))


@app.route("/cv/<cv_id>")
def view_cv(cv_id):
    user_id = get_user_id()
    if not user_id:
        return redirect(url_for("index"))
    data = load_cv(user_id, cv_id)
    if not data:
        flash("CV not found.")
        return redirect(url_for("index"))
    return render_template("preview.html", data=data, cv_id=cv_id, owner=True)


@app.route("/share/<user_id>/<cv_id>")
def share_cv(user_id, cv_id):
    data = load_cv(user_id, cv_id)
    if not data or not data.get("meta", {}).get("public"):
        flash("This CV is not publicly shared.")
        return redirect(url_for("index"))
    return render_template("preview.html", data=data, cv_id=cv_id, owner=False)


@app.route("/cv/<cv_id>/edit", methods=["GET", "POST"])
def edit_cv(cv_id):
    user_id = get_user_id()
    if not user_id:
        return redirect(url_for("index"))

    data = load_cv(user_id, cv_id)
    if not data:
        flash("CV not found.")
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("edit.html", data=data, cv_id=cv_id)

    data = parse_form(request.form, data)
    save_cv(user_id, cv_id, data)

    # Update title in index
    idx = load_index(user_id)
    for item in idx:
        if item["id"] == cv_id:
            item["title"] = data["personal"].get("name") or data["meta"].get("title", "My CV")
    save_index(user_id, idx)

    flash("Saved successfully!")
    return redirect(url_for("view_cv", cv_id=cv_id))


@app.route("/cv/<cv_id>/delete")
def delete_cv(cv_id):
    user_id = get_user_id()
    if not user_id:
        return redirect(url_for("index"))

    p = cv_path(user_id, cv_id)
    if os.path.exists(p):
        os.remove(p)

    idx = [x for x in load_index(user_id) if x["id"] != cv_id]
    save_index(user_id, idx)
    flash("CV deleted.")
    return redirect(url_for("index"))


@app.route("/cv/<cv_id>/download")
def download_cv(cv_id):
    user_id = get_user_id()
    if not user_id:
        return redirect(url_for("index"))

    data = load_cv(user_id, cv_id)
    if not data:
        flash("CV not found.")
        return redirect(url_for("index"))

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    generate_pdf(data, tmp.name)

    name = (data["personal"].get("name") or "CV").replace(" ", "_")
    return send_file(tmp.name, as_attachment=True,
                     download_name=f"{name}_CV.pdf",
                     mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
