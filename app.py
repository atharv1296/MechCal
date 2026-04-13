from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import json
import math
import statistics as _stats
import random as _random
import re
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos


PYTHON_KEYWORDS = {
    'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
    'def', 'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
    'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
    'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True', 'try',
    'while', 'with', 'yield'
}

# ─── Excel-style Math Namespace ──────────────────────────────────────────────────
# Helper functions
def _sum(*a):          return sum(a)
def _avg(*a):          return sum(a) / len(a) if a else 0
def _min(*a):          return min(a)
def _max(*a):          return max(a)
def _count(*a):        return len([x for x in a if isinstance(x, (int, float))])
def _median(*a):       return _stats.median(a)
def _mode(*a):
    try:               return _stats.mode(a)
    except Exception:  return a[0] if a else 0
def _stdev(*a):        return _stats.stdev(a) if len(a) >= 2 else 0
def _var(*a):          return _stats.variance(a) if len(a) >= 2 else 0
def _product(*a):      r = 1; [setattr([], '', None) for x in a if [r := r * x]]; return r
def _product(*a):
    r = 1
    for x in a: r *= x
    return r
def _large(*a):        # LARGE(v1,v2,...,k) — last arg is rank k
    *vals, k = a; return sorted(vals, reverse=True)[int(k) - 1]
def _small(*a):        # SMALL(v1,v2,...,k) — last arg is rank k
    *vals, k = a; return sorted(vals)[int(k) - 1]
# Logical
def _if(cond, t, f=0):    return t if cond else f
def _ifs(*a):              # IFS(cond1,val1, cond2,val2, ...)
    for i in range(0, len(a) - 1, 2):
        if a[i]: return a[i + 1]
    return 0
def _and(*a):              return int(all(bool(x) for x in a))
def _or(*a):               return int(any(bool(x) for x in a))
def _not(x):               return int(not x)
# Rounding
def _roundup(x, n=0):     f = 10 ** int(n); return math.ceil(x * f) / f
def _rounddown(x, n=0):   f = 10 ** int(n); return math.floor(x * f) / f
def _ceiling(x, s=1):     return math.ceil(x / s) * s if s else x
def _floor_s(x, s=1):     return math.floor(x / s) * s if s else x
# Misc math
def _power(x, n):          return x ** n
def _mod(x, y):            return x % y
def _sign(x):              return 1 if x > 0 else (-1 if x < 0 else 0)
def _int(x):               return int(x)
def _gcd(a, b):            return math.gcd(int(a), int(b))
def _lcm(a, b):
    a, b = int(a), int(b)
    return abs(a * b) // math.gcd(a, b) if a and b else 0
def _clamp(x, lo, hi):    return max(lo, min(hi, x))
def _rand():               return _random.random()
def _randbetween(lo, hi):  return _random.uniform(lo, hi)

MATH_NAMESPACE = {
    # ── Constants ─────────────────────────────────────────────
    'pi': math.pi,      'PI': math.pi,
    'e':  math.e,       'E':  math.e,
    # ── Basic Aggregation (Excel: SUM, AVERAGE, MIN, MAX ...) ─
    'SUM': _sum,        'sum': _sum,
    'AVERAGE': _avg,    'AVG': _avg,        'average': _avg,
    'MIN': _min,        'min': _min,
    'MAX': _max,        'max': _max,
    'COUNT': _count,    'count': _count,
    'MEDIAN': _median,  'median': _median,
    'MODE': _mode,      'mode': _mode,
    'STDEV': _stdev,    'stdev': _stdev,
    'VAR': _var,        'var': _var,
    'PRODUCT': _product,'product': _product,
    'LARGE': _large,    'SMALL': _small,
    # ── Logical ───────────────────────────────────────────────
    'IF': _if,          'IFS': _ifs,
    'AND': _and,        'OR': _or,          'NOT': _not,
    # ── Basic Math ────────────────────────────────────────────
    'ABS': abs,         'abs': abs,
    'SQRT': math.sqrt,  'sqrt': math.sqrt,
    'POWER': _power,    'pow': _power,
    'MOD': _mod,        'mod': _mod,
    'SIGN': _sign,      'sign': _sign,
    'INT': _int,        'int': _int,
    'EXP': math.exp,    'exp': math.exp,
    'GCD': _gcd,        'gcd': _gcd,
    'LCM': _lcm,        'lcm': _lcm,
    'CLAMP': _clamp,    'clamp': _clamp,
    'hypot': math.hypot,'HYPOT': math.hypot,
    'fabs': math.fabs,  'FABS': math.fabs,
    # ── Rounding ───────────────────────────────────────────────
    'ROUND': round,         'round': round,
    'ROUNDUP': _roundup,    'roundup': _roundup,
    'ROUNDDOWN': _rounddown,'rounddown': _rounddown,
    'CEILING': _ceiling,    'ceil': math.ceil,
    'FLOOR': _floor_s,      'floor': math.floor,
    'TRUNC': math.trunc,    'trunc': math.trunc,
    # ── Trigonometry ───────────────────────────────────────────
    'SIN': math.sin,    'sin': math.sin,
    'COS': math.cos,    'cos': math.cos,
    'TAN': math.tan,    'tan': math.tan,
    'ASIN': math.asin,  'asin': math.asin,
    'ACOS': math.acos,  'acos': math.acos,
    'ATAN': math.atan,  'atan': math.atan,
    'ATAN2': math.atan2,'atan2': math.atan2,
    'SINH': math.sinh,  'sinh': math.sinh,
    'COSH': math.cosh,  'cosh': math.cosh,
    'TANH': math.tanh,  'tanh': math.tanh,
    'DEGREES': math.degrees, 'degrees': math.degrees,
    'RADIANS': math.radians, 'radians': math.radians,
    # ── Logarithms / Exponential ───────────────────────────────
    'LOG': math.log,    'log': math.log,
    'LOG10': math.log10,'log10': math.log10,
    'LOG2': math.log2,  'log2': math.log2,
    'LOG1P': math.log1p,'log1p': math.log1p,
    'EXPM1': math.expm1,'expm1': math.expm1,
    # ── Extra Math ─────────────────────────────────────────────
    'FACT': math.factorial, 'factorial': math.factorial,
    'RAND': _rand,          'rand': _rand,
    'RANDBETWEEN': _randbetween,
}

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'atlas_copco_secret_2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///calculators.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ─── Image Upload Config ──────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80),  unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)   # hashed
    role         = db.Column(db.String(20),  nullable=False, default='user')  # 'admin' or 'user'
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class Calculator(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    config      = db.Column(db.Text, nullable=False)   # JSON
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    results     = db.relationship('CalculationResult', backref='calculator', lazy=True,
                                  cascade='all, delete-orphan')

class CalculationResult(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    calculator_id = db.Column(db.Integer, db.ForeignKey('calculator.id'), nullable=False)
    inputs        = db.Column(db.Text, nullable=False)   # JSON
    outputs       = db.Column(db.Text, nullable=False)   # JSON
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    # Seed default users on first run
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin',
                            password=generate_password_hash('admin123'),
                            role='admin'))
    if not User.query.filter_by(username='user').first():
        db.session.add(User(username='user',
                            password=generate_password_hash('user123'),
                            role='user'))
    db.session.commit()

# ─── Jinja2 helpers ──────

# Use Python's built-in enumerate safely
import builtins as _builtins
app.jinja_env.globals['enumerate'] = _builtins.enumerate

@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value)
    except Exception:
        return {}

@app.context_processor
def inject_now():
    return {
        'now': datetime.utcnow().strftime('%d %b %Y, %H:%M UTC'),
        'current_user_role': session.get('role'),
        'current_username':  session.get('username'),
    }

# ─── Auth Decorators ──────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('Administrator access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── PDF Report Class ──────────────────────────────────────────────────────────

class AtlasCopcoReport(FPDF):
    def header(self):
        # Background Accent Bar (Teal)
        self.set_fill_color(0, 75, 80)
        self.rect(0, 0, 210, 40, 'F')
        
        # Company Name
        self.set_y(12)
        self.set_x(15)
        self.set_font("helvetica", "B", 26)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "Atlas Copco", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        
        self.set_font("helvetica", "", 10)
        self.set_text_color(200, 200, 200)
        self.set_x(16)
        self.cell(0, 5, "DESIGN & ENGINEERING COMPUTATION SUITE", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        
        # Report Tag (Gold)
        self.set_y(15)
        self.set_x(-75)
        self.set_fill_color(184, 151, 42)
        self.set_text_color(255, 255, 255)
        self.set_font("helvetica", "B", 11)
        self.cell(60, 10, "OFFICIAL REPORT", align="C", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.ln(20)

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(0, 75, 80)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Atlas Copco Internal Document - Confidential", align="L")
        self.cell(0, 10, f"Page {self.page_no()} of {{nb}}", align="R", ln=1)

def create_calc_pdf(calc_title, designer_name, inputs, outputs, image_paths):
    pdf = AtlasCopcoReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # ── METADATA HEADER ───────────────────────────────────────────
    pdf.set_y(50)
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(0, 75, 80)
    pdf.cell(0, 12, calc_title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(100, 8, f"Document ID: AC-CALC-{datetime.now().strftime('%Y%m%d%H%M')}")
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%B %d, %Y')}", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Primary Engineer: {designer_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    # ── INPUT VARIABLES ───────────────────────────────────────────
    pdf.set_fill_color(0, 75, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 10, "  1.0 DESIGN INPUT PARAMETERS", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.ln(2)
    
    # Table Header
    pdf.set_fill_color(240, 245, 245)
    pdf.set_text_color(68, 68, 68)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(120, 8, "  Variable Name / Label", border='B', fill=True)
    pdf.cell(70, 8, "Value", border='B', fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(28, 28, 28)
    fill = False
    for label, val in inputs.items():
        pdf.set_fill_color(248, 250, 250) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(120, 9, f"  {label}", fill=True)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(70, 9, f"{val}", fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        fill = not fill
    
    pdf.ln(12)

    # ── COMPUTATION RESULTS ───────────────────────────────────────
    pdf.set_fill_color(184, 151, 42) # Gold
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 10, "  2.0 VERIFIED COMPUTATION RESULTS", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.ln(2)
    
    # Grid results
    for label, val in outputs.items():
        # Result Card mockup
        pdf.set_fill_color(252, 248, 235)
        pdf.set_draw_color(184, 151, 42)
        pdf.set_text_color(140, 110, 20)
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(0, 6, f"  {label.upper()}", border='TLR', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_text_color(0, 75, 80)
        pdf.set_font("helvetica", "B", 18)
        pdf.cell(0, 14, f"  {val}", border='BLR', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)
        
    # ── REFERENCE IMAGES ──────────────────────────────────────────
    if image_paths:
        pdf.add_page()
        pdf.set_fill_color(220, 220, 220)
        pdf.set_text_color(50, 50, 50)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 10, "  3.0 REFERENCE SCHEMATICS & DIAGRAMS", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(10)
        
        for i, img_data in enumerate(image_paths):
            fpath = os.path.join(UPLOAD_FOLDER, img_data['filename'])
            if os.path.exists(fpath):
                # Calculate height to fit proportionately
                # We aim for roughly half a page per image if possible
                pdf.image(fpath, x=25, y=pdf.get_y(), w=160)
                pdf.ln(95) # Approximate space for image
                
                pdf.set_font("helvetica", "I", 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 10, f"DOCUMENTATION FIG {i+1}: {img_data.get('caption', 'General Reference')}", 
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                pdf.ln(10)
                
                if (i+1) % 2 == 0 and i < len(image_paths) - 1:
                    pdf.add_page()

    return bytes(pdf.output())

# ─── Routes ───────────────────────────────────────────────────────────────────

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id']  = user.id
            session['username'] = user.username
            session['role']     = user.role
            flash(f'Welcome back, {user.username}!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    calculators = Calculator.query.order_by(Calculator.created_at.desc()).all()
    return render_template('index.html', calculators=calculators)


@app.route('/about')
@login_required
def about():
    return render_template('about.html')


@app.route('/history')
@login_required
def history():
    results = (CalculationResult.query
               .join(Calculator)
               .order_by(CalculationResult.calculated_at.desc())
               .limit(100)
               .all())
    return render_template('history.html', results=results)


@app.route('/create-form', methods=['GET', 'POST'])
@admin_required
def create_form():
    if request.method == 'POST':
        data = request.form

        num_inputs    = int(data.get('num_inputs', 0))
        num_outputs   = int(data.get('num_outputs', 0))
        num_constants = int(data.get('num_constants', 0))
        num_dropdowns = int(data.get('num_dropdowns', 0))
        title         = data.get('title', 'Calculator').strip()

        # Check for title uniqueness
        existing = Calculator.query.filter_by(title=title).first()
        if existing:
            flash(f"A tool with the name '{title}' already exists. Please use a unique title.", "error")
            return render_template('create_form.html')

        config = {
            'title':         title,
            'num_inputs':    num_inputs,
            'num_outputs':   num_outputs,
            'num_constants': num_constants,
            'num_dropdowns': num_dropdowns,
            'inputs': [], 'outputs': [], 'constants': [], 'dropdowns': [],
            'ref_images': []
        }

        calc = Calculator(title=title, config=json.dumps(config))
        db.session.add(calc)
        db.session.commit()

        return redirect(url_for('setup_calculator', calc_id=calc.id))

    return render_template('create_form.html')


@app.route('/edit-form/<int:calc_id>', methods=['GET', 'POST'])
@admin_required
def edit_form(calc_id):
    calc = Calculator.query.get_or_404(calc_id)
    config = json.loads(calc.config)
    
    if request.method == 'POST':
        data = request.form
        num_inputs    = int(data.get('num_inputs', 0))
        num_outputs   = int(data.get('num_outputs', 0))
        num_constants = int(data.get('num_constants', 0))
        num_dropdowns = int(data.get('num_dropdowns', 0))
        title         = data.get('title', calc.title).strip()

        # Check for title uniqueness (if title changed)
        if title != calc.title:
            existing = Calculator.query.filter_by(title=title).first()
            if existing:
                flash(f"The title '{title}' is already in use by another tool. Please choose a unique title.", "error")
                return render_template('create_form.html', calc=calc, config=config, is_edit=True)

        config['num_inputs'] = num_inputs
        config['num_outputs'] = num_outputs
        config['num_constants'] = num_constants
        config['num_dropdowns'] = num_dropdowns
        config['title'] = title
        
        calc.title = title
        calc.config = json.dumps(config)
        db.session.commit()
        
        flash('Calculator structure updated.', 'success')
        return redirect(url_for('setup_calculator', calc_id=calc.id))

    return render_template('create_form.html', calc=calc, config=config, is_edit=True)

@app.route('/setup/<int:calc_id>', methods=['GET', 'POST'])

@admin_required
def setup_calculator(calc_id):
    calc   = Calculator.query.get_or_404(calc_id)
    config = json.loads(calc.config)

    if request.method == 'POST':
        data = request.form
        label_error = None

        # 1. Collect all labels to check for global uniqueness
        input_labels    = [data.get(f'input_label_{i}', f'Input {i+1}').strip() for i in range(config['num_inputs'])]
        const_labels    = [data.get(f'const_label_{i}', f'Const {i+1}').strip() for i in range(config['num_constants'])]
        output_labels   = [data.get(f'output_label_{i}', f'Output {i+1}').strip() for i in range(config['num_outputs'])]
        dropdown_labels = [data.get(f'dropdown_label_{i}', f'Menu {i+1}').strip() for i in range(config['num_dropdowns'])]
        
        all_labels = input_labels + const_labels + output_labels + dropdown_labels
        # 2. Build current preview from form data (to preserve values on error)
        inputs = [{'label': l} for l in input_labels]
        constants = []
        for i, l in enumerate(const_labels):
            constants.append({'label': l, 'value': data.get(f'const_value_{i}', '0')})
        outputs = []
        for i, l in enumerate(output_labels):
            outputs.append({'label': l, 'formula': data.get(f'output_formula_{i}', '0')})
        dropdowns = []
        for i, l in enumerate(dropdown_labels):
            items_raw = data.get(f'dropdown_items_{i}', '').strip()
            options = []
            for entry in items_raw.split(','):
                if not entry.strip(): continue
                if ':' in entry:
                    lbl, val = entry.split(':', 1)
                    options.append({'label': lbl.strip(), 'value': val.strip()})
                else:
                    options.append({'label': entry.strip(), 'value': entry.strip()})
            dropdowns.append({'label': l, 'options': options})

        preview_config = config.copy()
        preview_config.update({
            'inputs': inputs, 'constants': constants, 
            'outputs': outputs, 'dropdowns': dropdowns
        })

        # 3. Global Uniqueness Check
        if len(all_labels) != len(set(all_labels)):
            seen = set()
            duplicates = [x for x in all_labels if x in seen or seen.add(x)]
            label_error = f"Duplicate label(s) detected: '{', '.join(set(duplicates))}'. All names must be unique."
            return render_template('setup_calculator.html', calc=calc, config=preview_config, label_error=label_error)

        # 4. Reserved Keywords Check
        for lbl in all_labels:
            if lbl in PYTHON_KEYWORDS:
                label_error = f"'{lbl}' is a reserved system keyword. Please use a different name."
                return render_template('setup_calculator.html', calc=calc, config=preview_config, label_error=label_error)

        # 5. Success! Update real config
        config.update({
            'inputs': inputs, 'constants': constants, 
            'outputs': outputs, 'dropdowns': dropdowns
        })

        # ── Handle Image Uploads ──────────────────────────────────────────────
        existing_images = config.get('images', [])
        new_images = []
        for i in range(10):
            file = request.files.get(f'image_{i}')
            if file and file.filename and allowed_file(file.filename):
                ext      = file.filename.rsplit('.', 1)[1].lower()
                fname    = f"calc_{calc.id}_{i}_{secure_filename(file.filename)}"
                fpath    = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                file.save(fpath)
                caption  = data.get(f'image_caption_{i}', '').strip()
                new_images.append({'filename': fname, 'caption': caption})

        # Preserve existing images unless replaced
        config['images'] = existing_images + new_images

        calc.config = json.dumps(config)
        db.session.commit()

        return redirect(url_for('use_calculator', calc_id=calc.id))

    return render_template('setup_calculator.html', calc=calc, config=config)


@app.route('/calculator/<int:calc_id>', methods=['GET', 'POST'])
@login_required
def use_calculator(calc_id):
    calc   = Calculator.query.get_or_404(calc_id)
    config = json.loads(calc.config)

    results    = None
    error      = None
    form_vals  = {}

    if request.method == 'POST':
        data = request.form

        # Collect input values
        input_vals = {}
        for i, inp in enumerate(config.get('inputs', [])):
            label = inp['label']
            val   = data.get(f'input_{i}', '0')
            try:
                input_vals[label] = float(val)
            except ValueError:
                input_vals[label] = 0.0
            form_vals[f'input_{i}'] = val

        # Collect dropdown values
        dropdown_vals = {}
        for i, dd in enumerate(config.get('dropdowns', [])):
            label = dd['label']
            val   = data.get(f'dropdown_{i}', '0')
            try:
                dropdown_vals[label] = float(val)
            except ValueError:
                dropdown_vals[label] = 0.0 # Standard fallback if not numeric
            form_vals[f'dropdown_{i}'] = val
        
        input_vals.update(dropdown_vals)

        # Collect constant values (from config)
        const_vals = {}
        for c in config.get('constants', []):
            try:
                const_vals[c['label']] = float(c['value'])
            except ValueError:
                const_vals[c['label']] = 0.0

        # Collect dropdown selections
        dropdown_vals = {}
        for i, dd in enumerate(config.get('dropdowns', [])):
            dropdown_vals[dd['label']] = data.get(f'dropdown_{i}', '')

        # Merge all into evaluation namespace
        namespace = {**input_vals, **const_vals, **dropdown_vals}
        # Add all Excel-style math functions to the namespace
        namespace.update(MATH_NAMESPACE)

        results = []
        calc_error = False
        for i, out in enumerate(config.get('outputs', [])):
            formula = out['formula']
            try:
                # Replace label names with namespace values
                safe_formula = formula
                # Sanitize — allow only safe characters
                # Sanitize — allow only safe characters 
                # (allowing ^ for intermediate conversion and other math symbols)
                if re.search(r'[^0-9a-zA-Z_\s\+\-\*\/\(\)\.\,\%\^\:]', safe_formula):
                    raise ValueError("Unsafe characters in formula")
                result = eval(safe_formula, {"__builtins__": {}}, namespace)
                result_val = round(float(result), 6)
                results.append({'label': out['label'], 'value': result_val, 'formula': formula, 'error': None})
                # Allow subsequent outputs to reference this output as op1, op2, etc.
                namespace[f'op{i+1}'] = result_val
                # Also allow referencing by the output's own label (e.g., 'shaft')
                namespace[out['label']] = result_val
            except Exception as e:
                results.append({'label': out['label'], 'value': None, 'formula': formula, 'error': str(e)})
                calc_error = True

        if not calc_error:
            # Save to history
            cr = CalculationResult(
                calculator_id = calc.id,
                inputs        = json.dumps({**input_vals, **const_vals}),
                outputs       = json.dumps({r['label']: r['value'] for r in results})
            )
            db.session.add(cr)
            db.session.commit()

    return render_template('calculator.html', calc=calc, config=config,
                           results=results, error=error, form_vals=form_vals)


@app.route('/delete/<int:calc_id>', methods=['POST'])
@admin_required
def delete_calculator(calc_id):
    calc = Calculator.query.get_or_404(calc_id)
    # Also delete uploaded images for this calculator
    config = json.loads(calc.config)
    for img in config.get('images', []):
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], img['filename'])
        if os.path.exists(fpath):
            os.remove(fpath)
    db.session.delete(calc)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/delete-image/<int:calc_id>/<int:img_index>', methods=['POST'])
@admin_required
def delete_image(calc_id, img_index):
    """Remove a single reference image from a calculator."""
    calc   = Calculator.query.get_or_404(calc_id)
    config = json.loads(calc.config)
    images = config.get('images', [])
    if 0 <= img_index < len(images):
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], images[img_index]['filename'])
        if os.path.exists(fpath):
            os.remove(fpath)
        images.pop(img_index)
        config['images'] = images
        calc.config = json.dumps(config)
        db.session.commit()
        flash('Image removed.', 'success')
    return redirect(url_for('setup_calculator', calc_id=calc_id))


@app.route('/generate-report/<int:calc_id>', methods=['POST'])
@login_required
def generate_report(calc_id):
    calc = Calculator.query.get_or_404(calc_id)
    config = json.loads(calc.config)
    designer_name = request.form.get('designer_name', 'System Engineer')
    
    # Get the latest result for this calculator
    latest_result = (CalculationResult.query
                     .filter_by(calculator_id=calc_id)
                     .order_by(CalculationResult.calculated_at.desc())
                     .first())
    
    if not latest_result:
        flash('No calculation results found to generate report.', 'error')
        return redirect(url_for('use_calculator', calc_id=calc_id))
    
    inputs = json.loads(latest_result.inputs)
    outputs = json.loads(latest_result.outputs)
    image_paths = config.get('images', [])
    
    pdf_content = create_calc_pdf(calc.title, designer_name, inputs, outputs, image_paths)
    
    from flask import make_response
    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    filename = f"Report_{calc.title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


if __name__ == '__main__':
    app.run(debug=True)
