import os
import re
import io
from datetime import datetime
from typing import Dict, Any, List, Tuple

import streamlit as st
st.set_page_config(page_title="안심전세 리포트", layout="wide")

PDF_OK = False
OCR_OK = False
OPENAI_OK = True

pdfplumber = None
Image = None
pytesseract = None

try:
    import importlib
    pdfplumber = importlib.import_module("pdfplumber")
    PDF_OK = True
except Exception:
    PDF_OK = False

try:
    from PIL import Image as PILImage
    Image = PILImage
    OCR_OK = True
except Exception:
    OCR_OK = False

try:
    import pytesseract as _pytesseract
    pytesseract = _pytesseract
except Exception:
    pytesseract = None

try:
    from openai import OpenAI
except Exception:
    OPENAI_OK = False

import pandas as pd

BROKER_CSV_PATH = "data/부동산중개업소.csv"

@st.cache_data
def load_broker_csv(path: str):
    # ⚠️ 공공데이터 CSV는 cp949인 경우가 많음
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    # 정규화 컬럼(공백 제거)
    if "등록번호" in df.columns:
        df["_reg"] = df["등록번호"].str.replace(" ", "", regex=False)
    else:
        df["_reg"] = ""
    if "상호" in df.columns:
        df["_name"] = df["상호"].str.replace(" ", "", regex=False)
    else:
        df["_name"] = ""
    return df

BROKER_DF = load_broker_csv(BROKER_CSV_PATH)

st.markdown(
"""
<style>
/* =========================
   Global layout & reset
   ========================= */
.block-container { max-width: 1020px; padding-top: 2rem; padding-bottom: 3rem; }
html, body, [data-testid="stAppViewContainer"] {
  background: #F6F7FB !important;
  color: #111827 !important; /* ✅ 전역 텍스트는 검정 */
}
header, footer { visibility: hidden; height: 0; }

/* 혹시 어떤 요소가 상속을 안 타고 흰색으로 박혀있을 때 대비 */
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] span,
[data-testid="stAppViewContainer"] div,
[data-testid="stAppViewContainer"] label {
  color: inherit;
}

/* =========================
   Typography
   ========================= */
.kicker { color:#111827; font-weight: 800; font-size: 0.95rem; letter-spacing: -0.2px; }
.title { font-size: 1.85rem; font-weight: 950; letter-spacing: -0.9px; margin: 0.15rem 0 0.25rem 0; }
.sub { color: #6B7280; font-size: 0.98rem; margin-bottom: 1.25rem; }
.muted { color:#6B7280; font-size: 0.95rem; }

/* =========================
   Cards / blocks
   ========================= */
.box, .resultCard {
  background: #FFFFFF;
  border: 1px solid #E8EBF3;
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 1px 0 rgba(17,24,39,0.04);
  color: #111827; /* ✅ 카드 안 텍스트도 검정 */
}
.hr { height:1px; background:#EEF0F6; margin: 14px 0; }

.sectionTitle { font-weight: 950; letter-spacing:-0.4px; margin-top: 6px; }

.badges { display:flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.badge {
  display:inline-block; padding: 6px 10px; border-radius: 999px;
  background:#F7F8FC; border:1px solid #E8EBF3; font-size: 0.92rem; color:#111827;
}
.chip { display:inline-block; padding: 6px 10px; border-radius: 999px; font-size: 0.92rem; font-weight: 900; }
.chip.low { background: #ECFDF5; color:#065F46; border:1px solid #A7F3D0; }
.chip.mid { background: #FFFBEB; color:#92400E; border:1px solid #FDE68A; }
.chip.high { background: #FEF2F2; color:#991B1B; border:1px solid #FECACA; }

.warnTitle { font-size: 1.2rem; font-weight: 950; letter-spacing: -0.5px; margin: 0; }
.warnRed { color: #EF4444; font-weight: 950; }
.warnSub { color:#6B7280; margin-top: 6px; }

.lock {
  display:inline-flex; align-items:center; justify-content:center;
  width: 34px; height: 34px; border-radius: 10px; border:1px solid #E8EBF3;
  background:#F7F8FC; color:#6B7280;
}

/* =========================
   Tabs
   ========================= */
.stTabs [data-baseweb="tab"] {
  border-radius: 999px !important;
  padding: 10px 14px !important;
  background: #FFFFFF !important;
  border: 1px solid #E8EBF3 !important;
  margin-right: 8px !important;
  color: #111827 !important;
}
.stTabs [aria-selected="true"] {
  background: #111827 !important;
  color: #FFFFFF !important;
  border-color: #111827 !important;
}

/* =========================
   Inputs (핵심)
   - 라벨/설명: 검정(전역 상속)
   - 입력창 내부: 다크 배경 + 흰 글씨
   ========================= */
.stNumberInput input, .stTextInput input, .stTextArea textarea { border-radius: 14px !important; }

/* input root 배경은 흰색 유지 (레이아웃 박스 느낌) */
[data-testid="stTextInputRoot"],
[data-testid="stNumberInput"],
[data-testid="stTextAreaRoot"] {
  background: #FFFFFF !important;
}

/* ✅ 입력창(inside)만 다크 */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
  color: #FFFFFF !important;
  background-color: #1F2937 !important;
}

/* placeholder */
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
  color: #9CA3AF !important;
}

/* number_input +/- 버튼 */
[data-testid="stNumberInput"] button {
  color: #FFFFFF !important;
}

/* focus */
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  outline: none !important;
  border: 1px solid #6366F1 !important;
  box-shadow: 0 0 0 1px #6366F1 !important;
}

/* =========================
   Buttons
   ========================= */
.stButton button {
  border-radius: 14px !important;
  border: 1px solid #E8EBF3 !important;
  background: #111827 !important;
  color: #FFFFFF !important;
  padding: 0.55rem 0.9rem !important;
}
.stButton button:hover { filter: brightness(1.05); }

/* =========================
   File uploader (Browse files 글자/설명)
   ========================= */
[data-testid="stFileUploader"] button {
  color: #FFFFFF !important;
}
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small {
  color: #E5E7EB !important;
}

/* =========================
   Radio (전세/월세/미선택 텍스트)
   - BaseWeb radio 내부 텍스트를 직접 지정
   ========================= */
[data-testid="stRadio"] [data-baseweb="radio"] span,
[data-testid="stRadio"] [data-baseweb="radio"] div,
[data-testid="stRadio"] [data-baseweb="radio"] p {
  color: #111827 !important;
  font-weight: 700 !important;
}

/* =========================
   Signals
   ========================= */
.signal {
  background:#FFFFFF; border:1px solid #E8EBF3; border-radius: 14px; padding: 12px 12px; margin-bottom: 10px;
}
.signal-title { font-weight: 950; color:#111827; margin-bottom: 4px; }
.signal-detail { color:#374151; }
.signal-meta { color:#6B7280; font-size: 0.9rem; margin-top: 6px; }

/* empty box hide */
.resultCard:empty { display: none !important; }
.box:empty { display: none !important; }

</style>
""",
unsafe_allow_html=True,
)

st.markdown("<div class='kicker'>안전빵</div>", unsafe_allow_html=True)
st.markdown("<div class='title'>전월세 계약 전, 위험 신호를 미리 확인하세요</div>", unsafe_allow_html=True)
st.markdown("<div class='sub'>서류 업로드 또는 보증금·시세 입력만으로도 리스크 요인을 점검할 수 있어요.</div>", unsafe_allow_html=True)

def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, str]:
    """
    1) pdfplumber로 텍스트 추출 시도
    2) 텍스트가 비어있으면(스캔본 가능) PyMuPDF(fitz)로 렌더링 → OCR fallback
    """
    # 1) 텍스트 기반 PDF 추출
    if PDF_OK and pdfplumber is not None:
        try:
            parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    if t.strip():
                        parts.append(t)
            text = "\n".join(parts).strip()
            if text:
                return text, "pdf:ok"
        except Exception:
            # 텍스트 추출 자체가 실패하면 아래 OCR fallback로 내려감
            pass

    # 2) OCR fallback (스캔/촬영 PDF)
    # OCR 가능한 환경인지 확인
    if not (OCR_OK and Image is not None and pytesseract is not None):
        return "", "pdf:ocr_no_ocr"

    # PyMuPDF(fitz)로 페이지를 이미지로 렌더링해서 OCR
    try:
        import fitz  # PyMuPDF
    except Exception:
        return "", "pdf:ocr_no_fitz"

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        ocr_parts = []
        for page in doc:
            pix = page.get_pixmap(dpi=300)  # ✅ 200 -> 300 (글자 선명도↑)

            mode = "RGB" if pix.alpha == 0 else "RGBA"
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            if mode == "RGBA":
                img = img.convert("RGB")

            # ✅ 전처리: 그레이스케일 + 이진화(흑백)로 노이즈 줄이기
            try:
                img = img.convert("L")  # grayscale
                img = img.point(lambda x: 0 if x < 170 else 255, "1")  # threshold(임계값)
            except Exception:
                pass

            try:
                t = (pytesseract.image_to_string(
                    img,
                    lang="kor",  # ✅ 계약서가 한글+숫자면 kor만이 더 깔끔한 경우 많음
                    config="--oem 3 --psm 6"
                ) or "").strip()
            except Exception:
                doc.close()
                return "", "pdf:ocr_no_tesseract"

            if t:
                ocr_parts.append(t)

        doc.close()
        ocr_text = "\n".join(ocr_parts).strip()
        return (ocr_text, "pdf:ocr_ok") if ocr_text else ("", "pdf:ocr_empty")

    except Exception:
        return "", "pdf:ocr_error"

def extract_text_from_image(file_bytes: bytes) -> Tuple[str, str]:
    if not OCR_OK or Image is None or pytesseract is None:
        return "", "img:no_ocr"
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        text = (pytesseract.image_to_string(
            img,
            lang="kor",
            config="--oem 3 --psm 6"
        ) or "").strip()
        return (text, "img:ok") if text else ("", "img:empty")
    except Exception:
        return "", "img:error"


def extract_text_from_upload(name: str, mime: str, b: bytes) -> Tuple[str, str]:
    name_l = (name or "").lower()
    mime_l = (mime or "").lower()

    if mime_l == "application/pdf" or name_l.endswith(".pdf"):
        return extract_text_from_pdf(b)

    if mime_l.startswith("image/") or any(name_l.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
        return extract_text_from_image(b)

    if mime_l.startswith("text/") or name_l.endswith(".txt"):
        try:
            return b.decode("utf-8", errors="ignore").strip(), "text:ok"
        except Exception:
            return "", "text:error"

    return "", "none"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).strip()

def find_snippet(text: str, keyword: str, window: int = 40) -> str:
    """키워드 주변 원문 근거 1줄을 뽑아주는 간단 스니펫"""
    if not text or not keyword:
        return ""
    idx = text.find(keyword)
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return snippet

def find_nearest_article(text: str, pos: int) -> str:
    """
    text에서 pos(매칭 시작 인덱스) 기준으로,
    바로 '이전'에 등장한 '제N조'를 찾아 반환.
    없으면 "".
    """
    if not text or pos is None or pos < 0:
        return ""
    # pos 이전 구간에서 제N조를 모두 찾고, 마지막(가장 가까운 이전) 것을 사용
    prior = text[:pos]
    matches = list(re.finditer(r"제\s*(\d+)\s*조", prior))
    if not matches:
        return ""
    last = matches[-1]
    return f"제 {last.group(1)}조"

def extract_registry_key_lines(rt: str, max_lines: int = 6) -> List[Dict[str, str]]:
    """
    등기부 OCR 텍스트에서 '순위번호 N + 등기목적(근저당/가압류/압류/경매/신탁)' 라인 근처를 뽑아
    등기부 탭(t3)에서 리스트로 보여주기 위한 용도.
    """
    out = []
    if not rt:
        return out

    t = rt.replace("\r", "\n")
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    KEY = ("근저당", "가압류", "압류", "경매", "신탁", "채권최고액", "가처분")

    # 1) 순위번호로 시작하는 줄 우선
    for ln in lines:
        if len(out) >= max_lines:
            break
        if not re.match(r"^\d+(\-\d+)?\s+", ln):
            continue
        if any(k in ln for k in KEY):
            out.append({"line": ln[:180]})

    # 2) 위에서 거의 안 잡히면 키워드 포함 줄이라도 추출
    if not out:
        for ln in lines:
            if len(out) >= max_lines:
                break
            if any(k in ln for k in KEY):
                out.append({"line": ln[:180]})

    return out

def extract_clause_key_lines(ct: str, max_lines: int = 20) -> List[Dict[str, str]]:
    """
    계약서에서 '위험 특약'으로 볼 수 있는 문장만 발췌한다.
    - 정상 조항(목적/기간/일반 종료조항 등)은 제외
    - BAD_CLAUSE_PATTERNS(위험 패턴)에 실제로 매칭되는 문장만 출력
    - 발견된 문장은 전부 출력(접기 없음) / max_lines는 안전장치
    """
    out: List[Dict[str, str]] = []
    if not ct:
        return out

    text = ct.replace("\r", "\n")

    # OCR은 줄바꿈이 많아서 "줄" + "문장" 둘 다 사용
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    sentences = split_sentences_ko(text)

    # 핵심 사기 표현/애매 표현을 더 확실히 잡는 보조 패턴(추가)
    extra_risky_patterns = [
        r"확인\s*하에\s*처리",              # "부동산 확인 하에 처리"
        r"책임\s*지고\s*반환",              # "책임지고 반환"
        r"중개(한|한)\s*부동산",            # "중개한 부동산"
        r"보증금.*(부동산|중개).*반환",     # 보증금 + 부동산 + 반환 같은 조합
    ]

    # 최종 위험 패턴 목록 = 기존 BAD_CLAUSE_PATTERNS + extra
    risky_patterns = [p for (p, _label) in BAD_CLAUSE_PATTERNS] + extra_risky_patterns

    def _hit_any_pattern(s: str) -> bool:
        return any(re.search(p, s) for p in risky_patterns)

    # 1) 문장 단위에서 먼저 뽑기(가독성 좋음)
    picks = []
    for s in sentences:
        if _hit_any_pattern(s):
            picks.append(s.strip())

    # 2) 문장이 거의 안 잡히면 줄 단위로라도 뽑기(OCR 깨짐 대응)
    if not picks:
        for ln in lines:
            if _hit_any_pattern(ln):
                picks.append(ln.strip())

    # 3) 중복 제거 + 길이 제한
    seen = set()
    for s in picks:
        key = re.sub(r"\s+", " ", s).strip()
        if not key or key in seen:
            continue
        seen.add(key) 
        matched_label = ""
        for pat, label in BAD_CLAUSE_PATTERNS:
            if re.search(pat, key):
                matched_label = label
                break

        out.append({
            "line": key[:220],
            "label": matched_label
        })
        if len(out) >= max_lines:
            break

    return out

def find_id_like(text: str) -> List[str]:
    hits = set()
    if not text:
        return []
    for m in re.findall(r"\b\d{10,14}\b", text):
        hits.add(m)
    for m in re.findall(r"\b\d{3}-\d{2}-\d{5}\b", text):
        hits.add(m)
    return sorted(hits)

def _norm_name_for_broker(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", "", s)
    # 흔한 꼬리 단어 제거(너무 과하게 제거하지 않음)
    s = s.replace("공인중개사사무소", "").replace("부동산중개", "").replace("부동산", "")
    return s

def extract_broker_from_text(text: str):
    """
    계약서 OCR 텍스트에서 '등록번호'와 '상호'를 뽑음.
    시연용 PDF는 너가 '상호: OO부동산' 이런 포맷으로 넣어주면 성공률 99%임.
    """
    t = text or ""

    # 등록번호: 11710-2015-00012 같은 패턴
    reg = ""
    m = re.search(r"\b(\d{4,6}-\d{4}-\d{4,6})\b", t)
    if m:
        reg = m.group(1).strip()

    # 상호: "상호: OO부동산" 형태 우선
    name = ""
    m2 = re.search(r"(상호)\s*[:：]?\s*([^\n\r]{2,40})", t)
    if m2:
        name = m2.group(2).strip()

    return name, reg

def verify_broker_against_csv(contract_text: str, broker_df):
    """
    결과 status:
      - match: 등록번호가 CSV에 있고 상호도 대충 맞음
      - mismatch: 등록번호가 CSV에 없음 (가장 강한 신호)
      - need_check: 일부만 확인됨/상호가 애매함
      - unknown: 둘 다 추출 실패
    """
    name, reg = extract_broker_from_text(contract_text)
    reg_n = (reg or "").replace(" ", "")
    name_n = _norm_name_for_broker(name)

    if not reg_n and not name_n:
        return {"status": "unknown", "name": name, "reg": reg, "row": None}

    # 등록번호가 있으면 그걸 1순위로 검증
    if reg_n:
        hit = broker_df[broker_df["_reg"] == reg_n]
        if len(hit) == 0:
            return {"status": "mismatch", "name": name, "reg": reg, "row": None}

        row = hit.iloc[0].to_dict()
        # 상호도 있으면 '대충 맞는지'만 확인 (OCR 오타 고려)
        if name_n:
            csv_name_n = _norm_name_for_broker(row.get("상호", ""))
            if csv_name_n and (csv_name_n in name_n or name_n in csv_name_n):
                return {"status": "match", "name": name, "reg": reg, "row": row}
            # 등록번호는 존재하지만 상호가 다르면: OCR/표기 차이 가능 → need_check
            return {"status": "need_check", "name": name, "reg": reg, "row": row}

        # 등록번호만 맞으면 일단 match 처리(상호는 미추출)
        return {"status": "match", "name": name, "reg": reg, "row": row}

    # 등록번호 없고 상호만 있으면 후보가 너무 많아서 need_check
    return {"status": "need_check", "name": name, "reg": reg, "row": None}

KOR_NUM = {"영":0,"공":0,"일":1,"이":2,"삼":3,"사":4,"오":5,"육":6,"칠":7,"팔":8,"구":9}
KOR_UNIT = {"십":10,"백":100,"천":1000}
KOR_BIG = {"만":10000,"억":100000000}

def parse_korean_number(s: str) -> int:
    """
    '사십구' -> 49, '오백' -> 500, '사백오십일' -> 451 같은 한글수 파싱(만원 단위까지 시연용 충분)
    """
    if not s:
        return 0
    s = re.sub(r"[^가-힣]", "", s)

    total = 0
    cur = 0
    num = 0

    for ch in s:
        if ch in KOR_NUM:
            num = KOR_NUM[ch]
        elif ch in KOR_UNIT:
            unit = KOR_UNIT[ch]
            if num == 0:
                num = 1
            cur += num * unit
            num = 0
        elif ch in KOR_BIG:
            big = KOR_BIG[ch]
            cur += num
            if cur == 0:
                cur = 1
            total += cur * big
            cur = 0
            num = 0
        else:
            pass

    return total + cur + num

def parse_money_kor(text: str) -> int:
    """
    금액 파싱(강화):
    1) (₩5.000,000) / ₩5000000 / 5,000,000원
    2) '사십만원정' '오백만원정' 같은 한글금액(만원 단위)
    """
    if not text:
        return 0
    t = str(text).replace(" ", "").replace("\n", "")

    # 1) 숫자 기반 (원/₩/￦ + 점/콤마)
    m = re.search(r"(₩|￦)?([0-9][0-9,\.]*)\s*원?", t)
    if m:
        num = m.group(2).replace(",", "").replace(".", "")
        try:
            return int(num)
        except Exception:
            pass

    # 2) 한글 금액: '사십만원정' '사십구만원정'
    m2 = re.search(r"([가-힣]+)\s*만\s*원", t)
    if m2:
        n = parse_korean_number(m2.group(1))
        if n > 0:
            return n * 10000

    return 0

def auto_extract_manual_from_contract(contract_text: str) -> Dict[str, Any]:
    """
    업로드 모드에서도 계약서에서 '보증금/월세/임대인/주소' 정도는 자동으로 뽑아서
    analyze_risk에 넣어주기 위한 최소 추출기.
    OCR이 구려도 '숫자+원', '임대인/임차인' 같은 키워드는 비교적 잘 잡힘.
    """
    t = contract_text or ""
    out = {
        "address": "",
        "landlord_name": "",
        "owner_name": "",   # 업로드 계약서만으로는 보통 못 뽑음(등기부에서 채움)
        "deposit": 0,
        "rent": 0,
        "sale_price": 0,
        "contract_type": "미선택",
        "report_source": "upload",
    }

    # 계약유형 추정(개선): "□전세  V월세" 같은 체크표시를 우선으로 판단
    out["contract_type"] = "미선택"

    # 체크표시로 자주 나오는 문자들
    CHECK = r"[Vv✓✔√■●]"

    # 1) "V월세" / "월세V" 형태
    if re.search(CHECK + r"\s*월\s*세", t) or re.search(r"월\s*세\s*" + CHECK, t):
        out["contract_type"] = "월세"
    elif re.search(CHECK + r"\s*전\s*세", t) or re.search(r"전\s*세\s*" + CHECK, t):
        out["contract_type"] = "전세"
    else:
        # 2) 체크표시가 없으면 단서(차임=월세)로만 약하게 추정
        if "차임" in t or "월세" in t:
            out["contract_type"] = "월세"
        elif "전세" in t:
            out["contract_type"] = "전세"
    
    # ✅ 전세로 판단되면 월세/차임은 0으로 고정(오탐 방지)
    if out["contract_type"] == "전세":
        out["rent"] = 0
        
    # 보증금: '보 증 금 ... (₩5.000,000)' 형태 우선
    out["deposit"] = 0
    m = re.search(r"보\s*증\s*금[^\n]{0,40}\(\s*(₩|￦)\s*([0-9,\.]+)\s*\)", t)
    if m:
        out["deposit"] = parse_money_kor(m.group(2))
    else:
        # 보증금 주변에서 숫자+원/₩/￦ 탐색
        idx = t.find("보증금")
        if idx != -1:
            out["deposit"] = parse_money_kor(t[idx: idx + 200])

    # 월세/차임(정확): '차 임 금 사십만원정' 같은 한글금액을 우선 추출
    out["rent"] = 0

    # 1) '차임 금 ...만원정' (가장 신뢰)
    m = re.search(r"차\s*임\s*금\s*([가-힣]+)\s*만\s*원", t)
    if m:
        out["rent"] = parse_money_kor(m.group(1) + "만원")

    # 2) '월세 금 ...만원정' (대체)
    if out["rent"] == 0:
        m2 = re.search(r"월\s*세\s*금\s*([가-힣]+)\s*만\s*원", t)
        if m2:
            out["rent"] = parse_money_kor(m2.group(1) + "만원")

    # 3) (₩...) 형태가 있으면 그걸 사용
    if out["rent"] == 0:
        m3 = re.search(r"(차\s*임|월\s*세)[^\n]{0,40}\(\s*(₩|￦)\s*([0-9,\.]+)\s*\)", t)
        if m3:
            out["rent"] = parse_money_kor(m3.group(3))

    # ✅ 오탐 방지: 비정상적으로 작은 값이면 제거
    if 0 < out["rent"] < 10000:
        out["rent"] = 0

    # 임대인 이름(개선): '에게/으로/및/등' 같은 조사/불용어를 걸러내기
    # 임대인 이름(강화): '임대인(갑) 성명', '(갑) 성명', '갑: 홍길동' 대응
    out["landlord_name"] = ""

    # 1) '임대인 ... 성명: 홍길동'
    m = re.search(r"임\s*대\s*인[^\n]{0,20}성\s*명\s*[:：]?\s*([가-힣]{2,6})", t)
    if m:
        out["landlord_name"] = m.group(1).strip()

    # 2) '(갑) 성명: 홍길동' 또는 '(갑) 홍길동'
    if not out["landlord_name"]:
        m2 = re.search(r"\(\s*갑\s*\)[^\n]{0,20}(성\s*명\s*[:：]?\s*)?([가-힣]{2,6})", t)
        if m2:
            out["landlord_name"] = (m2.group(2) or "").strip()

    # 3) '갑: 홍길동'
    if not out["landlord_name"]:
        m3 = re.search(r"갑\s*[:：]\s*([가-힣]{2,6})", t)
        if m3:
            out["landlord_name"] = m3.group(1).strip()

    # 불용어 필터
    stop = {"에게", "으로", "로", "및", "등", "외", "대한", "부터", "까지", "제", "항"}
    cand = re.sub(r"(에게|으로|로)$", "", out["landlord_name"]).strip()
    if cand in stop:
        cand = ""
    if not (2 <= len(cand) <= 6):
        cand = ""
    out["landlord_name"] = cand
    
        # 임대인 이름(추가 강력 패턴): 2페이지 '임 대 인 ... 성 명 황미숙' 형태
    if not out["landlord_name"]:
        m = re.search(r"임\s*대\s*인.*?성\s*명\s*([가-힣]{2,6})", t, flags=re.DOTALL)
        if m:
            out["landlord_name"] = m.group(1).strip()

    # 주소(간단): '소재지'나 '주소' 뒤 라인 일부
    m = re.search(r"(소\s*재\s*지|주\s*소)\s*[:：]?\s*([^\n]{6,60})", t)
    if m:
        out["address"] = m.group(2).strip()

    return out

BAD_CLAUSE_PATTERNS = [
    (r"보증금\s*반환\s*책임\s*없", "보증금 반환 책임 없음"),
    (r"확정일자\s*불가|확정일자\s*받지\s*않", "확정일자 관련 제한"),
    (r"전입\s*신고\s*불가|전입\s*불가", "전입신고 제한"),
    (r"임차인\s*부담|수리\s*일체\s*임차인", "임차인 부담 과다"),
    (r"계약\s*해지\s*불가|중도\s*해지\s*불가", "중도해지 제한"),
    (r"원상복구\s*전부|도배\s*장판\s*임차인", "원상복구 과다 부담"),
    (r"임대인\s*동의\s*없\s*이\s*전대|전대\s*금지", "전대/전출 관련 제한"),
    (r"보증금\s*반환\s*지연|반환\s*기일", "보증금 반환 기한/지연 가능성"),
    (r"임차인\s*귀책\s*불문|불문\s*하고\s*임차인", "책임 전가(임차인 일방 부담)"),
    (r"계약금\s*반환\s*불가|계약금\s*포기", "계약금 반환 제한"),
    (r"위약금\s*(\d+|[가-힣]+)\s*배", "과도한 위약금 가능성"),
    (r"임대인\s*면책|책임\s*면제", "임대인 책임 면책 조항"),
    (r"보증금.*(부동산|중개).*(책임|확인).*반환", "보증금 반환 책임 주체가 불명확한 표현"),
    (r"(책임지고|확인\s*하에).*(반환|처리)", "보증금 반환을 보장하는 것처럼 보일 수 있는 애매한 표현"),
    (r"정당한\s*사유\s*없.*계약금\s*포기", "임차인의 계약 해제 제한(계약금 포기 강제)"),
    (r"임차인.*(계약금\s*포기|포기하고서만).*해제", "임차인의 계약 해제 제한(계약금 포기 강제)"),
]

REGISTRY_RISK_KEYWORDS = [
    ("근저당", "담보권(근저당)"),
    ("가압류", "가압류"),
    ("압류", "압류"),
    ("경매", "경매/강제집행"),
    ("신탁", "신탁등기"),
    ("채권최고액", "채권최고액"),
]

def auto_extract_owner_from_registry(registry_text: str) -> str:
        t = (registry_text or "").strip()
        if not t:
            return ""

        # 등기부에서 자주 등장하는 키워드 중심(시연용 실전)
        patterns = [
            r"등\s*기\s*명\s*의\s*인\s*[:：]?\s*([가-힣]{2,6})",
            r"소\s*유\s*자\s*[:：]?\s*([가-힣]{2,6})",
            r"성\s*명\s*[:：]?\s*([가-힣]{2,6})",
        ]
        for pat in patterns:
            m = re.search(pat, t)
            if m:
                return (m.group(1) or "").strip()
        return ""

def split_sentences_ko(text: str):
    if not text:
        return []
    # 줄바꿈 + 마침표 기준으로 단순 분리 (OCR 대응)
    raw = re.split(r"[.\n]", text)
    return [s.strip() for s in raw if len(s.strip()) >= 10]

def summarize_additional_checks(report: dict) -> str:
    """
    분석 리포트 기반으로 '추가로 확인하면 좋은 항목'을 요약한다.
    확정 판단/법적 결론 금지.
    """
    if not report:
        return ""

    # 리포트에서 필요한 정보만 추려서 컨텍스트 구성
    ctx = []
    for s in report.get("signals", []):
        ctx.append(f"- {s.get('title')}: {s.get('detail')}")

    ctx_text = "\n".join(ctx)[:1500]  # 토큰 폭주 방지

    prompt = f"""
너는 전월세 계약 사기 예방을 돕는 AI다.
아래는 한 계약에 대해 감지된 위험 신호 요약이다.

{ctx_text}

위 정보를 바탕으로,
사용자가 '추가로 확인하면 좋은 항목'을
5개 이내의 체크리스트로 정리해라.

조건:
- 법적 판단/단정 금지
- "확인 필요", "권장", "가능성" 표현만 사용
- 각 항목은 한 줄
- 실무적으로 바로 행동 가능한 내용 위주
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return "AI 요약 생성 중 오류가 발생했습니다."

def analyze_risk(contract_text: str, registry_text: str, manual: Dict[str, Any]) -> Dict[str, Any]:
    ct = contract_text or ""
    rt = registry_text or ""
    signals: List[Dict[str, Any]] = []
    score = 0
    is_upload_mode = (manual.get("report_source") == "upload")

    owner = manual.get("owner_name", "")
    landlord = manual.get("landlord_name", "")
    deposit = int(manual.get("deposit", 0) or 0)
    sale_price = int(manual.get("sale_price", 0) or 0)

    if owner and landlord and norm(owner) != norm(landlord):
        signals.append({
            "title": "소유자와 임대인이 다름",
            "severity": "high",
            "detail": "대리계약 가능성. 위임장/인감증명/신분증 사본 등 계약 권한 확인이 필요합니다.",
            "weight": 35
        })
        score += 35

    rt = registry_text or ""

    # =========================
    # 등기부: 말소(해지)된 근저당 오탐 방지
    # =========================
    cancelled_mortgage_ranks = set()

    # ✅ 말소/해지/해제 등 "권리 소멸" 표현을 최대한 넓게 잡기 (OCR 깨짐 대응)
    CANCEL_WORDS = r"(말\s*소|기\s*말\s*소|등\s*기\s*말\s*소|해\s*지|해\s*제|삭\s*제|취\s*소)"
    MORT_WORD = r"(근\s*저\s*당\s*권\s*설\s*정|근저당권설정|근\s*저\s*당|근저당)"

    # 1) "2번 근저당권설정등기말소" / "2번근저당권설정 말소" 등
    for m in re.finditer(rf"(\d+)\s*번\s*{MORT_WORD}.*?{CANCEL_WORDS}", rt):
        cancelled_mortgage_ranks.add(m.group(1))

    # 2) 줄바꿈/공백이 섞이는 경우까지 커버 (OCR 깨짐 대응)
    for m in re.finditer(rf"(\d+)\s*번[\s\S]{{0,80}}?{MORT_WORD}[\s\S]{{0,140}}?{CANCEL_WORDS}", rt):
        cancelled_mortgage_ranks.add(m.group(1))

    # 3) 근저당권변경 + 말소/해지 케이스
    for m in re.finditer(rf"(\d+)\s*번\s*(근\s*저\s*당\s*권\s*변\s*경|근저당권변경)[\s\S]{{0,140}}?{CANCEL_WORDS}", rt):
        cancelled_mortgage_ranks.add(m.group(1))

    # ✅ "2 근저당권설정" 같은 설정 항목에서 순위번호를 잡음 (표의 왼쪽 번호)
    mortgage_set_ranks = []
    for m in re.finditer(r"(^|\n)\s*(\d+)\s+근저당권설정", rt):
        mortgage_set_ranks.append(m.group(2))

    active_mortgage_ranks = [r for r in mortgage_set_ranks if r not in cancelled_mortgage_ranks]
    has_active_mortgage = len(active_mortgage_ranks) > 0

    for kw, label in REGISTRY_RISK_KEYWORDS:
        # ✅ 말소된 근저당만 있는 경우:
        # "근저당" / "채권최고액"은 위험 신호로 올리지 않음(오탐 방지)
        if kw in ["근저당", "채권최고액"]:
            if not has_active_mortgage:
                continue

        if kw in rt:
            sev = "high" if kw in ["압류", "가압류", "경매"] else "mid"
            w = 28 if sev == "high" else 16

            # ✅ 근저당은 중복(근저당 + 채권최고액)으로 2번 뜨는 걸 줄이기:
            # '근저당'만 대표로 남기고 '채권최고액'은 스킵
            if kw == "채권최고액" and ("근저당" in rt):
                continue

            # 근저당은 활성 순위번호를 같이 보여주면 설명/방어가 훨씬 좋아짐
            if kw == "근저당":
                ranks_txt = ", ".join(active_mortgage_ranks[:5])
                detail = (
                    f"등기부(을구) 순위번호 {ranks_txt}번 항목에서 '근저당권설정' 기록이 확인됩니다. "
                    f"각 항목에서 채권최고액(얼마까지 빚을 보장하는지)과 말소(해지) 여부를 원문으로 확인하세요."
                )
                evidence = find_snippet(rt, "근저당권설정") or find_snippet(rt, "근저당")
            else:
                detail = f"등기부에서 '{kw}' 단서가 감지되었습니다. 원문에서 금액/순위/말소 여부를 확인하세요."
                evidence = find_snippet(rt, kw)

            signals.append({
                "title": f"등기부 위험 신호: {label}",
                "severity": sev,
                "detail": detail,
                "evidence": evidence,
                "weight": w,
            })
            score += w

    # (선택) 말소 근거가 잡힌 경우, 위험 대신 참고 안내를 하나 넣고 싶으면:
    # - 기본 화면에서는 접기/숨김 권장(노이즈 줄이기)
    if (not has_active_mortgage) and cancelled_mortgage_ranks:
        signals.append({
            "title": "등기부 참고: 말소(해지)된 근저당 표시 가능",
            "severity": "low",
            "detail": "근저당 관련 문구가 보이지만, 말소/해지 문구도 함께 감지되었습니다. 원문에서 취소선/말소 표시를 확인하세요.",
            "evidence": find_snippet(rt, "말소") or find_snippet(rt, "해지"),
            "weight": 0
        })

    has_clause_word = ("특약" in (contract_text or ""))
    has_clause_signal = any(
        ("특약" in s.get("title", "") or "특약" in s.get("detail", ""))
        for s in signals
    )

    # ⚠️ 특약은 있는데, 위험 판단을 못 한 경우 → 최소 '주의'
    clause_uncertain = has_clause_word and not has_clause_signal

    ct = contract_text or ""
    sentences = split_sentences_ko(ct)  # ✅ 문장 리스트(없으면 빈 리스트)

    clause_hits = []  # [{"label":..., "evidence":...}, ...]

    for pat, label in BAD_CLAUSE_PATTERNS:
        m = re.search(pat, ct)
        if not m:
            continue

        # ✅ 조항 번호는 '스니펫'이 아니라 '원문(ct) + 매칭 위치'로 역추적
        article = find_nearest_article(ct, m.start())

        clause_hits.append({
            "label": label,
            "article": article,   # 조항은 따로 저장
        })

    # ✅ 여러 개여도 1개 signal만 추가
    if clause_hits:
        # 근거는 최대 3개만 노출(너무 길어지는 거 방지)
        ev_lines = []
        for h in clause_hits[:3]:
            art = (h.get("article") or "").strip()
            lab = (h.get("label") or "").strip()
            if art:
                ev_lines.append(f"- {art} : {lab}")
            else:
                ev_lines.append(f"- {lab}")

        signals.append({
            "title": "계약서 특약 주의",
            "severity": "mid",
            "detail": (
                "특약 문구 중 일부가 보증금 반환/권리 행사에 불리하게 해석될 수 있어요. "
                "누가(임대인)·언제·어떤 조건으로 반환하는지, 기한/조건을 원문에 명확히 적는 것을 권장해요."
            ),
            "evidence": "\n".join(ev_lines),
            "weight": 14
        })
        score += 14

    # =========================
    # 중개업소 등록번호 교차확인(공공데이터 CSV 기반)
    # =========================
    broker_info = None

    try:
        v = verify_broker_against_csv(ct, BROKER_DF)

        if v["status"] == "mismatch":
            signals.append({
                "title": "중개업소 등록번호 교차확인 불일치",
                "severity": "mid",
                "detail": "계약서에서 추출된 등록번호가 공공데이터 목록과 일치하지 않습니다. OCR 인식/기재 오류 가능성이 있어 공식 조회로 재확인을 권장합니다.",
                "evidence": f"추출 등록번호: {v.get('reg','')}" if v.get("reg") else "",
                "weight": 10
            })
            score += 10

        elif v["status"] == "match":
            broker_info = {
                "title": "중개업소 등록정보 확인 완료",
                "detail": "공공데이터 기준 중개업소 등록번호가 일치합니다.",
                "evidence": f"등록번호: {v.get('reg','')}",
            }

        elif v["status"] == "need_check":
            signals.append({
                "title": "중개업소 등록정보 추가 확인 필요",
                "severity": "low",
                "detail": "상호/등록번호가 일부만 확인되거나 상호가 정확히 일치하지 않을 수 있습니다. 계약서 원문과 공공데이터를 함께 확인하는 것을 권장합니다.",
                "evidence": f"추출 상호: {v.get('name','')}, 등록번호: {v.get('reg','')}".strip(),
                "weight": 3
            })
            score += 3

        # match/unknown은 굳이 signals에 안 넣어도 됨(노이즈 줄이기)
    except Exception:
        # CSV 로드 실패/예외가 나도 전체 분석이 죽지 않게
        pass

    ratio = None
    if sale_price > 0 and deposit > 0:
        ratio = deposit / sale_price
        if ratio >= 0.9:
            signals.append({
                "title": "보증금 대비 시세 여유 부족",
                "severity": "high",
                "detail": f"보증금/시세 ≈ {ratio*100:.1f}%. 선순위 권리/채권최고액 확인이 특히 중요합니다.",
                "weight": 30
            })
            score += 30
        elif ratio >= 0.8:
            signals.append({
                "title": "보증금 대비 시세 여유 적음",
                "severity": "mid",
                "detail": f"보증금/시세 ≈ {ratio*100:.1f}%. 근저당·압류 같은 권리가 있으면 보증금 회수에 영향을 받을 수 있어요.",
                "weight": 18
            })
            score += 18
    else:
        if (not is_upload_mode) and deposit > 0:
            score += 8
            signals.append({
                "title": "시세 정보 없음",
                "severity": "mid",
                "detail": "보증금 대비 안전여유 판단을 위해 시세(실거래/매매가) 확인을 권장합니다.",
                "weight": 8
            })

    ids = find_id_like((contract_text or "") + "\n" + (registry_text or ""))[:10]
    score = max(0, min(100, score))
    has_high = any(s.get("severity") == "high" for s in signals)
    has_mid = any(s.get("severity") == "mid" for s in signals)

    if has_high:
        status_label = "위험"
        chip = "high"
    elif has_mid:
        status_label = "주의"
        chip = "mid"
    else:
        status_label = "안전"
        chip = "low"

    level = status_label

    return {
        "score": score,
        "level": level,
        "chip": chip,
        "signals": signals,
        "ids": ids,
        "ratio": ratio,
        "manual": manual,
        "missing_registry": (not (registry_text or "").strip()),
        "preview": {"contract": (contract_text or "")[:900], "registry": (registry_text or "")[:900]},
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status_label": status_label,
        "broker_info": broker_info,
    }


def get_client():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or not OPENAI_OK:
        return None
    return OpenAI(api_key=key)


def chat_answer(report: Dict[str, Any], history: List[Dict[str, str]], user_msg: str) -> str:
    client = get_client()
    if not client:
        return "챗봇을 쓰려면 OPENAI_API_KEY(환경변수)와 openai 패키지가 필요합니다."

    ctx = {
        "score": report.get("score"),
        "level": report.get("level"),
        "signals": report.get("signals"),
        "manual": report.get("manual"),
        "ids": report.get("ids"),
        "ratio": report.get("ratio"),
    }

    messages = [
        {"role": "system", "content": f"""
너는 전월세 사기 예방 상담 챗봇이야.
- 확정 판단 금지(가능성/확인 필요)
- 사용자가 지금 바로 할 행동을 체크리스트로
- 법률 자문 아님(일반 정보)
[컨텍스트]{ctx}
"""}
    ]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_msg})

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.4,
    )
    return res.choices[0].message.content.strip()


def manual_step_form() -> Dict[str, Any]:
    if "manual_form" not in st.session_state:
        st.session_state.manual_form = {
            "contract_type": "월세",
            "deposit_manwon": 0,
            "rent_manwon": 0,
            "address": "",
            "owner_name": "",
            "landlord_name": "",
            "sale_price_manwon": 0,
        }
    f = st.session_state.manual_form

    if "manual_deposit_input" not in st.session_state:
        st.session_state.manual_deposit_input = int(f.get("deposit_manwon", 0))
    if "manual_rent_input" not in st.session_state:
        st.session_state.manual_rent_input = int(f.get("rent_manwon", 0))
    if "manual_sale_price" not in st.session_state:
        st.session_state.manual_sale_price = int(f.get("sale_price_manwon", 0))

    st.markdown("<div class='box'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:1.2rem; font-weight:950; letter-spacing:-0.6px;'>보증금·월세 정보를 입력해 주세요</div>", unsafe_allow_html=True)
    st.markdown("<div class='muted' style='margin-top:6px;'>업로드 없이도 이 기능만 단독으로 사용할 수 있어요. 입력값은 저장되지 않아요.</div>", unsafe_allow_html=True)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    if "manual_contract_type_radio" not in st.session_state:
        st.session_state.manual_contract_type_radio = f.get("contract_type", "월세")

    f["contract_type"] = st.radio(
        "계약 유형",
        ["전세", "월세"],
        horizontal=True,
        key="manual_contract_type_radio",
    )

    # dict에도 동기화
    st.session_state.manual_form["contract_type"] = f["contract_type"]

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    # ===== 계약 유형별 입력 UI =====
    st.markdown("<div class='sectionTitle' style='margin-top:6px;'>보증금</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([4, 1])
    with c1:
        st.number_input(
            "보증금 금액 입력",
            min_value=0,
            step=10,
            label_visibility="collapsed",
            key="manual_deposit_input"
        )
    with c2:
        st.markdown(
            "<div style='height: 42px; display:flex; align-items:center; color:#6B7280;'>만원</div>",
            unsafe_allow_html=True
        )

    # 월세: 월세일 때만
    if f["contract_type"] == "월세":
        st.markdown("<div class='sectionTitle' style='margin-top:6px;'>월세</div>", unsafe_allow_html=True)
        c1, c2 = st.columns([4, 1])
        with c1:
            st.number_input(
                "월세 금액 입력",
                min_value=0,
                step=1,
                label_visibility="collapsed",
                key="manual_rent_input"
            )
        with c2:
            st.markdown(
                "<div style='height: 42px; display:flex; align-items:center; color:#6B7280;'>만원</div>",
                unsafe_allow_html=True
            )
    else:
        f["rent_manwon"] = 0

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sectionTitle'>추가 정보(선택)</div>", unsafe_allow_html=True)

    f["address"] = st.text_input("집 주소", value=f["address"], placeholder="예) 경남 진주시 ...", key="manual_address")
    cA, cB = st.columns(2)
    with cA:
        f["landlord_name"] = st.text_input("임대인 이름(계약서 기준)", value=f["landlord_name"], key="manual_landlord_name")
    with cB:
        f["owner_name"] = st.text_input("소유자 이름(등기부 기준)", value=f["owner_name"], key="manual_owner_name")

    st.number_input(
        label="매매가(대략, 알면 정확도↑) (만원)",
        min_value=0,
        step=100,
        key="manual_sale_price"
    )

    f["deposit_manwon"] = int(st.session_state.manual_deposit_input)
    f["rent_manwon"] = int(st.session_state.manual_rent_input)
    f["sale_price_manwon"] = int(st.session_state.manual_sale_price)
    st.markdown("</div>", unsafe_allow_html=True)
    return f

def render_signal_card(title: str, detail: str, evidence: str = ""):
    evidence = (evidence or "").strip()
    # ✅ 줄바꿈 보이게
    evidence_html = evidence.replace("\n", "<br>")

    ev_html = f"<div class='signal-meta'><b>근거:</b><br>{evidence_html}</div>" if evidence_html else ""

    st.markdown(
        f"""
        <div class="signal">
            <div class="signal-title">{title}</div>
            <div class="signal-detail">{detail}</div>
            {ev_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def build_top3_actions_from_report(report: Dict[str, Any]) -> List[str]:
    """리포트(signals/ratio) 기반으로 시연용 TOP3 행동을 고정 생성"""
    if not report:
        return []

    signals = report.get("signals", []) or []
    ratio = report.get("ratio", None)

    actions = []

    if any("등기부" in (s.get("title", "") or "") for s in signals):
        actions.append("등기부등본에서 근저당/압류/신탁 여부를 확인하세요.")
    if any("특약" in (s.get("title", "") or "") for s in signals):
        actions.append("계약서 특약 중 불리한 문구가 있는지 원문으로 확인하고 수정 협의를 권장해요.")
    if (ratio is not None) and (ratio >= 0.8):
        actions.append("보증금 대비 시세 여유가 적어 선순위 권리(채권최고액) 확인이 특히 필요해요.")

    base_actions = [
        "등기부등본에서 근저당/압류/신탁 여부를 확인하세요.",
        "계약서 특약에서 전입신고/확정일자 제한 문구가 없는지 확인하세요.",
        "계약 당일: 신분증·소유자 일치·대리계약 서류(위임장/인감) 여부를 확인하세요.",
    ]

    for a in base_actions:
        if len(actions) >= 3:
            break
        if a not in actions:
            actions.append(a)

    return actions[:3]

def render_report_like_app(report: Dict[str, Any]):
    if not report or not isinstance(report, dict):
        st.info("아직 리포트가 없어요. 상단에서 파일 업로드 후 ‘분석하기’를 눌러주세요.")
        return
    manual = report.get("manual", {})
    deposit = int(manual.get("deposit", 0))
    sale_price = int(manual.get("sale_price", 0))
    ratio = report.get("ratio", None)
    signals = report.get("signals", [])
    score = int(report.get("score", 0))  # 내부 판단용 유지
    level = report.get("level", "낮음")
    chip = report.get("chip", "low")
    missing_registry = report.get("missing_registry", False)
    contract_missing = not (report.get("preview", {}).get("contract", "").strip())
    registry_missing = missing_registry

    high_hit = any(s.get("severity") == "high" for s in signals)
    risky = (score >= 50) or (ratio is not None and ratio >= 0.8) or high_hit

    report_source = (report.get("manual", {}) or {}).get("report_source") or st.session_state.get("report_source", "upload")

    if report_source == "manual":
        (t4,) = st.tabs(["입력값 기준"])
    else:
        t1, t2, t3 = st.tabs(["분석 결과", "계약서(특약)", "등기부(권리관계)"])

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    if "report_ai" not in st.session_state:
        st.session_state.report_ai = None

    if report_source != "manual":
        with t1:
            st.markdown("<div class='resultCard'>", unsafe_allow_html=True)

            # ✅ 점수 뱃지 제거: 등급만 노출
            st.markdown(
                f"<div class='badges'>"
                f"<span class='chip {chip}'>등급: {level}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.write("")

            # ✅ 상태 기반 상단 문구(안전/주의/위험)
            status_label = report.get("level", "주의")  # 지금 너는 level에 안전/주의/위험 넣어둔 상태
            # 위험 신호/정보부족 기반으로 문구를 더 자연스럽게
            has_high = any(s.get("severity") == "high" for s in signals)
            has_mid = any(s.get("severity") == "mid" for s in signals)

            if has_high:
                headline = "보증금 회수에 영향 줄 수 있는 신호가 있어요."
                subline = "계약 진행 전 등기부/특약을 원문으로 확인하고, 필요하면 전문가 상담을 권장합니다."
            elif has_mid:
                headline = "확인이 필요한 항목이 있어요."
                subline = "특약 문구와 핵심 조건을 원문으로 확인하고, 필요하면 수정 협의를 권장합니다."
            else:
                headline = "현재 업로드된 문서 기준으로는 큰 위험 신호가 없어요."
                subline = "그래도 계약 전 최종 확인(특약/전입·확정일자)은 꼭 필요해요."
            st.markdown(
                f"<div class='warnTitle'>보증금 및 시세 확인 결과, <span class='warnRed'>{headline}</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='warnSub'>• {subline}</div>",
                unsafe_allow_html=True,
            )
            
            # ✅ 추출/근거가 눈에 보이도록: "계약서에서 잡힌 핵심" + "특약 감지" 한 줄 요약
            manual = report.get("manual", {}) or {}
            extracted_bits = []

            addr = (manual.get("address") or "").strip()
            if addr:
                extracted_bits.append(f"주소 {addr}")

            if manual.get("deposit", 0) > 0:
                extracted_bits.append(f"보증금 {int(manual['deposit']):,}원")

            if manual.get("rent", 0) > 0:
                extracted_bits.append(f"월세 {int(manual['rent']):,}원")

            if (manual.get("landlord_name") or "").strip():
                extracted_bits.append(f"임대인 '{manual.get('landlord_name')}'")

            # 특약 패턴 감지 요약(중복 안내 X, 한 줄만)
            has_clause = any(("특약" in (s.get("title",""))) for s in signals)

            # 특약 스니펫
            ct_full = st.session_state.get("upload_texts", {}).get("contract", "") or ""
            clause_snip = ""
            if "특약" in ct_full:
                clause_snip = find_snippet(ct_full, "특약", window=45)

            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
            st.markdown("<div class='sectionTitle'>이번 분석에서 문서에서 확인된 내용</div>", unsafe_allow_html=True)

            # 1) 핵심값 추출 표시
            if extracted_bits:
                st.markdown(
                    "<div class='badge'>문서에서 자동 추출됨</div>",
                    unsafe_allow_html=True
                )
                st.write(" · ".join(extracted_bits))
            else:
                st.caption("문서에서 핵심 금액/이름을 뚜렷하게 추출하지 못했어요. 아래 원문 확인을 권장해요.")

            # 2) 특약 감지 요약
            if has_clause:
                st.caption("특약 문구에서 확인이 필요한 패턴이 감지됐어요. 아래 ‘감지된 위험 신호’에서 근거를 확인하세요.")

            # 3) 특약 스니펫 보여주기
            if clause_snip:
                # ✅ 특약 근거는 '위험 패턴 감지'가 있을 때만 보여주기 (전문성↑, 노이즈↓)
                clause_signals = [
                    s for s in signals
                    if ("특약" in (s.get("title", "")) or "특약" in (s.get("detail", "")))
                ]

                if clause_signals:
                    # 근거 스니펫: 계약서 전체에서 특약 키워드 또는 패턴 근처를 1줄만
                    ct_full = st.session_state.get("upload_texts", {}).get("contract", "") or ""
                    ev = ""
                    # evidence가 있으면 그걸 쓰고, 없으면 특약 근처 스니펫
                    for cs in clause_signals:
                        if (cs.get("evidence") or "").strip():
                            ev = cs.get("evidence").strip()
                            break

                    if not ev and "특약" in ct_full:
                        ev = find_snippet(ct_full, "특약", window=60)

                    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
                    st.markdown("<div class='sectionTitle'>특약에서 확인이 필요한 문구</div>", unsafe_allow_html=True)

                    # 위험 패턴 요약(최대 2개)
                    for cs in clause_signals[:2]:
                        st.markdown(
                            f"<div class='signal-meta'>• {cs.get('detail','').strip()}</div>",
                            unsafe_allow_html=True
                        )

                    # 근거 원문(짧게)
                    if ev:
                        st.markdown(
                            f"<div class='signal-meta'><b>근거(원문 일부):</b> {ev}</div>",
                            unsafe_allow_html=True
                        )
                else:
                    # 위험 패턴이 없으면 특약 원문은 숨김
                    pass

            st.write("")
            if sale_price > 0 and deposit > 0:
                pct = min(100, int((deposit / sale_price) * 100))
                st.markdown("<div class='badge'>시세(입력 기반)</div>", unsafe_allow_html=True)
                st.write(f"{sale_price:,.0f} 원")
                st.write("")
                st.markdown(f"<div class='barWrap'><div class='barFill' style='width:{pct}%'></div></div>", unsafe_allow_html=True)
                st.markdown("<div class='barLabels'><span>0%~60%</span><span>60%~70%</span><span>70%~</span></div>", unsafe_allow_html=True)
            else:
                if report.get("manual", {}).get("report_source") == "manual":
                    st.info("시세(매매가)를 입력하면 ‘보증금 vs 시세’ 결과를 더 정확히 보여줄 수 있어요.")

            st.markdown("</div>", unsafe_allow_html=True)

            contract_missing = not (report.get("preview", {}).get("contract", "").strip())
            st.write("")
            st.markdown("<div class='sectionTitle'>감지된 위험 신호</div>", unsafe_allow_html=True)
            if not signals:
                if missing_registry:
                    st.info("등기부등본을 함께 올리면 담보·압류·신탁 같은 권리관계까지 더 정확히 확인할 수 있어요.")
                elif contract_missing:
                    st.info("계약서를 함께 올리면 특약, 전입신고, 확정일자 제한 여부까지 더 정확히 확인할 수 있어요.")
                else:
                    st.success("감지된 위험 신호가 없습니다. 그래도 계약 전 최종 확인은 권장해요.")
            else:
                for s in signals:
                    title = s.get("title", "위험 신호")
                    detail = s.get("detail", "")
                    sev = s.get("severity", "mid")

                    # 지금 할 일(간단 규칙 기반)
                    action = "관련 서류/원문을 확인하세요."
                    if "등기부" in title or any(k in detail for k in ["근저당", "압류", "가압류", "경매", "신탁", "채권최고액"]):
                        action = "등기부등본에서 순위/금액/말소 여부를 확인하세요."
                    elif "특약" in title or "특약" in detail:
                        action = "해당 특약 문구를 원문에서 찾아 수정/삭제를 협의하세요."
                    elif "소유자" in title or "임대인" in title or "대리" in detail:
                        action = "위임장·인감증명·신분증 사본 등 계약 권한을 확인하세요."
                    elif "시세" in title or "보증금/시세" in detail:
                        action = "실거래/매매가를 확인하고 선순위 권리(채권최고액)를 점검하세요."

                    render_signal_card(
                        title=title,
                        detail=detail,
                        evidence=s.get("evidence", "")
                    )

        with t2:
            contract_text = (st.session_state.get("upload_texts", {}) or {}).get("contract", "").strip()

            st.markdown("<div class='resultCard'>", unsafe_allow_html=True)

            st.markdown("<div class='sectionTitle'>계약서 특약 분석</div>", unsafe_allow_html=True)

            # CASE A: 계약서 미업로드 → 안내만, 분석결과 섹션 절대 출력 금지
            if not contract_text:
                st.markdown("""
                <div class="muted" style="margin-top:6px;">
                    계약서가 업로드되지 않았어요.
                </div>

                <div class="hr"></div>

                <div>
                    계약 전에는<br>
                    특약·전입신고·확정일자 제한 같은<br>
                    계약 조건을 확인하는 것이 중요해요.
                </div>

                <div style="margin-top:10px;">
                    계약서를 업로드하면<br>
                    특약 분석 결과를 바로 확인할 수 있어요.
                </div>
                """, unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)  # resultCard 닫기

            # CASE B: 계약서 업로드됨 → 그때만 분석 결과 출력
            else:
                clause_signals = [
                    s for s in (signals or [])
                    if "특약" in (s.get("title", "") or "") or "특약" in (s.get("detail", "") or "")
                ]

                st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

                if not clause_signals:
                    st.markdown("""
                    <div class="sectionTitle">특약 분석 결과</div>
                    <div class="muted" style="margin-top:6px;">
                        현재 업로드된 계약서 기준으로,<br>
                        확인이 필요한 특약 문구는 감지되지 않았어요.
                    </div>

                    <div class="hr"></div>

                    <div style="font-weight:800; margin-bottom:4px;">
                        그래도 계약 전에는 아래 항목을 원문으로 한 번 더 확인해 주세요.
                    </div>
                    <ul style="margin-top:6px;">
                        <li>전입신고 제한 문구</li>
                        <li>확정일자 관련 제한 여부</li>
                    </ul>
                    """, unsafe_allow_html=True)

                else:
                    st.markdown("""
                    <div class="sectionTitle">특약에서 확인이 필요한 항목</div>
                    <div class="muted" style="margin-top:6px;">
                        일부 특약 문구가 보증금 보호나 권리 행사에 영향을 줄 수 있어요.<br>
                        아래 문구를 원문 기준으로 확인해 보세요.
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

                    # 특약 핵심 문장 발췌 TOP3 (분석결과와 중복 방지)
                    key_lines = extract_clause_key_lines(contract_text, max_lines=20)

                    st.markdown("""
                    <div class="sectionTitle">특약에서 발췌한 핵심 문장</div>
                    <div class="muted" style="margin-top:6px;">
                    아래 문장은 OCR로 발췌된 '원문 일부'예요. 계약서 PDF 원문에서 동일 문장을 찾아 확인해 보세요.
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

                    if not key_lines:
                        st.info("특약/핵심 문장을 충분히 발췌하지 못했어요. (스캔 품질 또는 OCR 결과 영향)")
                    else:
                        for i, it in enumerate(key_lines, 1):
                            st.markdown(
                                f"""
                                <div class="signal">
                                    <div class="signal-title">핵심 {i}</div>
                                    <div class="signal-detail">{it.get("line","")}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    st.markdown("<div class='sectionTitle' style='margin-top:12px;'>이 부분에서 특히 확인할 점</div>", unsafe_allow_html=True)
                    st.write("• 보증금 반환 주체가 ‘임대인’으로 명확히 적혀 있는지")
                    st.write("• ‘확인 하에 처리’, ‘책임지고’처럼 기한/조건이 빠진 문구가 없는지")
                    
        with t3:
            st.markdown("<div class='resultCard'>", unsafe_allow_html=True)

            registry_text = (st.session_state.get("upload_texts", {}) or {}).get("registry", "").strip()

            # 등기부 관련 signal만 필터
            registry_signals = [
                s for s in signals
                if s.get("title", "").startswith("등기부 위험 신호")
            ]

            # -----------------------
            # CASE A: 등기부 미업로드
            # -----------------------
            if not registry_text:
                st.markdown("""
                <div class="sectionTitle">등기부 권리관계 분석</div>
                <div class="muted" style="margin-top:6px;">
                    등기부등본이 업로드되지 않았어요.
                </div>

                <div class="hr"></div>

                <div>
                    계약 전에는<br>
                    해당 주택에 근저당·압류·신탁 같은<br>
                    권리관계가 없는지 확인하는 것이 중요해요.
                </div>

                <div style="margin-top:10px;">
                    등기부등본을 업로드하면<br>
                    권리관계 분석 결과를 바로 확인할 수 있어요.
                </div>
                """, unsafe_allow_html=True)

            # -----------------------
            # CASE B: 등기부 업로드 + 위험 없음
            # -----------------------
            elif not registry_signals:
                st.markdown("""
                <div class="sectionTitle">등기부 권리관계 분석 결과</div>
                <div class="muted" style="margin-top:6px;">
                    현재 업로드된 등기부 기준으로,<br>
                    큰 위험 신호는 감지되지 않았어요.
                </div>

                <div class="hr"></div>

                <div style="font-weight:800; margin-bottom:4px;">
                    그래도 계약 전에는 아래 항목을 원문으로 한 번 더 확인해 주세요.
                </div>
                <ul style="margin-top:6px;">
                    <li>선순위 근저당 금액</li>
                    <li>말소 여부</li>
                </ul>
                """, unsafe_allow_html=True)

            # -----------------------
            # CASE C: 등기부 업로드 + 위험 있음
            # -----------------------
            else:
                st.markdown("""
                <div class="sectionTitle">등기부에서 확인이 필요한 권리관계</div>
                <div class="muted" style="margin-top:6px;">
                    일부 권리관계가 보증금 회수에 영향을 줄 수 있어요.<br>
                    아래 항목을 등기부 원문 기준으로 확인해 보세요.
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

                # 등기부 탭 전용: 원문 핵심 라인 + 읽는 법 안내
                rt_full = registry_text or ""
                key_lines = extract_registry_key_lines(rt_full, max_lines=8)

                st.markdown("<div class='sectionTitle'>핵심 요약</div>", unsafe_allow_html=True)
                st.write("등기부(을구)에 근저당 등 권리관계가 있어 보증금 회수에 영향을 줄 수 있어요.")

                st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
                st.markdown("<div class='sectionTitle'>등기부에서 뽑힌 핵심 문장</div>", unsafe_allow_html=True)

                top_lines = key_lines[:2]
                more_lines = key_lines[2:]

                # 기본 노출: TOP 2
                for i, item in enumerate(top_lines, 1):
                    st.markdown(
                        f"""
                        <div class="signal">
                            <div class="signal-title">핵심 {i}</div>
                            <div class="signal-detail">{item['line']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # 나머지는 접기
                if more_lines:
                    with st.expander("핵심 문장 더 보기"):
                        for i, item in enumerate(more_lines, len(top_lines) + 1):
                            st.markdown(
                                f"""
                                <div class="signal">
                                    <div class="signal-title">핵심 {i}</div>
                                    <div class="signal-detail">{item['line']}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                else:
                    st.caption("핵심 문장을 자동으로 뽑지 못했어요. 등기부 원문에서 ‘근저당/압류/신탁/채권최고액’ 키워드를 직접 확인하세요.")

                st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
                st.markdown("<div class='sectionTitle'>이 부분에서 특히 조심할 점</div>", unsafe_allow_html=True)

                main_checks = [
                    "같은 순위번호에 말소/해지(등기말소) 문구가 있는지",
                    "근저당이 있으면 채권최고액이 보증금보다 큰지",
                ]

                extra_checks = [
                    "압류/가압류/경매 문구가 있으면 진행 여부/해제 여부",
                    "신탁 문구가 있으면 임대 권한이 누구에게 있는지",
                ]

                # 기본 노출
                for c in main_checks:
                    st.write(f"• {c}")

            st.markdown("</div>", unsafe_allow_html=True)

    if report_source == "manual":
        with t4:
            manual = report.get("manual", {}) or {}
            level = report.get("level", "주의")
            chip = report.get("chip", "mid")
            signals = report.get("signals", []) or []

            deposit = int(manual.get("deposit", 0) or 0)
            rent = int(manual.get("rent", 0) or 0)
            sale_price = int(manual.get("sale_price", 0) or 0)

            # 1) 헤드라인(수동 전용)
            has_high = any(s.get("severity") == "high" for s in signals)
            has_mid = any(s.get("severity") == "mid" for s in signals)

            if has_high:
                headline = "입력하신 조건 기준으로, 보증금 회수에 영향 줄 수 있는 신호가 있어요."
                subline = "계약 진행 전 등기부/특약을 원문으로 확인하는 것을 권장해요."
            elif has_mid:
                headline = "입력하신 정보만으로는 추가 확인이 필요한 항목이 있어요."
                subline = "가능하면 계약서·등기부를 확보해서 원문 기반으로 다시 확인해 보세요."
            else:
                headline = "입력하신 정보 기준으로는 큰 위험 신호가 없어요."
                subline = "그래도 계약 전 등기부·특약 최종 확인은 권장돼요."

            st.markdown(
                f"<div class='badges'><span class='chip {chip}'>등급: {level}</span></div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                f"<div class='warnTitle'><span class='warnRed'>{headline}</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='warnSub'>• {subline}</div>",
                unsafe_allow_html=True,
            )

            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

            # 2) 입력값 요약 (수동 전용)
            st.markdown("<div class='sectionTitle'>입력한 정보 요약</div>", unsafe_allow_html=True)

            summary = []
            ct = (manual.get("contract_type") or "").strip()
            if ct:
                summary.append(f"유형: {ct}")
            if deposit > 0:
                summary.append(f"보증금: {deposit:,}원")
            if rent > 0:
                summary.append(f"월세: {rent:,}원")
            if sale_price > 0:
                summary.append(f"매매가(대략): {sale_price:,}원")
            if (manual.get("address") or "").strip():
                summary.append(f"주소: {manual.get('address')}")
            if (manual.get("landlord_name") or "").strip():
                summary.append(f"임대인: {manual.get('landlord_name')}")
            if (manual.get("owner_name") or "").strip():
                summary.append(f"소유자: {manual.get('owner_name')}")

            if summary:
                st.write(" · ".join(summary))
            else:
                st.caption("입력된 정보가 많지 않아 요약이 제한적이에요.")

            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

            # 3) 지금 할 일 TOP 3 (수동 전용)
            st.markdown("<div class='sectionTitle'>👉 지금 할 일 TOP 3</div>", unsafe_allow_html=True)

            actions = []
            if sale_price == 0 and deposit > 0:
                actions.append("비슷한 매물 ‘매매가(대략)’를 확인해 보증금 안전여유를 점검하세요.")
            if not (manual.get("owner_name") or "").strip():
                actions.append("등기부등본에서 소유자(명의자)와 권리관계(근저당/압류/신탁)를 확인하세요.")
            actions.append("계약서 특약에서 전입신고/확정일자 제한 문구가 없는지 원문으로 확인하세요.")

            # 3개로 고정
            actions = actions[:3]
            while len(actions) < 3:
                actions.append("가능하면 계약서·등기부를 업로드해 원문 기반으로 다시 분석해 보세요.")

            for i, a in enumerate(actions, 1):
                st.write(f"{i}. {a}")

            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

            # 4) 감지된 위험 신호(수동에서도 보여주되, 문서/원문 멘트는 제거)
            st.markdown("<div class='sectionTitle'>감지된 위험 신호</div>", unsafe_allow_html=True)

            if not signals:
                st.success("입력 정보 기준으로 감지된 위험 신호가 없습니다.")
                st.caption("정확도를 높이려면 계약서/등기부 원문 확인을 권장해요.")
            else:
                for s in signals:
                    title = s.get("title", "위험 신호")
                    render_signal_card(
                        title=title,
                        detail=s.get("detail", ""),
                        evidence=s.get("evidence", "")
                    )

if "upload_texts" not in st.session_state:
    st.session_state.upload_texts = {"contract": "", "registry": "", "method": {"contract": "none", "registry": "none"}}
if "report" not in st.session_state:
    st.session_state.report = None
if "chat" not in st.session_state:
    st.session_state.chat = []
if "uploader_nonce" not in st.session_state:
    st.session_state.uploader_nonce = 0
if "contract_files" not in st.session_state:
    st.session_state.contract_files = []
if "registry_files" not in st.session_state:
    st.session_state.registry_files = []

tab_upload, tab_manual, tab_ai, tab_chat = st.tabs(["서류 업로드", "보증금·월세 입력", "AI 요약", "챗봇"])

with tab_upload:
    st.markdown("<div class='box'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:1.15rem; font-weight:950; letter-spacing:-0.5px;'>서류 업로드</div>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>계약서·등기부를 올리면 텍스트를 추출해 위험 신호를 확인합니다.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

    u1, u2 = st.columns(2, gap="large")
    nonce = st.session_state.uploader_nonce

    with u1:
        st.markdown("### 계약서 업로드")
        new_contracts = st.file_uploader(
            "계약서 추가",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            accept_multiple_files=True,
            key=f"uploader_contract_{nonce}",
            label_visibility="collapsed",
        )

    with u2:
        st.markdown("### 등기부등본 업로드")
        new_registries = st.file_uploader(
            "등기부 추가",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            accept_multiple_files=True,
            key=f"uploader_registry_{nonce}",
            label_visibility="collapsed",
        )

    # ✅ 파일 누적 저장(추가 업로드)
    def _add_unique_files(dest, new_files):
        seen = {(f.name, getattr(f, "size", None)) for f in dest}
        for f in (new_files or []):
            k = (f.name, getattr(f, "size", None))
            if k not in seen:
                dest.append(f)
                seen.add(k)

    changed = False
    if new_contracts:
        _add_unique_files(st.session_state.contract_files, new_contracts)
        changed = True
    if new_registries:
        _add_unique_files(st.session_state.registry_files, new_registries)
        changed = True

    # 업로더 비우기(다음 드래그가 "추가"처럼 되게)
    if changed:
        st.session_state.uploader_nonce += 1
        st.rerun()

    # ✅ 첨부된 파일 목록 (업로더 아래에 고정 표시)
    st.write("")
    st.markdown("#### 현재 첨부된 파일")

    l1, l2 = st.columns(2, gap="large")
    with l1:
        if st.session_state.contract_files:
            for i, f in enumerate(st.session_state.contract_files, 1):
                st.write(f"✅ {i}. {f.name}")
            if st.button("계약서 비우기", key="clear_contracts"):
                st.session_state.contract_files = []
                st.session_state.uploader_nonce += 1
                st.rerun()
        else:
            st.caption("계약서가 아직 없어요.")

    with l2:
        if st.session_state.registry_files:
            for i, f in enumerate(st.session_state.registry_files, 1):
                st.write(f"✅ {i}. {f.name}")
            if st.button("등기부 비우기", key="clear_registries"):
                st.session_state.registry_files = []
                st.session_state.uploader_nonce += 1
                st.rerun()
        else:
            st.caption("등기부가 아직 없어요.")

    # ✅ 버튼 row (항상 같은 위치에 고정)
    st.write("")
    def _reflect_upload_texts():
        if not st.session_state.contract_files and not st.session_state.registry_files:
            st.warning("먼저 계약서 또는 등기부등본 파일을 업로드해 주세요.")
            st.stop()

        ctext_parts, rtext_parts = [], []
        c_method, r_method = "none", "none"

        # 계약서 여러 개 합치기
        for f in st.session_state.contract_files:
            t, m = extract_text_from_upload(f.name, f.type or "", f.getvalue())
            if t:
                ctext_parts.append(t)
            c_method = m

        # 등기부 여러 개 합치기
        for f in st.session_state.registry_files:
            t, m = extract_text_from_upload(f.name, f.type or "", f.getvalue())
            if t:
                rtext_parts.append(t)
            r_method = m

        ctext = "\n\n".join(ctext_parts).strip()
        rtext = "\n\n".join(rtext_parts).strip()

        st.session_state.upload_texts = {
            "contract": ctext or "",
            "registry": rtext or "",
            "method": {"contract": c_method, "registry": r_method},
        }

    btn_analyze = st.button(
        "분석하기 / 리포트 만들기",
        use_container_width=True,
        type="primary",
        key="btn_analyze_upload",
    )

    # ✅ 메인: 자동 반영 → 분석 → report 저장
    if btn_analyze:
        with st.spinner("분석 중..."):
            _reflect_upload_texts()

            contract_text = st.session_state.upload_texts.get("contract", "")
            registry_text = st.session_state.upload_texts.get("registry", "")

            # ✅ 업로드 모드도 계약서에서 기본 정보(보증금/월세/임대인/주소) 자동 추출
            auto_manual = auto_extract_manual_from_contract(contract_text)
            # ✅ 등기부가 있으면 소유자(owner_name) 자동 추출
            if (registry_text or "").strip():
                auto_manual["owner_name"] = auto_extract_owner_from_registry(registry_text)

            # 등기부가 있으면 소유자 이름(간단)도 시도해볼 수 있지만, 지금은 비워도 OK
            auto_manual["report_source"] = "upload"

            st.session_state.report = analyze_risk(contract_text, registry_text, auto_manual)
            st.session_state.report_ai = None
            st.session_state.ai_summary_open = False
            st.session_state.extra_open = False
            st.session_state.chat = []
            st.session_state.report_source = "upload"
            method = st.session_state.upload_texts.get("method", {})
            c_method = method.get("contract")
            r_method = method.get("registry")

            def _method_msg(m):
                return {
                    "pdf:ok": "PDF 텍스트 추출 성공",
                    "pdf:empty": "PDF에서 텍스트를 찾지 못함(스캔본 가능)",
                    "pdf:no_support": "PDF 추출 불가(pdfplumber 미설치)",
                    "img:ok": "이미지 OCR 성공",
                    "img:no_ocr": "OCR 미지원",
                    "text:ok": "텍스트 파일 처리됨",
                    "pdf:ocr_ok": "PDF 스캔본 OCR 성공",
                    "pdf:ocr_empty": "PDF 스캔본 OCR 결과가 비어있음",
                    "pdf:ocr_no_ocr": "PDF는 스캔본인데 OCR 환경이 없어 추출 불가",
                    "pdf:ocr_error": "PDF OCR 처리 중 오류",
                    "pdf:ocr_no_fitz": "PDF OCR에 필요한 PyMuPDF(fitz) 미설치",
                    "pdf:ocr_no_tesseract": "PDF OCR에 필요한 tesseract 엔진(실행파일) 미설치/경로 문제",
                }.get(m, f"처리 상태: {m}")

            if c_method:
                st.info(f"📄 계약서: {_method_msg(c_method)}")
            if r_method:
                st.info(f"📄 등기부: {_method_msg(r_method)}")
            st.success("리포트 생성 완료")
            st.write("")
        # --- OCR/추출 원문 확인용 (업로드 탭에서만) ---
            with st.expander("🔎 추출 텍스트 확인 (OCR 원문)", expanded=False):
                method = st.session_state.get("upload_texts", {}).get("method", {})
                c_method = method.get("contract", "none")
                r_method = method.get("registry", "none")

                ctext = st.session_state.get("upload_texts", {}).get("contract", "") or ""
                rtext = st.session_state.get("upload_texts", {}).get("registry", "") or ""

                c1, c2 = st.columns(2, gap="large")

                with c1:
                    st.markdown("#### 📄 계약서")
                    st.caption(f"method: {c_method} / length: {len(ctext)} chars")
                    if ctext.strip():
                        st.text_area("계약서 추출 원문(앞 8000자)", ctext[:8000], height=260, key="debug_contract_textarea")
                        if len(ctext) > 8000:
                            st.info("너무 길어서 앞 8000자만 보여줘요.")
                    else:
                        st.warning("계약서 텍스트가 비어 있어요.")

                with c2:
                    st.markdown("#### 🧾 등기부")
                    st.caption(f"method: {r_method} / length: {len(rtext)} chars")
                    if rtext.strip():
                        st.text_area("등기부 추출 원문(앞 8000자)", rtext[:8000], height=260, key="debug_registry_textarea")
                        if len(rtext) > 8000:
                            st.info("너무 길어서 앞 8000자만 보여줘요.")
                    else:
                        st.warning("등기부 텍스트가 비어 있어요.")
        render_report_like_app(st.session_state.report)

with tab_manual:
    form = manual_step_form()
    manual = {
        "address": form["address"],
        "landlord_name": form["landlord_name"],
        "owner_name": form["owner_name"],
        "deposit": int(form["deposit_manwon"]) * 10000,
        "rent": int(form["rent_manwon"]) * 10000,
        "sale_price": int(form["sale_price_manwon"]) * 10000,
        "contract_type": form["contract_type"],
    }

    st.write("")
    if st.button("리포트 만들기", use_container_width=True, key="btn_make_report_manual"):
        contract_type = manual.get("contract_type")

        # 전세: 보증금 필수
        if contract_type == "전세" and manual.get("deposit", 0) == 0:
            st.warning("보증금을 입력해 주세요.")
            st.stop()

        # 월세: 보증금 또는 월세 중 하나는 필요
        if contract_type == "월세" and manual.get("deposit", 0) == 0 and manual.get("rent", 0) == 0:
            st.warning("보증금 또는 월세 중 하나는 입력해 주세요.")
            st.stop()

        contract_text = ""
        registry_text = ""
        manual["report_source"] = "manual"

        report = analyze_risk(contract_text, registry_text, manual)
        st.session_state.report = report
        st.session_state.report_ai = None
        st.session_state.ai_summary_open = False
        st.session_state.extra_open = False
        st.session_state.chat = []
        st.session_state.report_source = "manual"
        st.success("리포트 생성 완료")

    st.write("")
    if st.session_state.report and st.session_state.get("report_source") == "manual":
        render_report_like_app(st.session_state.report)
    
if "ai_summary_chat" not in st.session_state:
    st.session_state.ai_summary_chat = []  # [{"role":"user/assistant","content":...}]
if "ai_summary_last_report_id" not in st.session_state:
    st.session_state.ai_summary_last_report_id = None

with tab_ai:
    st.markdown("<div class='box'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:1.15rem; font-weight:950; letter-spacing:-0.5px;'>AI 요약 / 체크리스트</div>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>리포트 내용을 바탕으로 요약과 ‘지금 할 일’을 생성합니다.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

    if "ai_summary_text" not in st.session_state:
        st.session_state.ai_summary_text = None
    if "ai_checklist_text" not in st.session_state:
        st.session_state.ai_checklist_text = None

    if not st.session_state.report:
        st.info("먼저 ‘서류 업로드’ 또는 ‘보증금·월세 입력’에서 리포트를 만들어 주세요.")
    else:
        # ✅ 리포트가 바뀌면(새 분석) 결과 초기화(겹침 방지)
        current_sig = (st.session_state.report.get("created_at", "") or "")
        if st.session_state.get("ai_last_report_sig") != current_sig:
            st.session_state.ai_summary_text = None
            st.session_state.ai_checklist_text = None
            st.session_state.ai_last_report_sig = current_sig

        # --- 버튼 2개 병렬 ---
        b1, b2 = st.columns(2)
        with b1:
            btn_summary = st.button("요약 생성", use_container_width=True, key="btn_ai_make_summary")
        with b2:
            btn_checklist = st.button("체크리스트 생성", use_container_width=True, key="btn_ai_make_checklist")

        # --- 공통: OpenAI 가능 여부 ---
        client = get_client()
        if not client:
            st.warning("AI 기능을 쓰려면 OPENAI_API_KEY(환경변수)와 openai 패키지가 필요합니다.")
            st.stop()

        report = st.session_state.report

        # PDF 근거(올린 문서 일부)도 같이 넘김: 너가 원했던 “업로드한 pdf 근거로 요약”
        payload = {
            "level": report.get("level"),
            "signals": report.get("signals", [])[:12],
            "ratio": report.get("ratio"),
            "ids": report.get("ids", [])[:5],
            "created_at": report.get("created_at"),
            "preview_contract": (report.get("preview", {}).get("contract", "") or "")[:2000],
            "preview_registry": (report.get("preview", {}).get("registry", "") or "")[:2000],
        }

        # -------------------------
        # 1) 요약 생성 버튼
        # -------------------------
        if btn_summary:
            with st.spinner("요약 생성 중..."):
                messages = [
                    {"role": "system", "content": """
                    너는 전월세 계약 사기 예방 리포트를 설명하는 AI다.
                    아래 payload(분석 결과 + 계약서/등기부 일부)를 근거로
                    사용자가 이해하기 쉬운 'AI 요약'을 작성하라.

                    중요 원칙:
                    - 법적 판단/단정 금지
                    - '확인 필요', '~로 해석될 수 있음', '가능성' 표현 사용
                    - 체크리스트와 중복되는 행동 지시 금지
                    - 왜 주의가 필요한지 '이유 설명 중심'

                    출력 형식(반드시 유지):

                    [한 줄 요약]
                    - 현재 계약에서 가장 주의가 필요한 핵심을 1문장으로 설명

                    [종합 판단 요약]
                    - 3~5문장
                    - 어떤 조건/조항/권리관계가
                    왜 임차인에게 불리하게 해석될 수 있는지 설명
                    - 문구가 애매한 이유, 해석 리스크를 중심으로 서술

                    [문서 기준 근거]
                    - 계약서 또는 등기부에서 확인된 내용 2~3개
                    - 조항 번호 또는 키워드를 함께 제시
                    - 원문 일부는 짧게 인용
                    """},
                    {"role": "user", "content": f"[payload]\n{payload}"},
                ]
                res = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    temperature=0.3,
                )
                st.session_state.ai_summary_text = res.choices[0].message.content.strip()

        # -------------------------
        # 2) 체크리스트 생성 버튼
        # -------------------------
        if btn_checklist:
            with st.spinner("체크리스트 생성 중..."):
                # 먼저 룰 기반 TOP3(=원래 서류업로드에 있던 TOP3) 생성
                top3 = build_top3_actions_from_report(report)

                messages = [
                    {"role": "system", "content": """
                    너는 전월세 계약에서 사용자가 ‘지금 당장 할 일’을 만드는 도우미야.
                    - 확정 판단 금지(가능성/확인 필요)
                    - 법률 자문 아님
                    - 아래 payload(리포트+원문 일부)만 근거로 작성
                    출력 형식(반드시 그대로):
                    [TOP3]
                    - ...
                    - ...
                    - ...
                    [추가 체크 5개]
                    - ...
                    - ...
                    - ...
                    - ...
                    - ...
                    """ },
                    {"role": "user", "content": f"[payload]\n{payload}\n\n[기본 TOP3(룰 기반)]\n{top3}"},
                ]
                res = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    temperature=0.3,
                )
                st.session_state.ai_checklist_text = res.choices[0].message.content.strip()

        if st.session_state.ai_summary_text:
            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
            st.markdown("<div class='sectionTitle'>요약 결과</div>", unsafe_allow_html=True)
            st.write(st.session_state.ai_summary_text)

        if st.session_state.ai_checklist_text:
            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
            st.markdown("<div class='sectionTitle'>체크리스트</div>", unsafe_allow_html=True)
            st.write(st.session_state.ai_checklist_text)

with tab_chat:
    st.markdown("<div class='box'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:1.15rem; font-weight:950; letter-spacing:-0.5px;'>챗봇</div>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>리포트 내용을 바탕으로 확인할 질문을 던져보세요.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

    if not st.session_state.report:
        st.info("먼저 ‘서류 업로드’ 또는 ‘보증금·월세 입력’에서 리포트를 만들어 주세요.")
    else:
        key_ok = bool(os.getenv("OPENAI_API_KEY", "").strip())
        if not key_ok or not OPENAI_OK:
            st.warning(
                "챗봇을 쓰려면 OPENAI_API_KEY(환경변수)와 openai 패키지가 필요합니다.\n"
                "예) PowerShell:  $env:OPENAI_API_KEY='키'  후 재실행"
            )
        else:
            for m in st.session_state.chat:
                with st.chat_message("user" if m["role"] == "user" else "assistant"):
                    st.write(m["content"])

            msg = st.chat_input("예) 소유자 불일치면 어떤 서류 요청? 확정일자/전입은 언제?", key="chat_input_main")
            if msg:
                st.session_state.chat.append({"role": "user", "content": msg})
                with st.chat_message("assistant"):
                    with st.spinner("답변 생성 중..."):
                        ans = chat_answer(st.session_state.report, st.session_state.chat, msg)
                    st.write(ans)

                st.session_state.chat.append({"role": "assistant", "content": ans})
