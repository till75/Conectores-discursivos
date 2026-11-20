"""Audit the project inputs and reconcile the published counts.

Reads local, gitignored inputs from doc/:
- listado_fuentes2009.csv, csl_excluidas.csv, referencia_piloto.csv
- comentarios_youtube.csv, comentarios_youtube_normalizados.csv
- Corpus piloto youtube__anotado.xlsx

Writes only counts, comment IDs, units, and labels next to this file. No comment
text is written, so the outputs can be published under R5.

Run from the repository root:
    .venv/Scripts/python.exe docs/results/data-overview/audit_inputs.py
"""

import re
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOC = ROOT / "doc"

LETRA = r"[\wáéíóúñÁÉÍÓÚÑü]"
ETIQ = re.compile(r"\[([^\[\]]+?)::([^\[\]]+)\]")

ANNOTATORS = [
    "anotador_1_jorge",
    "anotador_2_hernan",
    "anotador_3_javier",
    "anotadora_4_vannia",
]
REAL = ["anotador_1_jorge", "anotador_3_javier", "anotadora_4_vannia"]

lines: list[str] = []


def say(*parts: object) -> None:
    lines.append(" ".join(str(p) for p in parts))


def as_text(value: object) -> str:
    return value if isinstance(value, str) else ""


def norm_form(series: pd.Series) -> pd.Series:
    stripped = series.str.replace(r"\s*\d+$", "", regex=True)
    return stripped.str.strip().str.lower()


def label_from_listing(macro: str, cat: str, sub: str) -> str:
    cat = (cat or "").strip()
    sub = (sub or "").strip()
    if macro == "Operador":
        return "OP:" + cat.upper()
    if cat.startswith("Ordenador"):
        return "CON:" + ("INICIO" if sub == "De inicio" else sub.upper())
    if cat.startswith("Reformulativo"):
        return "CON:REFORMULATIVOS"
    return "CON:" + cat.upper()


def load_listing():
    listing = pd.read_csv(DOC / "listado_fuentes2009.csv", encoding="utf-8")
    listing["forma"] = norm_form(listing["unidad"])
    listing["etiqueta"] = [
        label_from_listing(m, c, s)
        for m, c, s in zip(
            listing.macrofuncion, listing.categoria, listing.subcategoria
        )
    ]
    admitidas = (
        listing.groupby("forma")["etiqueta"]
        .apply(lambda s: list(dict.fromkeys(s)))
        .to_dict()
    )
    ordered = sorted(admitidas, key=len, reverse=True)
    pattern = rf"(?<!{LETRA})(" + "|".join(
        re.escape(form) for form in ordered
    ) + rf")(?!{LETRA})"
    return listing, admitidas, re.compile(pattern, re.I)


def read_annotation(
    text: str, fallback: str
) -> tuple[str, list[tuple[int, int, str]]]:
    """Return the plain text and the bracket spans of one annotated cell."""
    if "::" not in text:
        return fallback, []
    plain, spans, pos = "", [], 0
    for match in ETIQ.finditer(text):
        plain += text[pos : match.start()]
        start = len(plain)
        plain += match.group(1)
        spans.append((start, len(plain), match.group(1).lower()))
        pos = match.end()
    plain += text[pos:]
    return plain, spans


def build_candidates(ref: pd.DataFrame, regex, csl_pairs: set[tuple[str, str]]):
    """Replicate the notebook's candidate construction, including exclusions."""
    rows: list[dict[str, object]] = []
    undetected = 0
    for _, row in ref.iterrows():
        comment_id = row["comment_id"]
        fallback = as_text(row["text_normalized"])
        plain, spans = read_annotation(row["anotacion"], fallback)
        zones = [
            (a, b)
            for a, b, unit in spans
            if (comment_id, unit) in csl_pairs
        ]
        spans = [span for span in spans if (comment_id, span[2]) not in csl_pairs]
        used: set[int] = set()
        for match in regex.finditer(plain):
            start, end = match.span()
            if any(a < end and start < b for a, b in zones):
                continue
            part_of_other = False
            hit = False
            for index, (a, b, _) in enumerate(spans):
                if a < end and start < b:
                    if index in used:
                        part_of_other = True
                    else:
                        used.add(index)
                        hit = True
                    break
            if part_of_other:
                continue
            rows.append(
                {
                    "comment_id": comment_id,
                    "unidad": match.group(0).lower(),
                    "oro": hit,
                    "unlabelled_row": len(spans) == 0,
                }
            )
        undetected += len([i for i in range(len(spans)) if i not in used])
    return pd.DataFrame(rows), undetected


def spans_per_cell(workbook: pd.DataFrame, column: str):
    return [
        read_annotation(value, "")[1] if isinstance(value, str) else []
        for value in workbook[column]
    ]


def annotator_table(workbook: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in ANNOTATORS:
        cells = workbook[column]
        spans = spans_per_cell(workbook, column)
        rows.append(
            {
                "annotator": column,
                "reviewed": int(cells.notna().sum()),
                "with_label": sum(1 for s in spans if s),
                "spans": sum(len(s) for s in spans),
                "sin_etiquetas": int((cells.fillna("") == "Sin etiquetas").sum()),
                "cells_with_markup": int(
                    cells.fillna("").str.contains("::", regex=False).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def parsed_labels(workbook: pd.DataFrame) -> dict[str, dict[str, Counter]]:
    return {
        column: {
            cid: Counter(
                (m.group(1).lower(), m.group(2).strip().upper())
                for m in ETIQ.finditer(value)
            )
            if isinstance(value, str)
            else Counter()
            for cid, value in zip(workbook["comment_id"], workbook[column])
        }
        for column in ANNOTATORS
    }


def agreement_table(workbook: pd.DataFrame) -> pd.DataFrame:
    parsed = parsed_labels(workbook)
    reviewed = {
        column: set(workbook.loc[workbook[column].notna(), "comment_id"])
        for column in ANNOTATORS
    }
    rows = []
    for a, b in combinations(ANNOTATORS, 2):
        shared = reviewed[a] & reviewed[b]
        both_empty = both_agree = category = detection = one_empty = 0
        for cid in shared:
            ca, cb = parsed[a][cid], parsed[b][cid]
            if not ca and not cb:
                both_empty += 1
            elif ca == cb:
                both_agree += 1
            elif ca and cb and {u for u, _ in ca} == {u for u, _ in cb}:
                category += 1
            elif ca and cb:
                detection += 1
            else:
                one_empty += 1
        active = len(shared) - both_empty
        rows.append(
            {
                "pair": f"{a} vs {b}",
                "shared": len(shared),
                "both_empty": both_empty,
                "both_agree": both_agree,
                "category_conflict": category,
                "detection_conflict": detection,
                "one_empty": one_empty,
                "agreement_on_active": round(both_agree / active, 3) if active else 0.0,
            }
        )
    return pd.DataFrame(rows)


def count_matches(series: pd.Series, regex) -> int:
    return sum(len(regex.findall(text)) for text in series.fillna(""))


def main() -> None:
    listing, admitidas, regex = load_listing()
    say("=== LISTING")
    say("rows:", len(listing), "| distinct forms:", len(admitidas))
    say("macrofunction:", listing["macrofuncion"].value_counts().to_dict())
    say("polifuncional:", listing["polifuncional"].value_counts().to_dict())
    say(
        "forms with exactly one category:",
        sum(len(v) == 1 for v in admitidas.values()),
    )
    say(
        "forms with more than one category:",
        sum(len(v) > 1 for v in admitidas.values()),
    )
    raw_bytes = (DOC / "listado_fuentes2009.csv").read_bytes()
    say("no BOM:", raw_bytes[:3] != b"\xef\xbb\xbf", "| bytes:", len(raw_bytes))

    raw = pd.read_csv(DOC / "comentarios_youtube.csv", encoding="utf-8-sig", dtype=str)
    norm_path = DOC / "comentarios_youtube_normalizados.csv"
    norm = pd.read_csv(norm_path, encoding="utf-8-sig", dtype=str)
    say("\n=== RAW VS NORMALIZED")
    say("raw:", raw.shape, "| normalized:", norm.shape)
    differs = int((raw["comment_text"] != raw["comment_text_raw"]).sum())
    say("comment_text differs from comment_text_raw:", differs)
    users_text = int(raw["comment_text"].fillna("").str.count("@USER").sum())
    users_raw = int(raw["comment_text_raw"].fillna("").str.count("@USER").sum())
    say("@USER in comment_text:", users_text, "| in comment_text_raw:", users_raw)
    changed = int(
        (norm["text_normalized"].fillna("") != norm["comment_text"].fillna("")).sum()
    )
    share = f"({changed / len(norm):.1%})"
    say("text_normalized differs from comment_text:", changed, share)
    emoji_tokens = int(
        norm["text_normalized"].fillna("").str.count(r"\[[0-9]+ emoticon").sum()
    )
    say("emoji tokens inserted:", emoji_tokens)
    say("rows flagged in revisar:", int((norm["revisar"].fillna("") != "").sum()))

    say("\n=== APPLICATION CANDIDATES")
    on_raw = count_matches(norm["comment_text"], regex)
    on_norm = count_matches(norm["text_normalized"], regex)
    say("listing matches on comment_text:", on_raw)
    say("listing matches on text_normalized:", on_norm)
    say("difference:", on_norm - on_raw)
    per_comment = norm["text_normalized"].fillna("").map(
        lambda t: len(regex.findall(t))
    )
    say(
        "comments with at least one match:",
        int((per_comment > 0).sum()),
        "of",
        len(norm),
    )

    ref = pd.read_csv(DOC / "referencia_piloto.csv", encoding="utf-8-sig", dtype=str)
    ref["anotacion"] = ref["anotacion"].fillna("Sin etiquetas")
    csl = pd.read_csv(DOC / "csl_excluidas.csv", encoding="utf-8-sig", dtype=str)
    csl_pairs = set(zip(csl["comment_id"], csl["unidad"].str.lower()))

    candidates, undetected = build_candidates(ref, regex, csl_pairs)
    spans = [
        span
        for _, row in ref.iterrows()
        for span in read_annotation(
            row["anotacion"], as_text(row["text_normalized"])
        )[1]
        if (row["comment_id"], span[2]) not in csl_pairs
    ]
    label_pairs = [
        (match.group(1).lower(), match.group(2).strip().upper())
        for text in ref["anotacion"]
        for match in ETIQ.finditer(text)
    ]
    say("\n=== REFERENCE")
    say(
        "rows:",
        len(ref),
        "| rows with a label:",
        int(ref["anotacion"].str.contains("::").sum()),
    )
    say("spans:", len(label_pairs), "| after CSL exclusion:", len(spans))
    say("distinct units:", len({unit for unit, _ in label_pairs}))
    say("distinct labels:", len({label for _, label in label_pairs}))
    say("candidates after CSL and multiword exclusion:", len(candidates))
    say("candidates with a gold label:", int(candidates["oro"].sum()))
    say("candidates without a gold label:", int((~candidates["oro"]).sum()))
    unlabelled = int(candidates["unlabelled_row"].sum())
    say("candidates from 'Sin etiquetas' rows:", unlabelled)
    say("reference spans the listing never detects:", undetected)
    candidates.to_csv(
        HERE / "reference_candidates.csv", index=False, encoding="utf-8"
    )

    say("\n=== CSL")
    say("rows:", len(csl), "| distinct units:", csl["unidad"].nunique())
    say("distinct comments:", csl["comment_id"].nunique())
    in_ref = bool(csl["comment_id"].isin(ref["comment_id"]).all())
    say("all rows are in the reference:", in_ref)

    workbook_path = DOC / "Corpus piloto youtube__anotado.xlsx"
    workbook = pd.read_excel(workbook_path, sheet_name="Comentarios")
    annotators = annotator_table(workbook)
    annotators.to_csv(HERE / "annotators.csv", index=False, encoding="utf-8")
    say("\n=== WORKBOOK")
    say("shape:", workbook.shape, "| videos:", workbook["video_id"].nunique())
    say("channels:", workbook["video_channel_title"].nunique())
    say("threads:", workbook["thread_id"].nunique())
    say(
        "text_normalized non-null:",
        int(workbook["text_normalized"].notna().sum()),
        "| anotacion_final non-null:",
        int(workbook["anotacion_final"].notna().sum()),
    )
    for row in annotators.itertuples(index=False):
        say(
            f"  {row.annotator}: reviewed {row.reviewed}, label {row.with_label}, "
            f"spans {row.spans}, 'Sin etiquetas' {row.sin_etiquetas}"
        )

    counts = workbook[ANNOTATORS].notna().sum(axis=1)
    by_columns = counts.value_counts().sort_index().to_dict()
    say("comments by number of annotator columns:", by_columns)
    multi = set(workbook.loc[counts >= 2, "comment_id"])
    reference_ids = set(ref["comment_id"])
    say("reference equals comments with two or more columns:", multi == reference_ids)
    real_counts = workbook[REAL].notna().sum(axis=1)
    in_reference = workbook["comment_id"].isin(reference_ids)
    say(
        "real annotators per reference comment:",
        real_counts[in_reference].value_counts().sort_index().to_dict(),
    )
    say(
        "videos in the reference:",
        workbook.loc[in_reference, "video_id"].nunique(),
    )

    agreement = agreement_table(workbook)
    agreement.to_csv(HERE / "agreement.csv", index=False, encoding="utf-8")
    say("\n=== AGREEMENT (all pairs)")
    for row in agreement.itertuples(index=False):
        say(
            f"  {row.pair}: shared {row.shared}, both empty {row.both_empty}, "
            f"agree {row.both_agree}, category {row.category_conflict}, "
            f"detection {row.detection_conflict}, one empty {row.one_empty}, "
            f"active agreement {row.agreement_on_active:.1%}"
        )

    say("\n=== REFERENCE VS ANNOTATORS (labelled reference rows)")
    labelled = ref[ref["anotacion"].str.contains("::")]
    parsed = parsed_labels(workbook)
    for column in ANNOTATORS:
        reviewed = set(workbook.loc[workbook[column].notna(), "comment_id"])
        identical = other = empty = not_reviewed = 0
        for _, row in labelled.iterrows():
            cid = row["comment_id"]
            if cid not in reviewed:
                not_reviewed += 1
                continue
            gold = Counter(
                (m.group(1).lower(), m.group(2).strip().upper())
                for m in ETIQ.finditer(row["anotacion"])
            )
            if parsed[column][cid] == gold:
                identical += 1
            elif parsed[column][cid]:
                other += 1
            else:
                empty += 1
        say(
            f"  {column}: identical {identical}, other labels {other}, "
            f"reviewed with no label {empty}, not reviewed {not_reviewed}"
        )

    (HERE / "audit_summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print("written", len(lines), "lines")


if __name__ == "__main__":
    main()
