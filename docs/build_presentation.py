"""Build editable PRESENTATION.pptx and a matching vector PRESENTATION.pdf.

Run from any directory with Python 3.11+, python-pptx and pymupdf installed:
    python docs/build_presentation.py
No network access, source dataset, screenshots or template PDF is required.
The source PDF inspired the design only; all slide elements are created here.
"""
from pathlib import Path
import math
import pymupdf as fitz
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

OUT = Path(__file__).resolve().parent
W, H = 1440, 810
BG, INK, ORANGE, MUTED = '#F7F7F7', '#262626', '#F2620F', '#575757'
PALETTE = ['#F8D2BE', '#F7B494', '#F6A073', '#F68D54', '#F4772B', '#F2620F']
# Portable substitution: Aileron is used in the reference but is not installed.
FONT = 'Liberation Sans'
REG = '/run/current-system/sw/share/fonts/truetype/LiberationSans-Regular.ttf'
BOLD = '/run/current-system/sw/share/fonts/truetype/LiberationSans-Bold.ttf'


def fontfile(bold=False):
    import subprocess
    name = 'Liberation Sans:style=Bold' if bold else 'Liberation Sans:style=Regular'
    return subprocess.check_output(['fc-match', '-f', '%{file}', name], text=True).strip()


REG, BOLD = fontfile(), fontfile(True)
PDF_FONTS = {False: fitz.Font(fontfile=REG), True: fitz.Font(fontfile=BOLD)}
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(16), Inches(9)
prs.core_properties.title = 'FinTrace  -  Follow the evidence'
prs.core_properties.subject = 'Four-person project demonstration'
prs.core_properties.author = 'FinTrace team'
pdf = fitz.open()
checks = []


def rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def shape(slide, page, x, y, w, h, color, rounded=False, angle=0):
    obj = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                                 Inches(x / 90), Inches(y / 90), Inches(w / 90), Inches(h / 90))
    obj.fill.solid()
    obj.fill.fore_color.rgb = RGBColor.from_string(color[1:])
    obj.line.fill.background()
    if rounded:
        obj.adjustments[0] = .5
    obj.rotation = angle
    if angle:
        # Rounded crosses are composed of two rotated capsules.
        center = fitz.Point(x + w / 2, y + h / 2)
        page.draw_rect(fitz.Rect(x, y, x + w, y + h), color=None, fill=rgb(color),
                       radius=.5, morph=(center, fitz.Matrix(angle)))
    else:
        page.draw_rect(fitz.Rect(x, y, x + w, y + h), color=None, fill=rgb(color),
                       radius=.5 if rounded else None)


def text(slide, page, content, x, y, w, size=30, bold=False, color=INK, line=1.17):
    font = PDF_FONTS[bold]
    lines = []
    for para in content.split('\n'):
        current = ''
        for word in para.split():
            candidate = (current + ' ' + word).strip()
            if current and font.text_length(candidate, fontsize=size) > w - 4:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    height = len(lines) * size * line + 10
    if y + height > 716:
        raise ValueError(f'Text crosses footer: {content[:65]} ({y + height})')
    box = slide.shapes.add_textbox(Inches(x / 90), Inches(y / 90), Inches(w / 90), Inches(height / 90))
    tf = box.text_frame
    tf.clear()
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = False
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = ln
        p.font.name = FONT
        p.font.size = Pt(size * .8)
        p.font.bold = bold
        p.font.color.rgb = RGBColor.from_string(color[1:])
        p.space_before = p.space_after = Pt(0)
        p.line_spacing = 1.17
        page.insert_text((x, y + size * .93 + i * size * line), ln, fontsize=size,
                         fontname='DeckBold' if bold else 'DeckRegular', color=rgb(color))
    checks.append((content[:50], x, y, w, height))


def new(title, n, owner, timing, cue, talk, cover=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(BG[1:])
    page = pdf.new_page(width=W, height=H)
    page.draw_rect(page.rect, color=None, fill=rgb(BG))
    page.insert_font(fontname='DeckRegular', fontfile=REG)
    page.insert_font(fontname='DeckBold', fontfile=BOLD)
    for i, c in enumerate(PALETTE):
        shape(slide, page, -50, 0, 1194 - i * 111, 75, c, True)
    cy = 277 if cover else 166
    shape(slide, page, 78, cy - 16, 83, 29, '#F7B494', True, -45)
    shape(slide, page, 78, cy - 16, 83, 29, ORANGE, True, 45)
    text(slide, page, title, 242, 242 if cover else 130, 1112, 88 if cover else 61, True)
    # Native footer line and text.
    shape(slide, page, 0, 737, 1367, 1, '#858585')
    for value, x, width, c, b in [(f'{n:02d}.', 74, 70, ORANGE, True),
                                  ('FINTRACE / PROJECT DEMO', 242, 600, MUTED, False),
                                  (owner.upper(), 1170, 200, INK, False)]:
        box = slide.shapes.add_textbox(Inches(x / 90), Inches(758 / 90), Inches(width / 90), Inches(.35))
        tf = box.text_frame; tf.margin_left = tf.margin_top = 0
        tf.text = value
        tf.paragraphs[0].font.name = FONT
        tf.paragraphs[0].font.size = Pt(18 if b else 14)
        tf.paragraphs[0].font.bold = b
        tf.paragraphs[0].font.color.rgb = RGBColor.from_string(c[1:])
        page.insert_text((x, 780), value, fontsize=23 if b else 18,
                         fontname='DeckBold' if b else 'DeckRegular', color=rgb(c))
    slide.notes_slide.notes_text_frame.text = f'{owner} | {timing}\nSCREEN CUE: {cue}\n\n{talk}\n\nCurrent setup and service scope: README.md. Replace presenter labels with your names. Use actual on-screen counts; do not claim accuracy. Review actions use a disposable demo database.'
    return slide, page


def cols(s, p, items, y=400):
    count = len(items)
    width = (1110 - 55 * (count - 1)) / count
    for i, (heading, body) in enumerate(items):
        x = 242 + i * (width + 55)
        text(s, p, heading, x, y, width, 29, True)
        text(s, p, body, x, y + 64, width, 25)


s, p = new('FinTrace\nFollow the evidence.', 1, 'Person 1', '0:00–0:25', 'Start with team on camera, then this title.',
           'Introduce all four presenters. We help reviewers inspect transfer patterns and understand why an account needs attention. Today: overview, evidence, connections and a human review decision.', True)
text(s, p, 'Explainable transaction investigation\nIBM synthetic data · Rules and graphs · Human review', 242, 485, 1080, 31)

s, p = new('One payment is not the story.', 2, 'Person 1', '0:25–1:10', 'Show this slide, then switch to Overview. Keep synthetic-data notice and snapshot visible.',
           'Several transfers together can reveal a pattern that one payment cannot. These are research records, not real customer data. The selected snapshot uses only transfers before an explicit time limit.')
cols(s, p, [('Many senders', 'Several accounts pay one account.'), ('Fast forwarding', 'Money arrives, then moves onward.'), ('Connected transfers', 'A sequence links several accounts.')])
text(s, p, 'A pattern is a reason to look closer - not proof of wrongdoing.', 242, 633, 1090, 27, True)

s, p = new('A clear path from data to review', 3, 'Person 1', '1:10–1:35', 'Use this diagram briefly. Then return to Overview.',
           'Data preparation preserves source references and separates labels. Rules and chronological graph checks produce evidence. Fixed policy points prioritize review. The reviewer can inspect and record an action.')
for i, (head, body) in enumerate([('Prepare', 'Validate source\nand keep references'), ('Find patterns', 'Rules + time-ordered\ngraph checks'), ('Prioritize', 'Fixed points with\nvisible contributions'), ('Review', 'Inspect evidence\nand save a decision')]):
    x = 242 + i * 286
    shape(s, p, x, 375, 250, 7, ORANGE)
    text(s, p, head, x, 410, 250, 31, True)
    text(s, p, body, x, 469, 250, 24)
    if i < 3:
        text(s, p, '→', x + 251, 407, 35, 32, True, ORANGE)
text(s, p, 'Benchmark labels stay outside detection and scoring.', 242, 628, 1090, 27, True)

s, p = new('Start with the review overview.', 4, 'Person 1', '1:35–2:15', 'LIVE APP: Overview → cards → priority distribution → patterns → coverage expander.',
           'Use the actual selected snapshot counts. Explain review accounts, alerts and supporting findings. Show coverage: unavailable or incomplete analysis is not a clean result. Hand over to Person 2.')
cols(s, p, [('See the workload', 'Accounts, alerts and supporting findings.'), ('Choose a starting point', 'Priority bands and evidence families.'), ('Read the limits', 'Coverage and incomplete searches stay visible.')])
text(s, p, 'LIVE DEMO  /  Overview', 242, 643, 950, 24, True, ORANGE)

s, p = new('Every alert has evidence.', 5, 'Person 2', '2:15–3:55', 'LIVE APP: Alert review → search rehearsed account → Inspect an alert → Evidence. Expand measurements and thresholds.',
           'Search and filter the queue. Choose the rehearsed account. Show the explanation, window and transfer references. Compare one observed measurement to its policy threshold. Point out the evidence JSON download and limitations; it is not a regulatory report.')
cols(s, p, [('What happened?', 'Plain explanation, time window and observed measurements.'), ('Why did it trigger?', 'Visible policy thresholds and exact transfer references.'), ('What can we check?', 'Inspect the evidence and download the selected finding.')])
text(s, p, 'LIVE DEMO  /  Alert review → Evidence', 242, 643, 1050, 24, True, ORANGE)

s, p = new('Priority is not probability.', 6, 'Person 2', '3:55–4:35', 'LIVE APP: Priority ledger → score → family points → suppressed correlations if present.',
           'Fixed weights show where the score comes from. Related findings are grouped so the same type of clue is not counted repeatedly. The score is capped at 100. Eighty means review sooner, not eighty percent likely to be crime. Hand over to Person 3.')
text(s, p, 'REVIEW PRIORITY', 242, 365, 470, 25, True, ORANGE)
text(s, p, 'Where to look\nnext', 242, 417, 500, 62, True)
text(s, p, 'NOT A PROBABILITY', 846, 365, 510, 25, True)
text(s, p, 'Not a verdict\nof crime', 846, 417, 510, 58, True)
text(s, p, 'Fixed points · Visible contributions · Related clues grouped', 242, 640, 1100, 27)

s, p = new('An account, in context', 7, 'Person 3', '4:35–5:35', 'LIVE APP: Account evidence → same bank/account pair → Observed transfers → Load graph-window transfers.',
           'Show priority, findings and linked alerts. Load the linked graph-window transfers. Totals remain separate by currency. They are not balances or a full account history. Verified customer information remains unavailable rather than fabricated.')
cols(s, p, [('One evidence view', 'Priority, findings and linked alerts for the selected account.'), ('Precise transfers', 'Sender, receiver, time and both payment amounts.'), ('Honest boundaries', 'Currencies stay separate. Missing customer context stays missing.')])
text(s, p, 'Observed transfers - not a balance or a complete account history.', 242, 643, 1110, 26, True)

s, p = new('Connections need a time order.', 8, 'Person 3', '5:35–6:55', 'LIVE APP: Network explorer → same Seed account → Highlight finding → hover → Direction → hops 1 to 2 → displayed-transfer table.',
           'Dots are accounts; arrows are transfers. Orange edges identify selected evidence. Show exact references in the table. Connections alone are not chronological money flow: later transfers cannot explain earlier ones. Equal timestamps do not establish an order. Disclose partial searches and display caps.')
for i, (name, time) in enumerate([('Account A', '10:00'), ('Account B', '10:10'), ('Account C', '10:20')]):
    x = 242 + i * 390
    shape(s, p, x, 370, 268, 105, '#F8D2BE', True)
    text(s, p, name, x + 25, 394, 230, 32, True)
    text(s, p, time, x + 25, 505, 230, 29, False, ORANGE)
    if i < 2:
        text(s, p, '→', x + 299, 392, 70, 44, True, ORANGE)
text(s, p, 'Illustrative sequence - not a measured transaction from the dataset.', 242, 590, 1100, 24)
text(s, p, 'LIVE DEMO  /  Network explorer', 242, 643, 1050, 24, True, ORANGE)

s, p = new('The reviewer stays in control.', 9, 'Person 4', '6:55–7:55', 'LIVE APP, disposable database: Alert review → Review & audit → In review → Reviewer + reason → Save audited review once → show history.',
           'Use an open alert in a disposable demo copy. Save the reviewer and reason, then show the new event. Old events remain. Refresh does not submit twice. This is alert review, not complete case management. No automatic account freeze, bank contact or regulatory filing.')
cols(s, p, [('Inspect', 'Read the finding and its limits before acting.'), ('Record', 'Name the reviewer, choose the status and give a reason.'), ('Keep the history', 'Time, actor, action and reason remain in the audit trail.')])
text(s, p, 'LIVE DEMO  /  Review & audit  -  use the demo database only', 242, 643, 1110, 24, True, ORANGE)

s, p = new('Trust the checks - not a claim.', 10, 'Person 4', '7:55–8:45', 'Show this slide, then a fresh terminal test result. Do not type a fake result or memorize a test count.',
           'Labels are separated from detector inputs. Source references and exact amounts are preserved. Invalid rows go to quarantine. Automated checks cover time limits, evidence, workflow and the interface. Passing tests does not establish detection accuracy.')
cols(s, p, [('No answer leakage', 'Benchmark labels never feed detectors or priority scores.'), ('Traceable evidence', 'Exact amounts, source references and visible analysis limits.'), ('Regression checks', 'Tests cover boundaries, saved review actions and screens.')])
text(s, p, 'Tests check behaviour. They do not prove detection accuracy.', 242, 643, 1110, 27, True)

s, p = new('Working now. Planned next.', 11, 'Person 4', '8:45–9:05', 'Use this slide for the scope summary. Do not demonstrate placeholder routes.',
           'Implemented: preparation, deterministic rules, bounded graphs, explainable priorities, four investigation screens and audited alert review. Future: complete cases, general reports, replay and benchmark evaluation. No accuracy percentage claimed.')
cols(s, p, [('Working now', 'Prepared data and evidence\nRules and bounded graphs\nPriorities and four app screens\nAudited alert review'), ('Future work', 'Complete case management\nGeneral evidence reports\nHistorical replay\nBenchmark evaluation')], y=345)

s, p = new('Show the evidence.\nKeep the human decision.', 12, 'All four', '9:05–9:20', 'Close together on camera, or keep this closing slide visible.',
           'Our aim is simple: do not just flag a pattern. Show the evidence, explain the priority and let a person make an informed decision. That is FinTrace. Thank you.', True)
text(s, p, 'FinTrace\nQuestions and discussion', 242, 506, 1100, 34)

prs.save(OUT / 'PRESENTATION.pptx')
pdf.save(OUT / 'PRESENTATION.pdf', garbage=4, deflate=True)
print(f'Built {len(prs.slides)} editable slides and matching PDF; {len(checks)} text boxes checked.')
preview_root = Path('/tmp/fintrace-slides-work')
preview_root.mkdir(parents=True, exist_ok=True)
for i in (0, 4, 7, 10):
    pdf[i].get_pixmap(matrix=fitz.Matrix(.9, .9)).save(str(preview_root / f'slide-{i + 1:02d}.png'))
