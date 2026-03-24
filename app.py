from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import math
import re
import os

app = Flask(__name__)
app.secret_key = 'atlas_copco_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calculators.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── Models ───────────────────────────────────────────────────────────────────

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
    return {'now': datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    calculators = Calculator.query.order_by(Calculator.created_at.desc()).all()
    return render_template('index.html', calculators=calculators)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/history')
def history():
    results = (CalculationResult.query
               .join(Calculator)
               .order_by(CalculationResult.calculated_at.desc())
               .limit(100)
               .all())
    return render_template('history.html', results=results)


@app.route('/create-form', methods=['GET', 'POST'])
def create_form():
    if request.method == 'POST':
        data = request.form

        num_inputs    = int(data.get('num_inputs', 0))
        num_outputs   = int(data.get('num_outputs', 0))
        num_constants = int(data.get('num_constants', 0))
        num_dropdowns = int(data.get('num_dropdowns', 0))
        title         = data.get('title', 'Calculator').strip()

        config = {
            'title':         title,
            'num_inputs':    num_inputs,
            'num_outputs':   num_outputs,
            'num_constants': num_constants,
            'num_dropdowns': num_dropdowns,
        }

        calc = Calculator(title=title, config=json.dumps(config))
        db.session.add(calc)
        db.session.commit()

        return redirect(url_for('setup_calculator', calc_id=calc.id))

    return render_template('create_form.html')


@app.route('/setup/<int:calc_id>', methods=['GET', 'POST'])
def setup_calculator(calc_id):
    calc   = Calculator.query.get_or_404(calc_id)
    config = json.loads(calc.config)

    if request.method == 'POST':
        data = request.form

        # Build input field definitions
        inputs = []
        for i in range(config['num_inputs']):
            inputs.append({'label': data.get(f'input_label_{i}', f'Input {i+1}')})

        # Build constant field definitions
        constants = []
        for i in range(config['num_constants']):
            constants.append({
                'label': data.get(f'const_label_{i}', f'Const {i+1}'),
                'value': data.get(f'const_value_{i}', '0')
            })

        # Build output field definitions
        outputs = []
        for i in range(config['num_outputs']):
            outputs.append({
                'label':   data.get(f'output_label_{i}', f'Output {i+1}'),
                'formula': data.get(f'output_formula_{i}', '0')
            })

        # Build dropdown definitions
        dropdowns = []
        for i in range(config['num_dropdowns']):
            dd_label = data.get(f'dropdown_label_{i}', f'Dropdown {i+1}')
            items_raw = data.get(f'dropdown_items_{i}', '')
            items = [item.strip() for item in items_raw.split(',') if item.strip()]
            dropdowns.append({'label': dd_label, 'items': items})

        config['inputs']    = inputs
        config['constants'] = constants
        config['outputs']   = outputs
        config['dropdowns'] = dropdowns

        calc.config = json.dumps(config)
        db.session.commit()

        return redirect(url_for('use_calculator', calc_id=calc.id))

    return render_template('setup_calculator.html', calc=calc, config=config)


@app.route('/calculator/<int:calc_id>', methods=['GET', 'POST'])
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
        # Add math functions to namespace
        namespace.update({
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
            'tan': math.tan,   'log': math.log, 'log10': math.log10,
            'exp': math.exp,   'abs': abs,       'pi': math.pi,
            'pow': math.pow,   'ceil': math.ceil,'floor': math.floor,
        })

        results = []
        calc_error = False
        for i, out in enumerate(config.get('outputs', [])):
            formula = out['formula']
            try:
                # Replace label names with namespace values
                safe_formula = formula
                # Sanitize — allow only safe characters
                if re.search(r'[^0-9a-zA-Z_\s\+\-\*\/\(\)\.\,]', safe_formula):
                    raise ValueError("Unsafe characters in formula")
                result = eval(safe_formula, {"__builtins__": {}}, namespace)
                results.append({'label': out['label'], 'value': round(float(result), 6), 'formula': formula, 'error': None})
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
def delete_calculator(calc_id):
    calc = Calculator.query.get_or_404(calc_id)
    db.session.delete(calc)
    db.session.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
