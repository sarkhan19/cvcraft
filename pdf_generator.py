"""
pdf_generator.py
Supports three templates: modern | classic | minimal
Color and photo from CV meta.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.utils import ImageReader
import base64, io, os

PAGE_W, PAGE_H = A4
L = R = 18 * mm
T = B = 16 * mm


def hex_color(h):
    h = h.lstrip("#")
    return colors.HexColor(f"#{h}")


def photo_image(b64str, size=28*mm):
    """Convert base64 photo string to a ReportLab image."""
    try:
        header, data = b64str.split(",", 1)
        img_bytes = base64.b64decode(data)
        buf = io.BytesIO(img_bytes)
        from reportlab.platypus import Image
        img = Image(buf, width=size, height=size)
        img.hAlign = "RIGHT"
        return img
    except Exception:
        return None


def styles_for(accent, template):
    INK   = colors.HexColor("#1c1c1c")
    MUTED = colors.HexColor("#888888")
    ACC   = hex_color(accent)
    WHITE = colors.white

    base = {
        "name": ParagraphStyle("name",
            fontSize=26 if template != "minimal" else 22,
            leading=30, textColor=INK if template != "modern" else WHITE,
            fontName="Helvetica-Bold"),
        "job_title": ParagraphStyle("job_title",
            fontSize=10, leading=13, textColor=ACC if template != "modern" else colors.HexColor("#dddddd"),
            fontName="Helvetica", spaceAfter=2),
        "contact": ParagraphStyle("contact",
            fontSize=8, leading=11,
            textColor=MUTED if template != "modern" else colors.HexColor("#bbbbbb"),
            fontName="Helvetica"),
        "section": ParagraphStyle("section",
            fontSize=9, leading=12, textColor=WHITE,
            fontName="Helvetica-Bold"),
        "company": ParagraphStyle("company",
            fontSize=10, leading=13, textColor=INK,
            fontName="Helvetica-Bold"),
        "position": ParagraphStyle("position",
            fontSize=9, leading=12, textColor=ACC,
            fontName="Helvetica-Bold"),
        "date": ParagraphStyle("date",
            fontSize=8, leading=10, textColor=MUTED,
            fontName="Helvetica"),
        "body": ParagraphStyle("body",
            fontSize=8.5, leading=13, textColor=colors.HexColor("#555555"),
            fontName="Helvetica", spaceAfter=3),
        "summary": ParagraphStyle("summary",
            fontSize=9, leading=14, textColor=colors.HexColor("#444444"),
            fontName="Helvetica"),
        "skill": ParagraphStyle("skill",
            fontSize=8.5, leading=11, textColor=INK,
            fontName="Helvetica-Bold"),
        "lang": ParagraphStyle("lang",
            fontSize=9, leading=12, textColor=INK,
            fontName="Helvetica"),
    }
    return base, ACC, INK, MUTED


def section_bar(title, s, acc, usable_w):
    tbl = Table([[Paragraph(f"  {title.upper()}", s["section"])]],
                colWidths=[usable_w], rowHeights=[7*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), acc),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    return tbl


def section_line(title, s, acc, usable_w):
    """Classic template: title + horizontal rule."""
    return [
        Paragraph(f'<font color="#{acc.hexval()[2:] if hasattr(acc,"hexval") else "333"}">{title.upper()}</font>',
                  ParagraphStyle("sh", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=acc, spaceAfter=1)),
        HRFlowable(width=usable_w, thickness=1, color=acc, spaceAfter=4),
    ]


def section_minimal(title, s, usable_w):
    """Minimal template: just a small caps label."""
    return [Paragraph(title.upper(),
                      ParagraphStyle("sm", fontSize=7.5, fontName="Helvetica-Bold",
                                     textColor=colors.HexColor("#aaaaaa"),
                                     spaceBefore=6, spaceAfter=4,
                                     letterSpacing=2))]


def add_section(story, title, template, s, acc, usable_w):
    story.append(Spacer(1, 3*mm))
    if template == "modern":
        story.append(section_bar(title, s, acc, usable_w))
    elif template == "classic":
        for el in section_line(title, s, acc, usable_w):
            story.append(el)
    else:
        for el in section_minimal(title, s, usable_w):
            story.append(el)
    story.append(Spacer(1, 2*mm))


def exp_block(exp, s, acc, usable_w, story):
    row = Table([[
        Paragraph(exp.get("company",""), s["company"]),
        Paragraph(f"{exp.get('start_date','')} – {exp.get('end_date','')}", s["date"])
    ]], colWidths=[usable_w*0.68, usable_w*0.32])
    row.setStyle(TableStyle([
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("ALIGN",(1,0),(1,0),"RIGHT"),("VALIGN",(0,0),(-1,-1),"BOTTOM"),
    ]))
    story.append(row)
    story.append(Paragraph(exp.get("position",""), s["position"]))
    story.append(Paragraph(exp.get("description",""), s["body"]))
    story.append(Spacer(1, 2*mm))


def skill_chips(skills, s, usable_w, cols=5):
    rows, row = [], []
    for i, sk in enumerate(skills):
        row.append(Paragraph(sk, s["skill"]))
        if (i+1) % cols == 0:
            rows.append(row); row = []
    if row:
        row += [""] * (cols - len(row)); rows.append(row)
    tbl = Table(rows, colWidths=[usable_w/cols]*cols)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f4f4f0")),
        ("GRID",(0,0),(-1,-1),.3,colors.white),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    return tbl


def generate_pdf(data, output_path):
    meta     = data.get("meta", {})
    template = meta.get("template", "modern")
    accent   = meta.get("color", "#2f6b4f")
    p        = data.get("personal", {})

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=L, rightMargin=R,
                            topMargin=T, bottomMargin=B)
    usable_w = PAGE_W - L - R
    s, ACC, INK, MUTED = styles_for(accent, template)
    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    name_para    = Paragraph(p.get("name",""), s["name"])
    title_para   = Paragraph(p.get("title",""), s["job_title"])
    contact_text = "  |  ".join(filter(None, [
        p.get("email"), p.get("phone"), p.get("location"),
        p.get("linkedin"), p.get("github")
    ]))
    contact_para = Paragraph(contact_text, s["contact"])

    photo_el = None
    if meta.get("photo"):
        photo_el = photo_image(meta["photo"])

    if template == "modern":
        # Dark background header
        if photo_el:
            header_content = [[
                [name_para, Spacer(1,2), title_para, Spacer(1,4), contact_para],
                photo_el
            ]]
            col_w = [usable_w*0.78, usable_w*0.22]
        else:
            header_content = [[[name_para, Spacer(1,2), title_para, Spacer(1,4), contact_para]]]
            col_w = [usable_w]

        hdr = Table(header_content, colWidths=col_w)
        hdr.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),INK),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        story.append(hdr)

    else:
        # Classic / Minimal: light header
        if photo_el:
            row = Table([[
                [name_para, Spacer(1,2), title_para, Spacer(1,4), contact_para],
                photo_el
            ]], colWidths=[usable_w*0.78, usable_w*0.22])
            row.setStyle(TableStyle([
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ]))
            story.append(row)
        else:
            story.append(name_para)
            story.append(Spacer(1,2))
            story.append(title_para)
            story.append(Spacer(1,3))
            story.append(contact_para)

        story.append(HRFlowable(width=usable_w, thickness=1.5,
                                color=ACC, spaceBefore=6, spaceAfter=4))

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    if p.get("summary"):
        add_section(story, "Profile", template, s, ACC, usable_w)
        story.append(Paragraph(p["summary"], s["summary"]))

    # ── EXPERIENCE ────────────────────────────────────────────────────────────
    if data.get("experience"):
        add_section(story, "Experience", template, s, ACC, usable_w)
        for exp in data["experience"]:
            exp_block(exp, s, ACC, usable_w, story)

    # ── EDUCATION ─────────────────────────────────────────────────────────────
    if data.get("education"):
        add_section(story, "Education", template, s, ACC, usable_w)
        for edu in data["education"]:
            row = Table([[
                Paragraph(edu.get("institution",""), s["company"]),
                Paragraph(f"{edu.get('start_date','')} – {edu.get('end_date','')}", s["date"])
            ]], colWidths=[usable_w*0.68, usable_w*0.32])
            row.setStyle(TableStyle([
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                ("ALIGN",(1,0),(1,0),"RIGHT"),("VALIGN",(0,0),(-1,-1),"BOTTOM"),
            ]))
            story.append(row)
            deg = f"{edu.get('degree','')} in {edu.get('field','')}"
            if edu.get("gpa"): deg += f"  •  GPA {edu['gpa']}"
            story.append(Paragraph(deg, s["body"]))
            story.append(Spacer(1,2*mm))

    # ── SKILLS ────────────────────────────────────────────────────────────────
    tech = data.get("skills",{}).get("technical",[])
    soft = data.get("skills",{}).get("soft",[])
    if tech or soft:
        add_section(story, "Skills", template, s, ACC, usable_w)
        if tech:
            story.append(Paragraph("<b>Technical</b>", s["body"]))
            story.append(skill_chips(tech, s, usable_w))
            story.append(Spacer(1,2*mm))
        if soft:
            story.append(Paragraph("<b>Soft Skills</b>", s["body"]))
            story.append(skill_chips(soft, s, usable_w, cols=4))

    # ── LANGUAGES + CERTS ─────────────────────────────────────────────────────
    langs = data.get("languages",[])
    certs = data.get("certifications",[])
    if langs or certs:
        add_section(story, "Languages & Certifications", template, s, ACC, usable_w)
        left, right = [], []
        for ln in langs:
            left.append(Paragraph(f"<b>{ln.get('language','')}</b>  –  {ln.get('level','')}", s["lang"]))
            left.append(Spacer(1,1*mm))
        for ct in certs:
            right.append(Paragraph(f"<b>{ct.get('name','')}</b>", s["body"]))
            right.append(Paragraph(f"{ct.get('issuer','')}  •  {ct.get('year','')}", s["date"]))
            right.append(Spacer(1,2*mm))
        if left or right:
            tbl = Table([[left or [""], right or [""]]],
                        colWidths=[usable_w*0.48, usable_w*0.48])
            tbl.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
            ]))
            story.append(tbl)

    doc.build(story)
    return output_path
