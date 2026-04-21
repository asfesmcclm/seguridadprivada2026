#!/usr/bin/env python3
"""
convenio_to_json.py
Conversor de Convenio Colectivo (DOCX) a JSON estructurado.

Uso:
  python convenio_to_json.py                              # usa rutas por defecto
  python convenio_to_json.py entrada.docx salida.json    # rutas personalizadas

Detecta automáticamente:
  Preámbulo · Capítulos · Artículos (bis/ter) · Disposiciones · Anexos · Adendas
"""

import re, json, sys, subprocess

# ── PATRONES ──────────────────────────────────────────────────────────────────
RE_CAP_INLINE   = re.compile(r'^(?:CAP[IÍ]TULO|Cap[ií]tulo)\s+([IVXLCDM]+)[.\s]+(.+)$')
RE_CAP_NUM_ONLY = re.compile(r'^(?:CAP[IÍ]TULO|Cap[ií]tulo)\s+([IVXLCDM]+)\s*$')
RE_ARTICULO     = re.compile(r'^Art[ií]culo\s+(\d+\s*(?:bis|ter)?)\s*[.\s]+(.+?)\.?\s*$')
RE_DISP_AD      = re.compile(r'^Disposici[oó]n\s+adicional\s+(\w+)\.?\s*(.*)')
RE_DISP_TR      = re.compile(r'^Disposici[oó]n\s+transitoria\s+(\w+)\.?\s*(.*)')
RE_DISP_FI      = re.compile(r'^Disposici[oó]n\s+final\s+(\w+)\.?\s*(.*)')
RE_ANEXO        = re.compile(r'^Anexo\s+(\w+)[.\s]+(.*)')
RE_ADENDA       = re.compile(r'^Adenda\s+(\w+)[.\s]+(.*)')
RE_ADENDAS_SEC  = re.compile(r'^ADENDAS?\s*$')
RE_PREAMBULO    = re.compile(r'^(?:PR[EÉ][AÁ]MBULO|Preámbulo|Preambulo)\s*$')

# ── EXTRACCIÓN ────────────────────────────────────────────────────────────────
def extract_text(path):
    r = subprocess.run(['extract-text', path], capture_output=True,
                       text=True, encoding='utf-8')
    return [l.strip() for l in r.stdout.splitlines()]

def find_body_start(lines):
    """Primera aparición de PREÁMBULO sin punto = inicio del cuerpo."""
    for i, l in enumerate(lines):
        if RE_PREAMBULO.match(l):
            return i
    return 0

# ── PARSER ────────────────────────────────────────────────────────────────────
def parse(lines):
    titulo   = next((l for l in lines[:10] if l), "")
    m        = re.search(r'(\d{4}[-\u2013]\d{4})', titulo)
    vigencia = m.group(1) if m else ""

    body = lines[find_body_start(lines):]
    res  = {"titulo": titulo, "vigencia": vigencia, "preambulo": "",
            "capitulos": [], "disposiciones_adicionales": [],
            "disposiciones_transitorias": [], "disposiciones_finales": [],
            "anexos": [], "adendas": []}

    sec=None; cap_i=None; item=None; buf=[]; in_adenda=False; pend_num=None

    def flush():
        t = " ".join(b for b in buf if b).strip()
        buf.clear()
        return re.sub(r'\s+', ' ', t)

    def save_item():
        nonlocal item
        if not item: return
        item["texto"] = flush()
        if   sec=="art" and cap_i is not None:
            res["capitulos"][cap_i]["articulos"].append(item)
        elif sec=="da":  res["disposiciones_adicionales"].append(item)
        elif sec=="dt":  res["disposiciones_transitorias"].append(item)
        elif sec=="df":  res["disposiciones_finales"].append(item)
        elif sec=="anx": res["anexos"].append(item)
        elif sec=="add": res["adendas"].append(item)
        item = None

    def mk_item(s, num, tit):
        nonlocal sec, item
        save_item(); sec=s
        item = {"num": num, "titulo": tit.strip().rstrip('.'), "texto": ""}
        buf.clear()

    def mk_cap(num, tit):
        nonlocal sec, item, cap_i, pend_num
        save_item()
        if sec=="pre": res["preambulo"] = flush()
        sec="cap"; item=None; pend_num=None; buf.clear()
        res["capitulos"].append({"num":num,"titulo":tit.strip().rstrip('.'),"articulos":[]})
        cap_i = len(res["capitulos"]) - 1

    for line in body:
        if RE_ADENDAS_SEC.match(line):
            save_item()
            if sec=="pre": res["preambulo"] = flush()
            in_adenda=True; sec=None; buf.clear(); continue

        if RE_PREAMBULO.match(line):
            if in_adenda: continue        # preámbulo de adenda: ignorar
            save_item()
            if sec=="pre": res["preambulo"] = flush()
            sec="pre"; buf.clear(); pend_num=None; continue

        if not in_adenda:
            m2 = RE_CAP_INLINE.match(line)
            if m2: mk_cap(m2.group(1).strip(), m2.group(2).strip()); continue

            m2 = RE_CAP_NUM_ONLY.match(line)
            if m2: pend_num = m2.group(1).strip(); continue

            if pend_num and line:
                mk_cap(pend_num, line.strip()); continue

            m2 = RE_ARTICULO.match(line)
            if m2: mk_item("art", m2.group(1).strip(), m2.group(2).strip()); continue

            m2 = RE_DISP_AD.match(line)
            if m2: mk_item("da", m2.group(1).strip(), m2.group(2).strip()); continue

            m2 = RE_DISP_TR.match(line)
            if m2: mk_item("dt", m2.group(1).strip(), m2.group(2).strip()); continue

            m2 = RE_DISP_FI.match(line)
            if m2: mk_item("df", m2.group(1).strip(), m2.group(2).strip()); continue

            m2 = RE_ANEXO.match(line)
            if m2: mk_item("anx", m2.group(1).strip(), m2.group(2).strip()); continue
        else:
            m2 = RE_ADENDA.match(line)
            if m2: mk_item("add", m2.group(1).strip(), m2.group(2).strip()); continue

        if sec in ("pre","art","da","dt","df","anx","add") and line:
            buf.append(line)

    save_item()
    if sec=="pre" and buf: res["preambulo"] = flush()
    return res

# ── ESTADÍSTICAS ──────────────────────────────────────────────────────────────
def print_stats(data):
    total = sum(len(c["articulos"]) for c in data["capitulos"])
    print(f"\n{'─'*54}")
    print(f"  {data['titulo'][:52]}")
    print(f"  Vigencia: {data['vigencia']}")
    print(f"{'─'*54}")
    print(f"  Capítulos:          {len(data['capitulos'])}")
    print(f"  Artículos:          {total}")
    print(f"  Disp. adicionales:  {len(data['disposiciones_adicionales'])}")
    print(f"  Disp. transitorias: {len(data['disposiciones_transitorias'])}")
    print(f"  Disp. finales:      {len(data['disposiciones_finales'])}")
    print(f"  Anexos:             {len(data['anexos'])}")
    print(f"  Adendas:            {len(data['adendas'])}")
    print(f"  Preámbulo:          {len(data['preambulo'])} chars")
    print(f"{'─'*54}")
    print()
    for c in data["capitulos"]:
        arts = c["articulos"]
        rng  = f"{arts[0]['num']}–{arts[-1]['num']}" if arts else "–"
        print(f"  Cap.{c['num']:6s} | {len(arts):2d} arts ({rng}) | {c['titulo'][:38]}")
    print()

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    docx = sys.argv[1] if len(sys.argv)>1 else "/mnt/user-data/uploads/convenio_seguridad_privada_limpio.docx"
    out  = sys.argv[2] if len(sys.argv)>2 else "/mnt/user-data/outputs/convenio_seguridad_privada.json"

    print(f"\nLeyendo: {docx}")
    lines = extract_text(docx)
    print(f"Líneas extraídas: {len(lines)}")
    print("Parseando estructura...")
    data = parse(lines)
    print_stats(data)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    kb = len(json.dumps(data, ensure_ascii=False)) / 1024
    print(f"✓ JSON guardado: {out}  ({kb:.1f} KB)\n")

if __name__ == "__main__":
    main()
