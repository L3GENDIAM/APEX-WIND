#!/usr/bin/env python3
"""
APEX WIND  —  Wind Rose Diagram Generator
Transportation Engineering Runway Analysis
WEB by BILAL AHMED | Run: python windrose_redesign.py
"""
import sys, subprocess, io

def _in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False

if __name__ == "__main__" and not _in_streamlit():
    DEPS = [("streamlit","streamlit"),("matplotlib","matplotlib"),
            ("numpy","numpy"),("pandas","pandas"),
            ("reportlab","reportlab"),("openpyxl","openpyxl"),("Pillow","PIL")]
    print("\n  APEX WIND  —  Wind Rose Generator\n  " + "─"*40)
    for pkg, mod in DEPS:
        try: __import__(mod)
        except ImportError:
            print(f"  Installing {pkg}...")
            subprocess.check_call(
                [sys.executable,"-m","pip","install",pkg,"-q","--disable-pip-version-check"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("  Launching ->  http://localhost:8501\n")
    subprocess.run([sys.executable,"-m","streamlit","run",__file__,
        "--server.port=8501","--server.headless=false",
        "--browser.gatherUsageStats=false"])
    sys.exit(0)

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import time
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors as RC
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Image as RLImage, PageBreak, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

st.set_page_config(page_title="APEX WIND | Wind Rose", page_icon="✈️",
                   layout="wide", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════
DIRS_16    = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
              "S","SSW","SW","WSW","W","WNW","NW","NNW"]
C2D        = {d: i*22.5 for i,d in enumerate(DIRS_16)}
SPD_BINS   = [-0.001, 0.97, 4.08, 7.00, 11.08, 17.11, 21.58, 9999]
SPD_LABELS = ["<0.97","0.97-4.08","4.08-7.00","7.00-11.08","11.08-17.11","17.11-21.58",">=21.58"]
TBL_COLS   = ["0.97-4.08","4.08-7.00","7.00-11.08","11.08-17.11","17.11-21.58",">=21.58"]
TBL_IDX    = [1,2,3,4,5,6]
T2_COLORS  = ["#e0e0e0","#c8d8c8","#ffff00","#ff0000","#0000ff","#008000","#00ffff"]
T2_NAMES   = ["< 0.97 (Calms)","0.97-4.08","4.08-7.00","7.00-11.08","11.08-17.11","17.11-21.58",">= 21.58"]

# ── THEME PALETTE ──────────────────────────────────────────────────
TH = {
    "dark": {
        "bg":"#080e1f",
        "card_css":"rgba(16, 26, 58, 0.65)",
        "brd_css":"rgba(56, 189, 248, 0.28)",
        "brd2_css":"rgba(255, 255, 255, 0.07)",
        "acc":"#38bdf8",        # Sky-400
        "acc2":"#0ea5e9",       # Sky-500
        "acc3":"#7dd3fc",       # Sky-300 (lighter accent for variety)
        "gold":"#fbbf24",
        "suc":"#34d399",
        "dng":"#f87171",
        "txt":"#e2eaf4",
        "mut":"#64748b",
        "ibg":"rgba(8, 14, 31, 0.75)",
        "itxt":"#e2eaf4",
        "pbg":"#0f172a",
        "ptxt":"#e2eaf4",
        "psel":"#0c4a6e",
        "phov":"#0369a1",
        "ebg":"rgba(16, 26, 58, 0.85)",
        "etxt":"#e2eaf4",
        "shd":"0 16px 50px rgba(0, 0, 0, 0.75)",
        "blur":"blur(24px) saturate(140%)",
        "m_bg":"#080e1f",
        "m_card":"#101a3a",
        "m_grid":"#1e3a5f",
        "m_tick":"#64748b",
        "m_title":"#38bdf8",
        "m_poly":"#38bdf8",
        "m_pfill":"#075985",
    },
    "light": {
        "bg":"#f0f6ff",
        "card_css":"rgba(255, 255, 255, 0.80)",
        "brd_css":"rgba(14, 165, 233, 0.22)",
        "brd2_css":"rgba(0, 0, 0, 0.05)",
        "acc":"#0284c7",        # Sky-600
        "acc2":"#0369a1",       # Sky-700
        "acc3":"#38bdf8",       # Sky-400
        "gold":"#d97706",
        "suc":"#059669",
        "dng":"#dc2626",
        "txt":"#0f1c30",
        "mut":"#4b6280",
        "ibg":"rgba(255, 255, 255, 0.90)",
        "itxt":"#0f1c30",
        "pbg":"#ffffff",
        "ptxt":"#0f1c30",
        "psel":"#e0f2fe",
        "phov":"#bae6fd",
        "ebg":"rgba(240, 249, 255, 0.95)",
        "etxt":"#0f1c30",
        "shd":"0 12px 40px rgba(2, 132, 199, 0.12)",
        "blur":"blur(24px) saturate(140%)",
        "m_bg":"#f0f6ff",
        "m_card":"#ffffff",
        "m_grid":"#cbd5e1",
        "m_tick":"#4b6280",
        "m_title":"#0284c7",
        "m_poly":"#0284c7",
        "m_pfill":"#e0f2fe",
    },
}

_SS = dict(theme="light",diagrams={},freq=None,rwy1=None,rwy2=None,
           stats=None,cxlim=19.4,ready=False,show_table=False,
           _file_bytes=None,_file_name=None,_cols=None,
           _file_rows=0,_file_loaded=False,
           _pdf_details={},_pdf_logo=None,
           _processing=False)
for k,v in _SS.items():
    if k not in st.session_state: st.session_state[k]=v

# ══════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════
def inject_css():
    T=TH[st.session_state.theme]; dk=st.session_state.theme=="dark"
    g=f"linear-gradient(135deg, {T['acc']}, {T['acc2']})"
    g2=f"linear-gradient(135deg, {T['acc3']}, {T['acc']})"
    TXT=T["txt"]; MUT=T["mut"]; IBG=T["ibg"]; ITXT=T["itxt"]
    EBG=T["ebg"]; ETXT=T["etxt"]; PBG=T["pbg"]; PTXT=T["ptxt"]

    bg_img = "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=2500&auto=format&fit=crop"
    overlay = "rgba(8, 14, 31, 0.91)" if dk else "rgba(240, 246, 255, 0.90)"

    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Bebas+Neue&family=JetBrains+Mono:wght@300;400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── RESET & BASE ────────────────────────────────────────────── */
:root{{
  --acc:{T['acc']}; --acc2:{T['acc2']}; --acc3:{T['acc3']};
  --gold:{T['gold']}; --suc:{T['suc']}; --dng:{T['dng']};
  --txt:{TXT}; --mut:{MUT};
  --card:{T['card_css']}; --brd:{T['brd_css']}; --brd2:{T['brd2_css']};
  --grd:{g}; --grd2:{g2};
  --shd:{T['shd']}; --blur:{T['blur']}; --rad:14px; --rad-lg:20px;
}}

html,body,.stApp,[data-testid="stApp"],[data-testid="stAppViewContainer"]{{
  font-family:'DM Sans',sans-serif!important;
  color:{TXT}!important;
}}

/* ── BACKGROUND ─────────────────────────────────────────────── */
[data-testid="stAppViewContainer"]{{
  background-image:url('{bg_img}');
  background-size:cover; background-position:center center;
  background-attachment:fixed;
}}
[data-testid="stAppViewContainer"]::before{{
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background:{overlay};
  backdrop-filter:blur(2px);
}}

/* ── LAYOUT ─────────────────────────────────────────────────── */
.block-container{{
  position:relative; z-index:1;
  max-width:1080px!important;
  margin:0 auto!important;
  padding:2.5rem 2rem 7rem!important;
}}

/* ── HIDE CHROME ────────────────────────────────────────────── */
[data-testid="stSidebar"],section[data-testid="stSidebar"],
[data-testid="collapsedControl"],[data-testid="stSidebarNav"],
button[title="Open sidebar"],button[title="Close sidebar"],
[data-testid="stSidebarCollapseButton"]{{
  display:none!important;width:0!important;min-width:0!important;
}}
#MainMenu,header,footer{{visibility:hidden!important;}}

/* ── GLOBAL COLOR ENFORCEMENT ───────────────────────────────── */
*,*::before,*::after{{
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
}}
/* Exceptions for elements that handle their own color */
.stButton>button,button[data-testid],.zl-step-num,
.zl-sv,.zl-footer-brand,.zl-title em,
.zl-type-code,.zl-tag,.zl-dot,
.zl-pass,.zl-warn,.zl-fail,
.zl-chip,.zl-sub::before,
.zl-lbl,.zl-sv,.zl-sl,
.zl-cov b,.zl-dlbl,
.zl-tbl th,.zl-tbl td.dc,.zl-tbl tr.trow td,
.zl-freq-hdr,.zl-footer-link,
.zl-load-stage,.zl-load-pct,.zl-load-sub{{
  -webkit-text-fill-color:unset!important;
}}

/* ── SCROLLBAR ──────────────────────────────────────────────── */
::-webkit-scrollbar{{width:6px;height:6px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{
  background:{'rgba(56,189,248,0.3)' if dk else 'rgba(2,132,199,0.3)'};
  border-radius:99px;
}}
::-webkit-scrollbar-thumb:hover{{background:{T['acc']};}}

/* ══════════════════════════════════════════════════════════════
   INPUTS
══════════════════════════════════════════════════════════════ */
.stTextInput>div>div>input,
.stTextInput input,
.stNumberInput>div>div>input,
.stNumberInput input{{
  background:{IBG}!important;
  color:{ITXT}!important;
  -webkit-text-fill-color:{ITXT}!important;
  caret-color:{T['acc']}!important;
  border:1.5px solid {T['brd2_css']}!important;
  border-bottom:2px solid {T['brd_css']}!important;
  border-radius:{T.get('rad','14px') if 'rad' in T else '10px'}!important;
  font-family:'JetBrains Mono',monospace!important;
  font-size:.88rem!important;
  padding:.62rem 1rem!important;
  transition:all .25s ease!important;
  box-shadow:inset 0 1px 3px rgba(0,0,0,0.07)!important;
}}
.stTextInput>div>div>input:focus,
.stNumberInput>div>div>input:focus{{
  border-color:{T['acc']}!important;
  border-bottom-width:2.5px!important;
  background:{PBG}!important;
  box-shadow:
    0 0 0 3px {'rgba(56,189,248,0.12)' if dk else 'rgba(2,132,199,0.10)'},
    inset 0 1px 3px rgba(0,0,0,0.07)!important;
  transform:translateY(-1px)!important;
}}
.stTextInput>div>div>input::placeholder,
.stNumberInput>div>div>input::placeholder{{
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  opacity:.55!important;
}}

/* ── SELECT ─────────────────────────────────────────────────── */
.stSelectbox>div>div{{
  background:{IBG}!important;
  border:1.5px solid {T['brd2_css']}!important;
  border-bottom:2px solid {T['brd_css']}!important;
  border-radius:10px!important;
  transition:all .25s ease!important;
}}
.stSelectbox>div>div:hover{{
  border-color:{T['acc']}!important;
  box-shadow:0 4px 16px {'rgba(56,189,248,0.1)' if dk else 'rgba(2,132,199,0.08)'}!important;
}}
.stSelectbox [class*="singleValue"],
.stSelectbox [class*="placeholder"],
.stSelectbox [data-baseweb="select"] span,
.stSelectbox [data-baseweb="select"] div{{
  color:{ITXT}!important;
  -webkit-text-fill-color:{ITXT}!important;
  background:transparent!important;
}}
[data-baseweb="popover"],
[data-baseweb="popover"]>div,
div[data-baseweb="menu"],
ul[data-baseweb="menu"],
[data-baseweb="popover"] ul{{
  background-color:{PBG}!important;
  border:1px solid {T['brd_css']}!important;
  border-radius:12px!important;
  backdrop-filter:{T['blur']}!important;
  box-shadow:0 16px 48px {'rgba(0,0,0,0.65)' if dk else 'rgba(2,132,199,0.15)'}!important;
  overflow:hidden!important;
}}
[data-baseweb="popover"] li,
[data-baseweb="popover"] [role="option"],
div[data-baseweb="option"],
li[data-baseweb="option"]{{
  background:transparent!important;
  color:{PTXT}!important;
  -webkit-text-fill-color:{PTXT}!important;
  font-family:'JetBrains Mono',monospace!important;
  font-size:.84rem!important;
  padding:.5rem 1rem!important;
  transition:background .15s ease!important;
}}
[data-baseweb="popover"] li:hover,
div[data-baseweb="option"]:hover{{background:{T['phov']}!important;}}
[data-baseweb="popover"] [aria-selected="true"],
li[aria-selected="true"]{{
  background:{T['psel']}!important;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  font-weight:700!important;
}}

/* ── LABELS ─────────────────────────────────────────────────── */
.stTextInput label,
.stSelectbox label,
.stNumberInput label,
.stFileUploader label,
.stCheckbox label,
.stRadio label{{
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  font-family:'JetBrains Mono',monospace!important;
  font-size:.65rem!important;
  font-weight:700!important;
  letter-spacing:.12em!important;
  text-transform:uppercase!important;
  margin-bottom:.3rem!important;
}}
div[data-testid="stCheckbox"] label span,
div[data-testid="stRadio"] label span,
div[data-testid="stCheckbox"] p,
div[data-testid="stRadio"] p{{
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
  font-family:'DM Sans',sans-serif!important;
  font-size:.92rem!important;
  font-weight:500!important;
  text-transform:none!important;
  letter-spacing:0!important;
}}

/* ── BUTTONS (Secondary) ────────────────────────────────────── */
.stButton>button{{
  background:var(--card)!important;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  border:1.5px solid {T['brd_css']}!important;
  border-radius:10px!important;
  font-family:'JetBrains Mono',monospace!important;
  font-weight:700!important;
  font-size:.78rem!important;
  letter-spacing:.08em!important;
  text-transform:uppercase!important;
  padding:.56rem 1.2rem!important;
  width:100%!important;
  transition:all .25s cubic-bezier(.4,0,.2,1)!important;
  backdrop-filter:var(--blur)!important;
  position:relative!important;
  overflow:hidden!important;
}}
.stButton>button::after{{
  content:'';
  position:absolute; inset:0;
  background:{'rgba(56,189,248,0.06)' if dk else 'rgba(2,132,199,0.04)'};
  opacity:0;
  transition:opacity .25s ease!important;
}}
.stButton>button:hover{{
  border-color:{T['acc']}!important;
  transform:translateY(-2px)!important;
  box-shadow:0 8px 24px {'rgba(56,189,248,0.20)' if dk else 'rgba(2,132,199,0.16)'}!important;
}}
.stButton>button:hover::after{{opacity:1!important;}}
.stButton>button:active{{transform:translateY(0px)!important;}}

/* ── DOWNLOAD BUTTONS ───────────────────────────────────────── */
.stDownloadButton>button{{
  background:var(--card)!important;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  border:1.5px solid {T['brd_css']}!important;
  border-radius:12px!important;
  font-family:'JetBrains Mono',monospace!important;
  font-weight:700!important;
  font-size:.82rem!important;
  letter-spacing:.06em!important;
  text-transform:uppercase!important;
  padding:.7rem 1.5rem!important;
  width:100%!important;
  backdrop-filter:var(--blur)!important;
  transition:all .25s ease!important;
}}
.stDownloadButton>button:hover{{
  border-color:{T['acc']}!important;
  background:{'rgba(56,189,248,0.08)' if dk else 'rgba(2,132,199,0.06)'}!important;
  transform:translateY(-2px)!important;
  box-shadow:0 8px 24px {'rgba(56,189,248,0.22)' if dk else 'rgba(2,132,199,0.16)'}!important;
}}

/* ── FILE UPLOADER ──────────────────────────────────────────── */
[data-testid="stFileUploader"]{{
  background:{'rgba(8,14,31,0.50)' if dk else 'rgba(255,255,255,0.65)'}!important;
  border:2px dashed {T['brd_css']}!important;
  border-radius:var(--rad-lg)!important;
  padding:2rem 1.5rem!important;
  transition:all .3s ease!important;
  backdrop-filter:var(--blur)!important;
}}
[data-testid="stFileUploader"]:hover{{
  background:{'rgba(56,189,248,0.07)' if dk else 'rgba(2,132,199,0.05)'}!important;
  border-color:{T['acc']}!important;
  box-shadow:inset 0 0 24px {'rgba(56,189,248,0.08)' if dk else 'rgba(2,132,199,0.06)'}!important;
}}
[data-testid="stFileDropzoneInstructions"] p,
[data-testid="stFileDropzoneInstructions"] span{{
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  font-size:.88rem!important;
}}

/* ── ALERTS ─────────────────────────────────────────────────── */
.stSuccess{{
  background:{'rgba(52,211,153,0.08)' if dk else 'rgba(5,150,105,0.07)'}!important;
  border:1px solid {T['suc']}!important;
  border-left:4px solid {T['suc']}!important;
  border-radius:12px!important;
  backdrop-filter:var(--blur)!important;
}}
.stError{{
  background:{'rgba(248,113,113,0.08)' if dk else 'rgba(220,38,38,0.07)'}!important;
  border:1px solid {T['dng']}!important;
  border-left:4px solid {T['dng']}!important;
  border-radius:12px!important;
  backdrop-filter:var(--blur)!important;
}}
.stWarning{{
  background:{'rgba(251,191,36,0.08)' if dk else 'rgba(217,119,6,0.07)'}!important;
  border:1px solid {T['gold']}!important;
  border-left:4px solid {T['gold']}!important;
  border-radius:12px!important;
  backdrop-filter:var(--blur)!important;
}}
.stInfo{{
  background:{'rgba(56,189,248,0.08)' if dk else 'rgba(2,132,199,0.07)'}!important;
  border:1px solid {T['acc']}!important;
  border-left:4px solid {T['acc']}!important;
  border-radius:12px!important;
  backdrop-filter:var(--blur)!important;
}}

/* ── IMAGES ─────────────────────────────────────────────────── */
.stImage img,[data-testid="stImage"] img{{
  border-radius:var(--rad)!important;
  border:1px solid var(--brd)!important;
  box-shadow:var(--shd)!important;
}}

/* ══════════════════════════════════════════════════════════════
   HERO
══════════════════════════════════════════════════════════════ */
.zl-hero{{
  text-align:center;
  padding:3.5rem 1rem 1.5rem;
  position:relative;
}}
.zl-hero-glow{{
  position:absolute; top:-20px; left:50%; transform:translateX(-50%);
  width:70%; height:420px; pointer-events:none; z-index:0;
  background:{'radial-gradient(ellipse at 50% 30%, rgba(56,189,248,0.16) 0%, transparent 68%)' if dk
              else 'radial-gradient(ellipse at 50% 30%, rgba(2,132,199,0.13) 0%, transparent 68%)'};
  filter:blur(50px);
}}
.zl-tag{{
  display:inline-flex; align-items:center; gap:.6rem;
  font-family:'JetBrains Mono',monospace;
  font-size:.68rem; font-weight:700;
  letter-spacing:.16em; text-transform:uppercase;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  background:var(--card);
  border:1px solid {T['brd_css']};
  padding:.38rem 1.1rem; border-radius:99px;
  margin-bottom:1.8rem;
  backdrop-filter:var(--blur);
  box-shadow:0 4px 20px {'rgba(56,189,248,0.12)' if dk else 'rgba(2,132,199,0.10)'};
  position:relative; z-index:2;
}}
.zl-dot{{
  display:inline-block; width:7px; height:7px; border-radius:50%;
  background:{T['acc']};
  box-shadow:0 0 12px {T['acc']};
  animation:zl-pulse 2.4s ease-in-out infinite;
}}
@keyframes zl-pulse{{
  0%,100%{{opacity:1; transform:scale(1);}}
  50%{{opacity:.3; transform:scale(.75);}}
}}

/* Title uses Bebas Neue for impact */
.zl-title{{
  font-family:'Bebas Neue',sans-serif;
  font-size:clamp(4rem,9vw,7.5rem);
  font-weight:400;
  line-height:.92;
  letter-spacing:.04em;
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
  margin:.2rem 0 1.2rem;
  text-shadow:0 12px 40px rgba(0,0,0,0.5);
  position:relative; z-index:2;
}}
.zl-title em{{
  font-style:normal;
  background:{g};
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent!important;
  background-clip:text;
}}
.zl-tagline{{
  font-family:'DM Sans',sans-serif;
  font-size:1.1rem; font-weight:400;
  letter-spacing:-.005em;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  text-align:center; max-width:780px; margin:0 auto 2.5rem;
  line-height:1.65; position:relative; z-index:2;
}}
.zl-chips{{
  display:flex; flex-wrap:wrap; justify-content:center;
  gap:.55rem; position:relative; z-index:2;
}}
.zl-chip{{
  font-family:'JetBrains Mono',monospace;
  font-size:.63rem; font-weight:600;
  letter-spacing:.07em; text-transform:uppercase;
  background:var(--card);
  border:1px solid {T['brd2_css']};
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  padding:.38rem .85rem; border-radius:8px;
  transition:all .25s cubic-bezier(.4,0,.2,1);
  backdrop-filter:var(--blur);
}}
.zl-chip:hover{{
  border-color:{T['acc']};
  background:{'rgba(56,189,248,0.07)' if dk else 'rgba(2,132,199,0.05)'};
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  transform:translateY(-3px);
  box-shadow:0 8px 20px {'rgba(56,189,248,0.18)' if dk else 'rgba(2,132,199,0.13)'};
}}

/* ── THEME TOGGLE ────────────────────────────────────────────── */
.zl-theme-wrap{{
  display:flex; justify-content:center;
  margin-top:1.6rem; margin-bottom:.8rem;
  position:relative; z-index:5;
}}
.zl-theme-group{{
  display:inline-flex;
  background:var(--card);
  border:1px solid {T['brd_css']};
  border-radius:99px; padding:4px;
  backdrop-filter:var(--blur);
  box-shadow:0 4px 16px rgba(0,0,0,0.15);
}}
.zl-theme-group .stButton{{width:auto!important;}}
.zl-theme-group .stButton>button{{
  background:transparent!important;
  border:none!important;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  padding:.38rem 1.1rem!important;
  font-size:.68rem!important;
  font-weight:700!important;
  border-radius:99px!important;
  box-shadow:none!important;
  letter-spacing:.10em!important;
  transition:all .25s ease!important;
}}
.zl-theme-group .stButton>button:hover{{
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  background:transparent!important;
  transform:none!important;
}}
.zl-theme-active .stButton>button{{
  background:{'rgba(56,189,248,0.18)' if dk else 'rgba(2,132,199,0.13)'}!important;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
}}

/* ── DIVIDER ─────────────────────────────────────────────────── */
.zl-hr{{
  height:1px; margin:2.8rem 0; border:none;
  background:{'linear-gradient(90deg,transparent 0%,rgba(56,189,248,0.35) 40%,rgba(56,189,248,0.35) 60%,transparent 100%)' if dk
              else 'linear-gradient(90deg,transparent 0%,rgba(2,132,199,0.25) 40%,rgba(2,132,199,0.25) 60%,transparent 100%)'};
}}

/* ── SECTION HEADER ──────────────────────────────────────────── */
.zl-section{{
  display:flex; align-items:center; gap:.9rem; margin:0 0 1.6rem;
}}
.zl-section-line{{
  flex:1; height:1px;
  background:{'linear-gradient(90deg,rgba(56,189,248,0.25),transparent)' if dk
              else 'linear-gradient(90deg,rgba(2,132,199,0.18),transparent)'};
}}
.zl-lbl{{
  font-family:'Space Grotesk',sans-serif;
  font-size:1.25rem; font-weight:700; letter-spacing:-.01em;
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
  white-space:nowrap;
}}

/* ── GLASS CARD ──────────────────────────────────────────────── */
.zl-card{{
  background:var(--card);
  border:1px solid var(--brd);
  border-radius:var(--rad-lg);
  padding:1.8rem;
  backdrop-filter:var(--blur);
  box-shadow:var(--shd);
  margin-bottom:1.2rem;
  position:relative; overflow:hidden;
  transition:box-shadow .3s ease;
}}
.zl-card::before{{
  content:''; position:absolute;
  top:0; left:0; right:0; height:2.5px;
  background:var(--grd); opacity:.85;
}}
.zl-card:hover{{
  box-shadow:0 20px 60px {'rgba(0,0,0,0.8)' if dk else 'rgba(2,132,199,0.16)'}!important;
}}

.zl-info-card{{
  background:{'linear-gradient(135deg,rgba(56,189,248,0.09),rgba(8,14,31,0.55))' if dk
              else 'linear-gradient(135deg,rgba(2,132,199,0.07),rgba(255,255,255,0.75))'};
  border:1px solid {T['brd_css']};
  border-left:3.5px solid {T['acc']};
  border-radius:12px; padding:1rem 1.3rem; margin-bottom:1.5rem;
  backdrop-filter:var(--blur);
}}

/* ── SUBHEADING ──────────────────────────────────────────────── */
.zl-sub{{
  font-family:'JetBrains Mono',monospace;
  font-size:.7rem; font-weight:700;
  letter-spacing:.14em; text-transform:uppercase;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  margin-bottom:.85rem;
  display:flex; align-items:center; gap:.55rem;
}}
.zl-sub::before{{
  content:'';
  display:inline-block; width:3.5px; height:14px;
  background:var(--grd); border-radius:2px; flex-shrink:0;
}}
.zl-hint{{
  font-family:'JetBrains Mono',monospace;
  font-size:.69rem;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  line-height:1.75; margin-top:.45rem;
}}

/* ── STEPS ───────────────────────────────────────────────────── */
.zl-step{{
  display:flex; align-items:flex-start; gap:1.1rem;
  padding:1rem 0; border-bottom:1px solid {T['brd2_css']};
  transition:transform .2s ease, opacity .2s ease;
}}
.zl-step:hover{{transform:translateX(5px); opacity:.95;}}
.zl-step:last-child{{border-bottom:none;}}
.zl-step-num{{
  width:34px; height:34px; border-radius:9px; flex-shrink:0;
  background:var(--grd);
  color:{'#080e1f' if dk else '#ffffff'}!important;
  -webkit-text-fill-color:{'#080e1f' if dk else '#ffffff'}!important;
  font-family:'Space Grotesk',sans-serif;
  font-size:.95rem; font-weight:700;
  display:flex; align-items:center; justify-content:center;
  box-shadow:0 4px 14px {'rgba(56,189,248,0.35)' if dk else 'rgba(2,132,199,0.28)'};
}}
.zl-step-title{{
  font-family:'Space Grotesk',sans-serif;
  font-size:1rem; font-weight:600;
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
  margin-bottom:.2rem;
}}
.zl-step-desc{{
  font-size:.84rem;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  line-height:1.65;
}}

/* ── TYPE CARDS ──────────────────────────────────────────────── */
.zl-type-grid{{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:.9rem; margin:.5rem 0 1rem;
}}
.zl-type-card{{
  background:var(--card);
  border:1px solid var(--brd);
  border-radius:var(--rad-lg);
  padding:1.4rem 1.2rem;
  transition:all .3s cubic-bezier(.4,0,.2,1);
  position:relative; overflow:hidden;
  backdrop-filter:var(--blur);
  box-shadow:var(--shd);
}}
.zl-type-card::before{{
  content:''; position:absolute;
  top:0; left:0; width:100%; height:3px;
  background:var(--grd); opacity:0;
  transition:opacity .3s ease;
}}
.zl-type-card:hover{{
  border-color:{T['acc']};
  transform:translateY(-7px);
  box-shadow:0 20px 45px {'rgba(0,0,0,0.7)' if dk else 'rgba(2,132,199,0.22)'};
}}
.zl-type-card:hover::before{{opacity:1;}}
.zl-type-code{{
  font-family:'Bebas Neue',sans-serif;
  font-size:2.8rem; font-weight:400; line-height:1;
  background:var(--grd);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent!important;
  background-clip:text; margin-bottom:.3rem;
  letter-spacing:.05em;
}}
.zl-type-name{{
  font-family:'JetBrains Mono',monospace;
  font-size:.63rem; font-weight:700;
  letter-spacing:.09em; text-transform:uppercase;
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
  margin-bottom:.6rem;
}}
.zl-type-desc{{
  font-size:.8rem;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  line-height:1.6; margin-top:.4rem;
}}
.zl-type-badge{{
  display:inline-flex; align-items:center; gap:5px;
  font-family:'JetBrains Mono',monospace;
  font-size:.58rem; font-weight:700;
  letter-spacing:.07em; text-transform:uppercase;
  padding:.22rem .65rem; border-radius:6px;
}}
.zl-badge-t1{{
  background:{'rgba(56,189,248,0.14)' if dk else 'rgba(2,132,199,0.11)'};
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
}}
.zl-badge-t2{{
  background:{'rgba(52,211,153,0.14)' if dk else 'rgba(5,150,105,0.11)'};
  color:{T['suc']}!important;
  -webkit-text-fill-color:{T['suc']}!important;
}}

/* ── STAT CARDS ──────────────────────────────────────────────── */
.zl-stats{{
  display:grid; grid-template-columns:repeat(6,1fr);
  gap:.7rem; margin:1.2rem 0;
}}
.zl-stat{{
  background:var(--card);
  border:1px solid var(--brd);
  border-radius:14px; padding:1.1rem .6rem;
  text-align:center; backdrop-filter:var(--blur);
  transition:all .25s ease; box-shadow:var(--shd);
  position:relative; overflow:hidden;
}}
.zl-stat::after{{
  content:''; position:absolute;
  bottom:0; left:0; right:0; height:2px;
  background:var(--grd); opacity:0;
  transition:opacity .25s ease;
}}
.zl-stat:hover{{
  border-color:{T['acc']};
  transform:translateY(-4px);
  box-shadow:0 12px 32px {'rgba(56,189,248,0.15)' if dk else 'rgba(2,132,199,0.14)'};
}}
.zl-stat:hover::after{{opacity:1;}}
.zl-sv{{
  font-family:'Space Grotesk',sans-serif;
  font-size:1.55rem; font-weight:700;
  background:var(--grd);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent!important;
  background-clip:text; line-height:1.1;
}}
.zl-sl{{
  font-family:'JetBrains Mono',monospace;
  font-size:.52rem; font-weight:700;
  letter-spacing:.12em; text-transform:uppercase;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  margin-top:.4rem;
}}

/* ── COVERAGE BAR ────────────────────────────────────────────── */
.zl-cov{{
  background:var(--card);
  border:1px solid var(--brd);
  border-radius:14px;
  padding:1rem 1.4rem;
  font-family:'JetBrains Mono',monospace;
  font-size:.8rem;
  color:{TXT}!important;
  display:flex; flex-wrap:wrap; gap:1.2rem; align-items:center;
  margin:1rem 0; backdrop-filter:var(--blur); box-shadow:var(--shd);
  border-left:3.5px solid {T['acc']};
}}
.zl-cov b{{
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  font-size:.88rem;
}}
.zl-pass,.zl-fail,.zl-warn{{
  display:inline-flex; align-items:center; gap:.4rem;
  font-family:'JetBrains Mono',monospace;
  font-size:.68rem; font-weight:800;
  letter-spacing:.10em; text-transform:uppercase;
  padding:4px 13px; border-radius:99px;
}}
.zl-pass{{
  background:{'rgba(52,211,153,0.13)' if dk else 'rgba(5,150,105,0.10)'};
  border:1px solid {T['suc']};
  color:{T['suc']}!important;
  -webkit-text-fill-color:{T['suc']}!important;
}}
.zl-fail{{
  background:{'rgba(248,113,113,0.13)' if dk else 'rgba(220,38,38,0.10)'};
  border:1px solid {T['dng']};
  color:{T['dng']}!important;
  -webkit-text-fill-color:{T['dng']}!important;
}}
.zl-warn{{
  background:{'rgba(251,191,36,0.13)' if dk else 'rgba(217,119,6,0.10)'};
  border:1px solid {T['gold']};
  color:{T['gold']}!important;
  -webkit-text-fill-color:{T['gold']}!important;
}}

/* ── DIAGRAM PREVIEWS ────────────────────────────────────────── */
.zl-dlbl{{
  font-family:'Space Grotesk',sans-serif;
  font-size:.92rem; font-weight:700; letter-spacing:.02em;
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
  text-align:center; padding:.6rem .2rem .45rem;
}}
.zl-diag-frame{{
  background:#ffffff;
  border-radius:16px; padding:10px;
  margin-bottom:.8rem;
  box-shadow:0 12px 40px {'rgba(0,0,0,0.65)' if dk else 'rgba(2,132,199,0.14)'};
  border:2px solid {'rgba(56,189,248,0.35)' if dk else 'rgba(2,132,199,0.22)'};
  transition:box-shadow .3s ease;
}}
.zl-diag-frame:hover{{
  box-shadow:0 20px 56px {'rgba(0,0,0,0.75)' if dk else 'rgba(2,132,199,0.22)'}!important;
}}

/* ── GENERATE BUTTON (PRIMARY) ───────────────────────────────── */
.zl-gen-wrap .stButton>button{{
  background:var(--grd)!important;
  color:{'#080e1f' if dk else '#ffffff'}!important;
  -webkit-text-fill-color:{'#080e1f' if dk else '#ffffff'}!important;
  font-family:'Space Grotesk',sans-serif!important;
  font-size:1.15rem!important;
  font-weight:700!important;
  letter-spacing:.06em!important;
  text-transform:uppercase!important;
  padding:1.15rem 2.5rem!important;
  border-radius:14px!important;
  border:none!important;
  box-shadow:0 8px 30px {'rgba(56,189,248,0.38)' if dk else 'rgba(2,132,199,0.32)'}!important;
  transition:all .3s ease!important;
}}
.zl-gen-wrap .stButton>button:hover{{
  transform:translateY(-4px)!important;
  box-shadow:0 16px 44px {'rgba(56,189,248,0.55)' if dk else 'rgba(2,132,199,0.48)'}!important;
  filter:brightness(1.06)!important;
}}
.zl-gen-wrap .stButton>button:active{{
  transform:translateY(-1px)!important;
}}

/* ── LOADING SCREEN ──────────────────────────────────────────── */
.zl-loading-screen{{
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  padding:4rem 1rem; gap:0;
  background:var(--card); border:1px solid var(--brd);
  border-radius:var(--rad-lg); backdrop-filter:var(--blur);
  margin:1.5rem 0; box-shadow:var(--shd);
}}
.takeoff-loader{{
  position:relative; width:220px; height:80px;
  margin-bottom:2rem; overflow:hidden;
}}
.takeoff-plane{{
  position:absolute; font-size:46px;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  bottom:10px; left:-20%;
  animation:flyplane 2.8s ease-in infinite;
  filter:drop-shadow(0 4px 10px {'rgba(56,189,248,0.6)' if dk else 'rgba(2,132,199,0.5)'});
}}
.takeoff-rwy{{
  position:absolute; bottom:10px; left:0;
  width:100%; height:4px;
  background:{'rgba(255,255,255,0.15)' if dk else 'rgba(0,0,0,0.15)'};
  border-radius:4px;
}}
.takeoff-rwy::after{{
  content:''; position:absolute; top:0; left:0;
  width:100%; height:100%;
  background:repeating-linear-gradient(90deg,{T['acc']} 0,{T['acc']} 20px,transparent 20px,transparent 40px);
  opacity:.75;
}}
@keyframes flyplane{{
  0%{{left:-20%;bottom:10px;transform:rotate(0deg);opacity:0;}}
  10%{{opacity:1;}}
  45%{{left:30%;bottom:10px;transform:rotate(0deg);}}
  75%{{left:65%;bottom:35px;transform:rotate(-22deg);}}
  100%{{left:120%;bottom:100px;transform:rotate(-35deg);opacity:0;}}
}}
.zl-load-stage{{
  font-family:'Space Grotesk',sans-serif;
  font-size:1.25rem; font-weight:700;
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
  letter-spacing:.01em; margin-bottom:.4rem;
}}
.zl-load-pct{{
  font-family:'JetBrains Mono',monospace;
  font-size:.82rem; font-weight:700;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  letter-spacing:.16em; margin-bottom:1.5rem;
}}
.zl-load-bar-outer{{
  width:300px; height:5px;
  background:{'rgba(56,189,248,0.12)' if dk else 'rgba(2,132,199,0.12)'};
  border-radius:99px; overflow:hidden;
  margin-bottom:1rem;
  box-shadow:inset 0 1px 3px rgba(0,0,0,0.2);
}}
.zl-load-bar-fill{{
  height:100%; border-radius:99px;
  background:var(--grd);
  transition:width .35s cubic-bezier(.4,0,.2,1);
  box-shadow:0 0 12px {T['acc']};
}}
.zl-load-sub{{
  font-family:'JetBrains Mono',monospace;
  font-size:.68rem; font-weight:600;
  letter-spacing:.16em; text-transform:uppercase;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
}}

/* ── FREQUENCY TABLE ─────────────────────────────────────────── */
.zl-freq-box{{
  background:{EBG};
  border:1px solid {T['brd_css']};
  border-radius:var(--rad-lg); padding:1.5rem;
  margin:1rem 0; box-shadow:var(--shd);
  backdrop-filter:var(--blur);
}}
.zl-freq-hdr{{
  font-family:'Space Grotesk',sans-serif;
  font-size:1.15rem; font-weight:700;
  color:{TXT}!important;
  -webkit-text-fill-color:{TXT}!important;
  margin-bottom:.25rem;
}}
.zl-freq-note{{
  font-family:'JetBrains Mono',monospace;
  font-size:.68rem; font-weight:500;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  margin-bottom:1rem; line-height:1.7;
}}
.zl-tbl{{
  width:100%; border-collapse:collapse;
  font-family:'JetBrains Mono',monospace;
  font-size:.74rem; border-radius:10px; overflow:hidden;
}}
.zl-tbl th{{
  background:{'rgba(8,14,31,0.92)' if dk else 'rgba(2,132,199,0.88)'}!important;
  color:#ffffff!important;
  -webkit-text-fill-color:#ffffff!important;
  padding:10px 12px;
  letter-spacing:.07em; font-size:.68rem;
  text-align:center; font-weight:700;
  border-bottom:2.5px solid {T['acc']};
}}
.zl-tbl th.dh{{text-align:left;}}
.zl-tbl td{{
  padding:8px 12px;
  border-bottom:1px solid {T['brd2_css']};
  text-align:center;
  color:{ETXT}!important;
  -webkit-text-fill-color:{ETXT}!important;
  font-size:.77rem;
  transition:background .15s ease;
}}
.zl-tbl td.dc{{
  font-weight:700; text-align:left;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  background:{'rgba(56,189,248,0.05)' if dk else 'rgba(2,132,199,0.04)'}!important;
}}
.zl-tbl tr:nth-child(even) td{{
  background:{'rgba(255,255,255,0.015)' if dk else 'rgba(2,132,199,0.025)'}!important;
}}
.zl-tbl tr:hover td{{
  background:{'rgba(56,189,248,0.07)' if dk else 'rgba(2,132,199,0.07)'}!important;
}}
.zl-tbl tr.trow td{{
  font-weight:800;
  border-top:2.5px solid {T['acc']};
  background:{'rgba(56,189,248,0.10)' if dk else 'rgba(2,132,199,0.08)'}!important;
  border-bottom:none;
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
}}

/* ── FILE BANNER ─────────────────────────────────────────────── */
.zl-file-banner{{
  font-family:'JetBrains Mono',monospace;
  font-size:.78rem; font-weight:500;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  background:{'rgba(56,189,248,0.07)' if dk else 'rgba(2,132,199,0.06)'};
  border:1px solid {T['brd_css']};
  border-radius:10px; padding:.55rem 1rem;
  margin-top:.5rem;
}}
.zl-file-banner b{{
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
}}

/* ── FOOTER ──────────────────────────────────────────────────── */
.zl-footer{{
  background:var(--card);
  border:1px solid var(--brd);
  border-radius:var(--rad-lg);
  padding:3rem 2rem; text-align:center;
  margin-top:4rem; backdrop-filter:var(--blur);
  box-shadow:var(--shd); position:relative; overflow:hidden;
}}
.zl-footer::before{{
  content:''; position:absolute;
  top:0; left:0; right:0; height:2.5px;
  background:var(--grd);
}}
.zl-footer-brand{{
  font-family:'Bebas Neue',sans-serif;
  font-size:2rem; font-weight:400;
  letter-spacing:.12em;
  background:var(--grd);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent!important;
  background-clip:text; margin-bottom:.5rem;
}}
.zl-footer-line{{
  font-family:'JetBrains Mono',monospace;
  font-size:.72rem; font-weight:500;
  color:{MUT}!important;
  -webkit-text-fill-color:{MUT}!important;
  margin:.3rem 0;
}}
.zl-footer-link{{
  color:{T['acc']}!important;
  -webkit-text-fill-color:{T['acc']}!important;
  text-decoration:none; font-weight:700;
}}
.zl-footer-link:hover{{text-decoration:underline;}}
.zl-footer-divider{{
  width:60px; height:2.5px;
  background:var(--grd);
  border-radius:3px; margin:1rem auto;
}}

/* ── RESPONSIVE ──────────────────────────────────────────────── */
@media(max-width:768px){{
  .zl-type-grid{{grid-template-columns:repeat(2,1fr)!important;}}
  .zl-stats{{grid-template-columns:repeat(3,1fr)!important;}}
  .zl-title{{font-size:3.5rem!important;}}
}}
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════
def section(label):
    return (f'<div class="zl-section">'
            f'<div class="zl-lbl">{label}</div>'
            f'<div class="zl-section-line"></div></div>')

def zl_loading(pct, stage, substage=""):
    return (f'<div class="zl-loading-screen">'
            f'<div class="takeoff-loader">'
            f'<div class="takeoff-plane">&#9992;</div>'
            f'<div class="takeoff-rwy"></div>'
            f'</div>'
            f'<div class="zl-load-stage">{stage}</div>'
            f'<div class="zl-load-pct">{pct:.0f}% COMPLETE</div>'
            f'<div class="zl-load-bar-outer">'
            f'<div class="zl-load-bar-fill" style="width:{pct:.0f}%;"></div></div>'
            f'<div class="zl-load-sub">{substage}</div></div>')

def sc(v, l):
    return (f'<div class="zl-stat"><div class="zl-sv">{v}</div>'
            f'<div class="zl-sl">{l}</div></div>')

# ══════════════════════════════════════════════════════════════════════
#  DATA PROCESSING
# ══════════════════════════════════════════════════════════════════════
def load_file(f):
    name=f.name.lower(); raw=f.read(); f.seek(0)
    if name.endswith((".xlsx",".xls")):
        try: return pd.read_excel(io.BytesIO(raw),engine="openpyxl"), None
        except Exception as e: return None, str(e)
    for enc in ("utf-8","utf-8-sig","latin-1","cp1252"):
        try: return pd.read_csv(io.BytesIO(raw),encoding=enc,low_memory=False), None
        except Exception: pass
    return None, "Cannot decode file."

@st.cache_data(show_spinner=False)
def process_data(fb, fname, dc, sc_col, dfmt, su):
    name=fname.lower()
    if name.endswith((".xlsx",".xls")): df=pd.read_excel(io.BytesIO(fb),engine="openpyxl")
    else:
        df=None
        for enc in ("utf-8","utf-8-sig","latin-1","cp1252"):
            try: df=pd.read_csv(io.BytesIO(fb),encoding=enc,low_memory=False); break
            except Exception: pass
        if df is None: raise ValueError("Cannot decode file.")
    df.columns=df.columns.str.strip()
    for col in (dc,sc_col):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found. Available: {list(df.columns)}")
    w=df[[dc,sc_col]].copy(); w.columns=["dir","spd"]
    if dfmt=="Compass (N, NNE ...)":
        w["dg"]=w["dir"].astype(str).str.strip().str.upper().map(C2D)
    else:
        w["dg"]=pd.to_numeric(w["dir"],errors="coerce")%360
    w["kmh"]=pd.to_numeric(w["spd"],errors="coerce")
    if su=="knots": w["kmh"]*=1.852
    elif su=="m/s":  w["kmh"]*=3.6
    w=w.dropna(subset=["dg","kmh"])
    if len(w)==0: raise ValueError("No valid rows after processing.")
    w["sec"]=(((w["dg"]+11.25)%360)//22.5).astype(int).clip(0,15)
    w["sc"]=pd.cut(w["kmh"],bins=SPD_BINS,labels=list(range(7))).astype(float).astype("Int64")
    total=len(w); freq=np.zeros((16,7))
    for s in range(16):
        for c in range(7):
            freq[s,c]=((w.sec==s)&(w.sc==c)).sum()/total*100
    op=freq[:,1:7].sum(axis=1)
    return freq,{"total":total,"calm":round(freq[:,0].sum(),1),
                 "op":round(op.sum(),1),"avg":round(w.kmh.mean(),1),
                 "max":round(w.kmh.max(),1),"dom":DIRS_16[int(op.argmax())]}

# ══════════════════════════════════════════════════════════════════════
#  RUNWAY ANALYSIS
# ══════════════════════════════════════════════════════════════════════
def ha(cx): return np.degrees(np.arcsin(min(cx/24.1,1.)))

def rwy_cov(freq,hdg,cx):
    h=ha(cx); t=0.
    for i in range(16):
        d=abs(((i*22.5-hdg+180)%360)-180)
        if d<=h or d>=180-h: t+=freq[i,1:7].sum()
    return min(t,100.)

def best_rwy(freq,cx,excl=None):
    bh,bc=0.,0.
    for hdg in np.arange(0,180,5):
        if excl is not None and abs(((hdg-excl+90)%180)-90)<20: continue
        c=rwy_cov(freq,hdg,cx)
        if c>bc: bc,bh=c,hdg
    return float(bh)

def comb_cov(freq,r1,r2,cx):
    h=ha(cx); t=0.
    for i in range(16):
        a=i*22.5; d1=abs(((a-r1+180)%360)-180); d2=abs(((a-r2+180)%360)-180)
        if d1<=h or d1>=180-h or d2<=h or d2>=180-h: t+=freq[i,1:7].sum()
    return min(t,100.)

def best_rwy_combined(freq, r1, cx):
    bh, bc = 0., 0.
    for hdg in np.arange(0, 180, 5):
        if abs(((hdg - r1 + 90) % 180) - 90) < 20: continue
        c = comb_cov(freq, r1, hdg, cx)
        if c > bc: bc, bh = c, hdg
    return float(bh)

def rwy_lbl(hdg):
    e1=int(round(hdg/10))%36 or 36; e2=int(round((hdg+180)/10))%36 or 36
    return f"Runway {e1:02d}/{e2:02d}"

# ══════════════════════════════════════════════════════════════════════
#  FREQUENCY TABLE
# ══════════════════════════════════════════════════════════════════════
def freq_table_html(freq, T):
    note=(f'Calms (&lt;0.97 Knots) = {freq[:,0].sum():.1f}%  ·  '
          f'Strong (&ge;21.58 Knots) = {freq[:,6].sum():.1f}%  ·  '
          f'Operational (&ge;0.97 Knots) = {sum(freq[:,j].sum() for j in TBL_IDX):.1f}%')
    th_cols="".join([f"<th>{c}</th>" for c in TBL_COLS])
    hdr=(f'<tr><th class="dh" rowspan="2">Direction</th>'
         f'<th colspan="{len(TBL_COLS)}">Duration of Wind (%)</th>'
         f'<th rowspan="2">Total % above 0.97 Knots</th></tr>'
         f'<tr>{th_cols}</tr>')
    rows=""
    for i,d in enumerate(DIRS_16):
        td_cells="".join([f"<td>{freq[i,j]:.1f}</td>" for j in TBL_IDX])
        tot=sum(freq[i,j] for j in TBL_IDX)
        rows+=(f'<tr><td class="dc">{d}</td>{td_cells}<td>{tot:.1f}</td></tr>')
    t_cells="".join([f"<td>{freq[:,j].sum():.1f}</td>" for j in TBL_IDX])
    tt=sum(freq[:,j].sum() for j in TBL_IDX)
    rows+=(f'<tr class="trow"><td class="dc">TOTAL</td>{t_cells}<td>{tt:.1f}</td></tr>')
    return (f'<div class="zl-freq-box"><div class="zl-freq-hdr">Wind Frequency Table</div>'
            f'<div class="zl-freq-note">{note}</div>'
            f'<table class="zl-tbl">{hdr}{rows}</table></div>')

def freq_to_csv(freq):
    rows=[]
    for i,d in enumerate(DIRS_16):
        r={"Direction":d}
        for j,lbl in enumerate(TBL_COLS): r[lbl]=round(freq[i,TBL_IDX[j]],4)
        r["Total % (>0.97 Knots)"]=round(sum(freq[i,j] for j in TBL_IDX),4)
        rows.append(r)
    t={"Direction":"TOTAL"}
    for j,lbl in enumerate(TBL_COLS): t[lbl]=round(freq[:,TBL_IDX[j]].sum(),4)
    t["Total % (>0.97 Knots)"]=round(sum(freq[:,j].sum() for j in TBL_IDX),4)
    rows.append(t)
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")

# ══════════════════════════════════════════════════════════════════════
#  DIAGRAM RENDERERS
# ══════════════════════════════════════════════════════════════════════
def _polar(title, theme):
    T=TH[theme]
    fig,ax=plt.subplots(figsize=(7.5,7.5),subplot_kw=dict(polar=True),facecolor="#ffffff")
    ax.set_facecolor("#f8faff")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.grid(color="#d4dff0",linestyle="--",lw=0.55,alpha=0.8)
    ax.spines["polar"].set_color("#dde4f0")
    ax.set_xticks(np.linspace(0,2*np.pi,16,endpoint=False))
    ax.set_xticklabels(DIRS_16,fontsize=9,fontweight="bold",color="#0d2244",fontfamily="monospace")
    ax.tick_params(axis="y",labelsize=7.5,labelcolor="#3d5a80")
    ax.set_title(title,fontsize=10.5,fontweight="bold",pad=26,color=T["m_title"],wrap=True)
    return fig,ax

def _leg(ax, handles):
    ax.legend(handles=handles,loc="lower left",bbox_to_anchor=(-0.22,-0.28),
              fontsize=8,framealpha=0.97,facecolor="#ffffff",
              edgecolor="#ccd4ee",labelcolor="#0d2244")

def _png(fig):
    buf=io.BytesIO()
    fig.savefig(buf,format="png",dpi=160,bbox_inches="tight",facecolor="#ffffff")
    plt.close(fig); buf.seek(0); return buf.getvalue()

def _refcircles(ax, mv):
    for frac in [.25,.5,.75,1.]:
        rv=mv*frac
        ax.plot(np.linspace(0,2*np.pi,200),[rv]*200,color="#ccd4ee",lw=0.6,alpha=0.7,zorder=1)
        ax.text(np.radians(10),rv,f"{rv:.1f}%",fontsize=6,color="#6688aa",ha="left",va="bottom")

def render_t1s(freq, theme):
    T=TH[theme]; dp=freq[:,1:7].sum(axis=1); N=16
    th=np.linspace(0,2*np.pi,N,endpoint=False); mv=max(dp.max(),1.)
    fig,ax=_polar("TYPE I  —  SINGLE RUNWAY\n",theme)
    _refcircles(ax,mv)
    ax.fill(th,dp,color=T["m_pfill"],alpha=0.35,zorder=2)
    ax.plot(np.append(th,th[0]),np.append(dp,dp[0]),color=T["m_poly"],lw=2.4,alpha=0.95,zorder=3)
    sz=[100 if dp[i]>=mv*.90 else 60 if dp[i]>=mv*.60 else 30 for i in range(N)]
    ax.scatter(th,dp,s=sz,color=T["m_poly"],zorder=4,edgecolors="#ffffff",linewidths=0.9)
    dom=int(np.argmax(dp))
    ax.text(th[dom],dp[dom]*1.16,f"{dp[dom]:.1f}%",fontsize=8.5,color=T["m_poly"],
            ha="center",va="bottom",fontweight="bold")
    ax.set_ylim(0,mv*1.30)
    _leg(ax,[mpatches.Patch(color=T["m_pfill"],alpha=0.5,label="Wind Rose Diagram"),
             plt.Line2D([0],[0],color=T["m_poly"],lw=2.4,label="Polygon outline"),
             plt.Line2D([0],[0],marker='o',color=T["m_poly"],lw=0,markersize=5.5,label="Direction value")])
    plt.tight_layout(rect=[0,.07,1,.97]); return _png(fig)

def render_t1m(freq, theme):
    T=TH[theme]; dp=freq[:,1:7].sum(axis=1); N=16
    th=np.linspace(0,2*np.pi,N,endpoint=False); mv=max(dp.max(),1.)
    fig,ax=_polar("TYPE I  —  MULTI RUNWAY\n",theme)
    _refcircles(ax,mv)
    ax.fill(th,dp,color=T["m_pfill"],alpha=0.32,zorder=2)
    ax.plot(np.append(th,th[0]),np.append(dp,dp[0]),color=T["m_poly"],lw=2.4,alpha=0.92,zorder=3)
    ax.scatter(th,dp,s=32,color=T["m_poly"],zorder=4,edgecolors="#ffffff",linewidths=0.8)
    dom=int(np.argmax(dp))
    ax.text(th[dom],dp[dom]*1.16,f"{dp[dom]:.1f}%",fontsize=8,color=T["m_poly"],
            ha="center",va="bottom",fontweight="bold")
    ax.set_ylim(0,mv*1.32)
    _leg(ax,[mpatches.Patch(color=T["m_pfill"],alpha=0.5,label="Wind Rose Diagram"),
             plt.Line2D([0],[0],color=T["m_poly"],lw=2.4,label="Polygon outline"),
             plt.Line2D([0],[0],marker='o',color=T["m_poly"],lw=0,markersize=5.5,label="Direction value")])
    plt.tight_layout(rect=[0,.07,1,.97]); return _png(fig)

def render_t2s(freq, theme):
    T=TH[theme]; N=16
    th=np.linspace(0,2*np.pi,N,endpoint=False); w=2*np.pi/N*.80
    fig,ax=_polar("TYPE II  —  SINGLE RUNWAY\n",theme)
    bot=np.zeros(N)
    for s in range(7):
        ax.bar(th,freq[:,s],width=w,bottom=bot,color=T2_COLORS[s],
               edgecolor="#ffffff",lw=0.45,alpha=0.93,label=T2_NAMES[s],zorder=3)
        bot+=freq[:,s]
    dom=int(bot.argmax())
    ax.text(th[dom],bot[dom]*1.10,f"{bot[dom]:.1f}%",fontsize=8,
            color="#0d2244",ha="center",va="bottom",fontweight="bold")
    ax.set_ylim(0,bot.max()*1.22 or 1)
    _leg(ax,[mpatches.Patch(color=T2_COLORS[i],label=T2_NAMES[i]) for i in range(7)])
    plt.tight_layout(rect=[0,.09,1,.97]); return _png(fig)

def render_t2m(freq, theme):
    T=TH[theme]; N=16
    th=np.linspace(0,2*np.pi,N,endpoint=False); w=2*np.pi/N*.80
    fig,ax=_polar("TYPE II  —  MULTI RUNWAY\n",theme)
    bot=np.zeros(N)
    for s in range(7):
        ax.bar(th,freq[:,s],width=w,bottom=bot,color=T2_COLORS[s],
               edgecolor="#ffffff",lw=0.45,alpha=0.93,label=T2_NAMES[s],zorder=3)
        bot+=freq[:,s]
    dom=int(bot.argmax())
    ax.text(th[dom],bot[dom]*1.10,f"{bot[dom]:.1f}%",fontsize=8,
            color="#0d2244",ha="center",va="bottom",fontweight="bold")
    ax.set_ylim(0,bot.max()*1.22 or 1)
    _leg(ax,[mpatches.Patch(color=T2_COLORS[i],label=T2_NAMES[i]) for i in range(7)])
    plt.tight_layout(rect=[0,.10,1,.97]); return _png(fig)

# ══════════════════════════════════════════════════════════════════════
#  PDF BUILDER
# ══════════════════════════════════════════════════════════════════════
def build_pdf(diagrams, details, logo_b=None):
    buf=io.BytesIO(); PW,PH=A4; MG=1.8*cm; lr=None
    if logo_b:
        try: lr=ImageReader(io.BytesIO(logo_b))
        except Exception: pass
    def pg(cvs,doc):
        cvs.saveState()
        cvs.setFont("Times-Bold",9.5); cvs.setFillColor(RC.HexColor("#0d1829"))
        cvs.drawCentredString(PW/2,PH-1.0*cm,"WIND ROSE DIAGRAM REPORT")
        cvs.setLineWidth(0.7); cvs.setStrokeColor(RC.HexColor("#0d1829"))
        cvs.line(MG,PH-1.35*cm,PW-MG,PH-1.35*cm)
        if lr:
            ls=1.4*cm
            try: cvs.drawImage(lr,PW-MG-ls,PH-1.32*cm,width=ls,height=ls,preserveAspectRatio=True,mask="auto")
            except Exception: pass
        cvs.line(MG,1.4*cm,PW-MG,1.4*cm)
        cvs.setFont("Times-Roman",8.5); cvs.setFillColor(RC.black)
        l1=[]
        if details.get('name'): l1.append(details['name'].strip())
        if details.get('roll'): l1.append(f"Roll No: {details['roll'].strip()}")
        if details.get('sec'):  l1.append(f"Section: {details['sec'].strip()}")
        if details.get('date'): l1.append(f"Date: {details['date'].strip()}")
        if l1: cvs.drawString(MG, 0.95*cm, "  |  ".join(l1))
        l2=[]
        if details.get('proj'): l2.append(details['proj'].strip())
        if details.get('inst'): l2.append(f"Instructor: {details['inst'].strip()}")
        if details.get('site'): l2.append(f"Site: {details['site'].strip()}")
        if details.get('dept'): l2.append(f"Dept: {details['dept'].strip()}")
        if l2: cvs.drawString(MG, 0.55*cm, "  |  ".join(l2))
        cvs.drawRightString(PW-MG,0.75*cm,f"Page {doc.page}")
        cvs.restoreState()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=MG,rightMargin=MG,topMargin=1.9*cm,bottomMargin=1.8*cm)
    sty_t=ParagraphStyle("t",fontName="Times-Bold",fontSize=15,textColor=RC.HexColor("#0d1829"),alignment=TA_CENTER,spaceAfter=4)
    sty_c=ParagraphStyle("c",fontName="Times-Italic",fontSize=9,textColor=RC.HexColor("#444"),alignment=TA_CENTER,spaceAfter=4)
    ORD=["t1s","t1m","t2s","t2m"]
    LBL={"t1s":"Type I - Single Runway  (Polygon)","t1m":"Type I - Multi Runway  (Polygon)",
         "t2s":"Type II - Single Runway  (Speed Bars)","t2m":"Type II - Multi Runway  (Speed Bars)"}
    story=[]; first=True
    for key in ORD:
        if key not in diagrams: continue
        if not first: story.append(PageBreak())
        first=False
        story.append(Paragraph(f"Wind Rose Diagram - {LBL[key]}",sty_t))
        story.append(HRFlowable(width="100%",thickness=0.8,color=RC.HexColor("#0d1829"),spaceAfter=10))
        story.append(Spacer(1,0.4*cm))
        story.append(RLImage(io.BytesIO(diagrams[key]),width=14.5*cm,height=14.5*cm,kind="proportional"))
        story.append(Spacer(1,0.25*cm))
        story.append(Paragraph(f"Figure: {LBL[key]}",sty_c))
    if not story: story.append(Paragraph("No diagrams selected.",sty_t))
    doc.build(story,onFirstPage=pg,onLaterPages=pg)
    buf.seek(0); return buf.getvalue()

# ══════════════════════════════════════════════════════════════════════
#  MAIN UI
# ══════════════════════════════════════════════════════════════════════
def main():
    inject_css()
    T=TH[st.session_state.theme]; dk=st.session_state.theme=="dark"

    # ── HERO ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="zl-hero">
      <div class="zl-hero-glow"></div>
      <div class="zl-tag"><span class="zl-dot"></span>Transportation Engineering · Runway Analysis</div>
      <div class="zl-title">APEX <em>WIND</em></div>
      <div class="zl-tagline">Engineered for Safety: Advanced Runway Coverage &amp; Wind Studies.</div>
      <div class="zl-chips">
        <span class="zl-chip">Automated WRD</span>
        <span class="zl-chip">ICAO Compliant</span>
        <span class="zl-chip">Type I &amp; Type II</span>
        <span class="zl-chip">PDF Export</span>
        <span class="zl-chip">16-Direction Analysis</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── THEME TOGGLE ───────────────────────────────────────────────
    st.markdown('<div class="zl-theme-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="zl-theme-group">', unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        btn_cls = "zl-theme-active" if not dk else ""
        st.markdown(f'<div class="{btn_cls}">', unsafe_allow_html=True)
        if st.button("☀ LIGHT", key="theme_l", use_container_width=True):
            st.session_state.theme="light"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with sc2:
        btn_cls = "zl-theme-active" if dk else ""
        st.markdown(f'<div class="{btn_cls}">', unsafe_allow_html=True)
        if st.button("☾ DARK", key="theme_d", use_container_width=True):
            st.session_state.theme="dark"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="zl-hr"></div>', unsafe_allow_html=True)

    # ── HOW IT WORKS ──────────────────────────────────────────────
    st.markdown(section("How It Works"), unsafe_allow_html=True)
    hc1,hc2=st.columns(2,gap="large")
    steps=[("Data Ingestion","Upload raw meteorological datasets via CSV or Excel formats."),
           ("Variable Mapping","Assign specific parameters for wind direction and velocity attributes."),
           ("Unit Configuration","Define precise velocity metrics and directional formatting schemes."),
           ("Project Metadata","Embed professional engineering credentials for final documentation."),
           ("Algorithmic Computation","Execute ICAO-compliant crosswind coverage mathematical models."),
           ("Final Export","Generate comprehensive PDF schematics and analytical frequency matrices.")]
    with hc1:
        html_c1 = '<div class="zl-card" style="padding:0.5rem 1.5rem;">'
        for i,(t,d) in enumerate(steps[:3],1):
            html_c1 += (f'<div class="zl-step"><div class="zl-step-num">{i}</div>'
                        f'<div><div class="zl-step-title">{t}</div>'
                        f'<div class="zl-step-desc">{d}</div></div></div>')
        html_c1 += '</div>'
        st.markdown(html_c1, unsafe_allow_html=True)
    with hc2:
        html_c2 = '<div class="zl-card" style="padding:0.5rem 1.5rem;">'
        for i,(t,d) in enumerate(steps[3:],4):
            html_c2 += (f'<div class="zl-step"><div class="zl-step-num">{i}</div>'
                        f'<div><div class="zl-step-title">{t}</div>'
                        f'<div class="zl-step-desc">{d}</div></div></div>')
        html_c2 += '</div>'
        st.markdown(html_c2, unsafe_allow_html=True)

    # ── DIAGRAM TYPES ──────────────────────────────────────────────
    st.markdown('<div class="zl-hr"></div>', unsafe_allow_html=True)
    st.markdown(section("Diagram Types"), unsafe_allow_html=True)
    st.markdown("""<div class="zl-type-grid">
      <div class="zl-type-card">
        <div class="zl-type-code">I·S</div>
        <div class="zl-type-name">Type I — Single Runway</div>
        <span class="zl-type-badge zl-badge-t1">&#11042; Polygon Method</span>
        <div class="zl-type-desc">Generates a closed directional polygon to isolate the primary wind vector. Ideal for single runway planning.</div>
      </div>
      <div class="zl-type-card">
        <div class="zl-type-code">I·M</div>
        <div class="zl-type-name">Type I — Multi Runway</div>
        <span class="zl-type-badge zl-badge-t1">&#11043; Polygon Method</span>
        <div class="zl-type-desc">Projects dual-axis alignments over a single wind polygon for complex, intersecting runway configurations.</div>
      </div>
      <div class="zl-type-card">
        <div class="zl-type-code">II·S</div>
        <div class="zl-type-name">Type II — Single Runway</div>
        <span class="zl-type-badge zl-badge-t2">&#128202; Speed Bar Method</span>
        <div class="zl-type-desc">Dissects wind vectors into six distinct velocity tiers, providing granular operational visibility.</div>
      </div>
      <div class="zl-type-card">
        <div class="zl-type-code">II·M</div>
        <div class="zl-type-name">Type II — Multi Runway</div>
        <span class="zl-type-badge zl-badge-t2">&#128201; Speed Bar Method</span>
        <div class="zl-type-desc">Evaluates intricate layouts by applying multi-tiered velocity bars to determine optimal multidirectional coverage.</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── UPLOAD & CONFIG ────────────────────────────────────────────
    st.markdown('<div class="zl-hr"></div>', unsafe_allow_html=True)
    st.markdown(section("Upload &amp; Configure"), unsafe_allow_html=True)
    st.markdown('<div class="zl-sub">Wind Data File</div>', unsafe_allow_html=True)

    uploaded=st.file_uploader("Upload file",type=["csv","xlsx","xls"],
                               label_visibility="collapsed",key="wind_file")
    st.markdown('<div class="zl-hint">Requires: wind_direction + wind_speed columns  ·  '
                'Speed processed in Knots  ·  Date/Time columns ignored automatically  ·  '
                'Supports multi-year historical datasets</div>', unsafe_allow_html=True)

    if uploaded is not None:
        load_ph=st.empty()
        load_ph.markdown(zl_loading(0,"Reading File","Detecting encoding and structure..."),unsafe_allow_html=True)
        df_tmp,err=load_file(uploaded); uploaded.seek(0)
        load_ph.empty()
        if err or df_tmp is None:
            st.error(f"Cannot read file: {err}"); st.session_state._file_loaded=False
        else:
            raw=uploaded.read(); uploaded.seek(0)
            st.session_state._file_bytes=raw; st.session_state._file_name=uploaded.name
            st.session_state._cols=list(df_tmp.columns)
            st.session_state._file_rows=len(df_tmp); st.session_state._file_loaded=True

    fl=st.session_state._file_loaded; cols=st.session_state._cols or []
    fn=st.session_state._file_name or ""; fr=st.session_state._file_rows or 0

    if fl:
        st.markdown(f'<div class="zl-file-banner">&#10003;&nbsp;<b>{fn}</b>&nbsp;&nbsp;'
                    f'&middot;&nbsp;&nbsp;{fr:,} rows&nbsp;&nbsp;&middot;&nbsp;&nbsp;{len(cols)} columns'
                    f'</div>', unsafe_allow_html=True)

    if fl and cols:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="zl-sub">Column Mapping</div>', unsafe_allow_html=True)
        def _g(opts,kws):
            for kw in kws:
                for i,c in enumerate(opts):
                    if kw in c.lower(): return i
            return 0
        di=_g(cols,["dir","wd","wind_d"]); si=_g(cols,["spee","ws","wind_s","vel"])
        if si==di: si=min(di+1,len(cols)-1)
        m1,m2,m3,m4=st.columns(4)
        with m1: dir_col=st.selectbox("Direction Column",cols,index=di,key="dcol")
        with m2: spd_col=st.selectbox("Speed Column",cols,index=si,key="scol")
        with m3: dir_fmt=st.selectbox("Direction Format",["Degrees (0-360)","Compass (N, NNE ...)"],key="dfmt")
        with m4: spd_unit=st.selectbox("Input Speed Unit",["km/h","knots","m/s"],index=1,key="sunit")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="zl-sub">Runway Configuration</div>', unsafe_allow_html=True)
        rw1,rw2,rw3,rw4=st.columns(4)
        with rw1:
            cx_s=st.selectbox("Crosswind Limit",
                ["10.5 Knots (19.4 km/h) — Light Aircraft",
                 "13.0 Knots (24.1 km/h) — Medium Aircraft",
                 "20.0 Knots (37.0 km/h) — Heavy Aircraft"],key="cxs")
            cxlim=float(cx_s.split("(")[1].split()[0])
        with rw2: auto=st.checkbox("Auto-detect runways",value=True,key="auto")
        with rw3: r1_in=st.number_input("Runway 1 heading (deg)",0,179,0,5,disabled=auto,key="r1i")
        with rw4: r2_in=st.number_input("Runway 2 heading (deg)",0,179,45,5,disabled=auto,key="r2i")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="zl-sub">Select Diagrams</div>', unsafe_allow_html=True)
        d1,d2,d3,d4=st.columns(4)
        with d1: s_t1s=st.checkbox("Type I  — Single",value=True,key="ct1s")
        with d2: s_t1m=st.checkbox("Type I  — Multi",value=True,key="ct1m")
        with d3: s_t2s=st.checkbox("Type II — Single",value=True,key="ct2s")
        with d4: s_t2m=st.checkbox("Type II — Multi",value=True,key="ct2m")
        sel={"t1s":s_t1s,"t1m":s_t1m,"t2s":s_t2s,"t2m":s_t2m}

    # ── ENGINEER & REPORT DETAILS ──────────────────────────────────
    st.markdown('<div class="zl-hr"></div>', unsafe_allow_html=True)
    st.markdown(section("Engineer &amp; Report Details"), unsafe_allow_html=True)
    st.markdown(f'<div class="zl-info-card">'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.73rem;'
                f'letter-spacing:.05em;color:{T["mut"]};">'
                f'Customize your PDF by adding an optional logo to the header and information to the footer below.'
                f'</span></div>', unsafe_allow_html=True)

    ui1,ui2,ui3,ui4=st.columns(4)
    with ui1: stu_name=st.text_input("Engineer Name",key="sname",placeholder="e.g. Bilal Ahmed")
    with ui2: stu_roll=st.text_input("Seat Number",key="sroll",placeholder="e.g. CE-21045")
    with ui3: stu_sec =st.text_input("Section / Group",key="ssec",placeholder="e.g. Section A")
    with ui4: stu_date=st.text_input("Date",key="sdate",placeholder="e.g. 17 April 2026")

    st.markdown("<br>", unsafe_allow_html=True)

    ui5,ui6,ui7,ui8=st.columns(4)
    with ui5: stu_proj=st.text_input("Project Title",key="sproj",placeholder="e.g. CE-432 Wind Rose Analysis")
    with ui6: stu_inst=st.text_input("Instructor",key="sinst",placeholder="e.g. Dr. Example")
    with ui7: stu_site=st.text_input("Site Location",key="ssite",placeholder="e.g. NEDUET")
    with ui8: stu_dept=st.text_input("Department / Firm",key="sdept",placeholder="e.g. Civil Engineering")

    st.markdown("<br>", unsafe_allow_html=True)
    lc1,lc2,lc3=st.columns([1,2,1])
    with lc2:
        logo_file=st.file_uploader("Organization Logo (Centered)",type=["png","jpg","jpeg"],
                                   key="logo_up",label_visibility="visible")

    # ── GENERATE BUTTON ───────────────────────────────────────────
    gen_btn=False
    if fl:
        st.markdown("<br>", unsafe_allow_html=True)
        _,gc,_=st.columns([1,3,1])
        with gc:
            st.markdown('<div class="zl-gen-wrap">', unsafe_allow_html=True)
            gen_btn=st.button("Generate Wind Rose Reports",use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── GENERATE LOGIC ────────────────────────────────────────────
    if gen_btn:
        if not fl:
            st.warning("Please upload a wind data file first.")
        elif not any(sel.values()):
            st.warning("Please select at least one diagram type.")
        else:
            st.session_state['_pdf_details']={
                'name':stu_name,'roll':stu_roll,'sec':stu_sec,'date':stu_date,
                'proj':stu_proj,'inst':stu_inst,'site':stu_site,'dept':stu_dept
            }
            if logo_file is not None:
                try: st.session_state['_pdf_logo']=logo_file.read(); logo_file.seek(0)
                except: st.session_state['_pdf_logo']=None
            else: st.session_state['_pdf_logo']=None

            ph=st.empty()
            ph.markdown(zl_loading(0,"Initialising","Preparing data pipeline..."),unsafe_allow_html=True)
            try:
                freq,stats=process_data(st.session_state._file_bytes,st.session_state._file_name,
                                        dir_col,spd_col,dir_fmt,spd_unit)
            except ValueError as e:
                ph.empty(); st.error(f"Data error: {e}"); st.stop()
            except Exception as e:
                ph.empty(); st.error(f"Error: {e}"); st.stop()

            ph.markdown(zl_loading(15,"Parsing Wind Records","Classifying speed bins..."),unsafe_allow_html=True)

            if auto:
                r1=best_rwy(freq,cxlim)
                r2=best_rwy_combined(freq,r1,cxlim)
            else:
                r1,r2=float(r1_in),float(r2_in)

            ph.markdown(zl_loading(28,"Runway Headings Resolved","Computing coverage angles..."),unsafe_allow_html=True)
            tnow=st.session_state.theme; diags={}
            rmap={"t1s":lambda:render_t1s(freq,tnow),"t1m":lambda:render_t1m(freq,tnow),
                  "t2s":lambda:render_t2s(freq,tnow),"t2m":lambda:render_t2m(freq,tnow)}
            lmap={"t1s":"Type I Single","t1m":"Type I Multi","t2s":"Type II Single","t2m":"Type II Multi"}
            substages={"t1s":"Rendering polygon wind rose...","t1m":"Rendering multi-runway polygon...",
                       "t2s":"Rendering speed-bar diagram...","t2m":"Rendering multi-runway bars..."}
            ts=sum(sel.values()); done=0
            for key,fn in rmap.items():
                if not sel[key]: continue
                try: diags[key]=fn()
                except Exception as e: st.warning(f"Cannot render {key}: {e}")
                done+=1
                ph.markdown(zl_loading(28+done/ts*68,f"Rendering {lmap[key]}",substages[key]),unsafe_allow_html=True)

            ph.markdown(zl_loading(100,"Analysis Complete","All diagrams generated successfully"),unsafe_allow_html=True)
            time.sleep(0.6); ph.empty()

            st.session_state.diagrams=diags; st.session_state.freq=freq
            st.session_state.rwy1=r1; st.session_state.rwy2=r2
            st.session_state.stats=stats; st.session_state.cxlim=cxlim
            st.session_state.ready=True
            st.success(f"  {len(diags)} diagram(s) generated successfully.")

    # ── RESULTS ───────────────────────────────────────────────────
    if st.session_state.ready and st.session_state.diagrams:
        freq=st.session_state.freq; r1=st.session_state.rwy1
        r2=st.session_state.rwy2; stats=st.session_state.stats
        cx=st.session_state.cxlim; diags=st.session_state.diagrams
        c1=rwy_cov(freq,r1,cx); c2=rwy_cov(freq,r2,cx)
        cc=comb_cov(freq,r1,r2,cx); icao=cc>=95.

        st.markdown('<div class="zl-hr"></div>', unsafe_allow_html=True)
        st.markdown(section("Analysis Results"), unsafe_allow_html=True)

        st.markdown('<div class="zl-stats">'
                    +sc(f"{stats['total']:,}","Total Obs.")
                    +sc(f"{stats['calm']:.1f}%","Calm Wind")
                    +sc(f"{stats['op']:.1f}%","Operational")
                    +sc(f"{stats['avg']:.1f} kt","Avg Speed")
                    +sc(stats['dom'],"Dominant Dir.")
                    +sc(f"{cc:.1f}%","Combined Cov.")
                    +'</div>', unsafe_allow_html=True)

        badge=(f'<span class="zl-pass">&#10003; ICAO COMPLIANT &ge;95%</span>'
               if icao else f'<span class="zl-warn">&#9888; ICAO REVIEW &lt;95%</span>')
        st.markdown(f"""<div class="zl-cov">
          &#9992; <b>{rwy_lbl(r1)}</b>: {c1:.1f}%
          &nbsp;&middot;&nbsp; &#9992; <b>{rwy_lbl(r2)}</b>: {c2:.1f}%
          &nbsp;&middot;&nbsp; Combined: <b>{cc:.1f}%</b>
          &nbsp;&middot;&nbsp; CW Limit: <b>{cx:.1f} kt</b>
          &nbsp;&middot;&nbsp; {badge}
        </div>""", unsafe_allow_html=True)

        # ── FREQUENCY TABLE ──────────
        tog_lbl="Hide Frequency Table" if st.session_state.show_table else "Show Frequency Table"
        if st.button(tog_lbl,key="tog_tbl"):
            st.session_state.show_table=not st.session_state.show_table; st.rerun()

        if st.session_state.show_table:
            st.markdown(freq_table_html(freq,T), unsafe_allow_html=True)
            ec1,ec2=st.columns([2,3])
            with ec1:
                st.download_button(label="Export Frequency Table CSV",
                                   data=freq_to_csv(freq),
                                   file_name="wind_frequency_table.csv",
                                   mime="text/csv",key="csv_dl")

        # ── DIAGRAM PREVIEWS ──────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(section("Diagram Previews"), unsafe_allow_html=True)
        DLBL={"t1s":"Type I — Single Runway","t1m":"Type I — Multi Runway",
              "t2s":"Type II — Single Runway","t2m":"Type II — Multi Runway"}
        vis=[k for k in ["t1s","t1m","t2s","t2m"] if k in diags]
        for ri in range(0,len(vis),2):
            row_k=vis[ri:ri+2]; rcols=st.columns(len(row_k),gap="large")
            for ci,key in enumerate(row_k):
                with rcols[ci]:
                    st.markdown(f'<div class="zl-dlbl">{DLBL[key]}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="zl-diag-frame">', unsafe_allow_html=True)
                    st.image(diags[key],use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.download_button(label=f"⬇ Download {DLBL[key]} (PNG)",
                                       data=diags[key],
                                       file_name=f"WindRose_{key}.png",
                                       mime="image/png",
                                       use_container_width=True,
                                       key=f"dl_btn_{key}")

        # ── PDF EXPORT ──────────────
        st.markdown('<div class="zl-hr"></div>', unsafe_allow_html=True)
        st.markdown(section("Export PDF Report"), unsafe_allow_html=True)

        _pdet=st.session_state.get('_pdf_details',{})
        _pl=st.session_state.get('_pdf_logo',None)

        st.info("Diagrams ready. Download your full wind rose report below.")
        _,dc,_=st.columns([1,2,1])
        with dc:
            with st.spinner("Building PDF..."):
                pdf_b=build_pdf(diags,_pdet,_pl)
            st.download_button("Download PDF Report",data=pdf_b,
                               file_name="WindRose_Report.pdf",
                               mime="application/pdf",use_container_width=True)

    # ── FOOTER ────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="zl-footer">
      <div class="zl-footer-brand">APEX WIND</div>
      <div class="zl-footer-divider"></div>
      <div class="zl-footer-line">Transportation Engineering &nbsp;&middot;&nbsp; Runway Analysis Engine</div>
      <div style="font-family:'Space Grotesk',sans-serif;font-size:.82rem;font-weight:700;
           letter-spacing:.06em;color:{T['acc']};-webkit-text-fill-color:{T['acc']};margin:.8rem 0 .3rem;">
        DEVELOPED BY BILAL AHMED
      </div>
      <div class="zl-footer-line">
        Contact: <a class="zl-footer-link" href="mailto:ba67363636@gmail.com">ba67363636@gmail.com</a>
      </div>
      <div class="zl-footer-line" style="margin-top:1rem;font-size:.63rem;opacity:.55;">
        &copy; 2026 APEX WIND. All rights reserved. Version 7.3.
      </div>
    </div>""", unsafe_allow_html=True)

main()
