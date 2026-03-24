/* ═══════════════════════════════════════════════════════════════
   ATLAS COPCO CALCULATOR — main.js
   ═══════════════════════════════════════════════════════════════ */

'use strict';

// ── Hamburger menu ──────────────────────────────────────────
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('navLinks');

if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
        navLinks.classList.toggle('open');
        hamburger.classList.toggle('open');
        hamburger.setAttribute('aria-expanded',
            navLinks.classList.contains('open').toString());
    });
    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
            navLinks.classList.remove('open');
            hamburger.classList.remove('open');
        }
    });
    // Close on nav link click (mobile)
    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('open');
            hamburger.classList.remove('open');
        });
    });
}

// ── Counter controls ────────────────────────────────────────
function changeCount(fieldId, delta) {
    const el  = document.getElementById(fieldId);
    if (!el) return;
    const min = parseInt(el.min, 10) || 0;
    const max = parseInt(el.max, 10) || 99;
    let   val = parseInt(el.value, 10) || 0;
    val = Math.min(max, Math.max(min, val + delta));
    el.value = val;
    // Pulse animation on the input
    el.style.transform = 'scale(1.12)';
    setTimeout(() => { el.style.transform = ''; }, 180);
}
window.changeCount = changeCount;

// ── Animate cards on scroll (Intersection Observer) ─────────
const observerOpts = { threshold: 0.12 };
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity   = '1';
            entry.target.style.transform = 'translateY(0)';
            observer.unobserve(entry.target);
        }
    });
}, observerOpts);

document.querySelectorAll('.feature-card, .calc-card, .stat-card, .about-feat, .count-card').forEach((el, i) => {
    el.style.opacity    = '0';
    el.style.transform  = 'translateY(28px)';
    el.style.transition = `opacity 0.45s ease ${i * 0.06}s, transform 0.45s ease ${i * 0.06}s`;
    observer.observe(el);
});

// ── Auto-dismiss flash messages ─────────────────────────────
document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        el.style.opacity    = '0';
        el.style.transform  = 'translateY(-8px)';
        setTimeout(() => el.remove(), 500);
    }, 4500);
});

// ── Calculator page: highlight changed inputs ──────────────
document.querySelectorAll('.calc-input').forEach(input => {
    input.addEventListener('input', () => {
        input.style.borderColor = 'var(--ac-primary)';
        input.style.boxShadow   = '0 0 0 3px rgba(22,163,74,.15)';
    });
    input.addEventListener('blur', () => {
        input.style.borderColor = '';
        input.style.boxShadow   = '';
    });
});

// ── Setup form: validation ────────────────────────────────
const setupForm = document.querySelector('.setup-form');
if (setupForm) {
    setupForm.addEventListener('submit', (e) => {
        let valid = true;
        setupForm.querySelectorAll('input[required]').forEach(inp => {
            if (!inp.value.trim()) {
                inp.style.borderColor = '#dc2626';
                inp.style.boxShadow   = '0 0 0 3px rgba(220,38,38,0.15)';
                valid = false;
                inp.addEventListener('input', () => {
                    inp.style.borderColor = '';
                    inp.style.boxShadow   = '';
                }, { once: true });
            }
        });
        if (!valid) {
            e.preventDefault();
            const first = setupForm.querySelector('input[required]:placeholder-shown');
            if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
}

// ── Calculate button: loading state ───────────────────────
const calcForm = document.querySelector('.calc-form');
if (calcForm) {
    calcForm.addEventListener('submit', () => {
        const btn = calcForm.querySelector('.btn-calculate');
        if (btn) {
            btn.innerHTML = '<span class="calc-btn-icon">⏳</span> Calculating…';
            btn.disabled  = true;
            btn.style.opacity = '0.75';
        }
    });
}

// ── Smooth stat counter animation ────────────────────────
document.querySelectorAll('.stat-num').forEach(el => {
    const target = parseInt(el.textContent, 10);
    if (isNaN(target) || target === 0) return;
    let current = 0;
    const step  = Math.ceil(target / 30);
    const timer = setInterval(() => {
        current = Math.min(current + step, target);
        el.textContent = current;
        if (current >= target) clearInterval(timer);
    }, 40);
});
