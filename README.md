# CV Generator App

A web application that stores CV data in a JSON database and generates a professional PDF.

## Project Structure

```
cv_app/
├── app.py            ← Flask web server (main entry point)
├── pdf_generator.py  ← PDF creation logic (ReportLab)
├── database.json     ← Your CV data (the "database")
├── run.sh            ← One-click start script
└── templates/
    ├── index.html    ← CV preview page
    └── edit.html     ← CV editor form
```

## How to Run

### Option 1 – Shell script (easiest)
```bash
bash run.sh
```

### Option 2 – Manual
```bash
pip install flask reportlab
python3 app.py
```

Then open **http://localhost:5000** in your browser.

## How It Works

1. **database.json** stores all your CV data (name, experience, skills, etc.)
2. The **Flask app** (app.py) reads this file and shows it in the browser
3. You can **edit** your CV through the web form — changes are saved back to database.json
4. Click **Download PDF** to generate a professional PDF using ReportLab

## Routes

| URL | What it does |
|-----|-------------|
| `/` | Preview your CV |
| `/edit` | Edit your CV in a form |
| `/save` | Saves form data (POST) |
| `/download` | Generates and downloads the PDF |
