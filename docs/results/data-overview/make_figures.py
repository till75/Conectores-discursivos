"""Describe the application corpus: videos, channels, threads, and reply depth.

Inputs (local only, gitignored): doc/comentarios_youtube_normalizados.csv
and doc/referencia_piloto.csv. Only metadata columns are read; no comment text.

Outputs, written next to this file:
- videos_summary.csv
- depth_counts.csv
- reference_summary.txt
- fig1_comments_per_video.png
- fig2_threads_depth.png

Run from the repository root:
    .venv/Scripts/python.exe docs/results/data-overview/make_figures.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOC = ROOT / "doc"

META = [
    "video_id",
    "video_title",
    "video_channel_title",
    "video_published_at",
    "comment_id",
    "parent_comment_id",
    "thread_id",
    "is_reply",
    "total_thread_replies",
]


def load_meta() -> pd.DataFrame:
    return pd.read_csv(
        DOC / "comentarios_youtube_normalizados.csv",
        usecols=META,
        dtype=str,
        encoding="utf-8-sig",
    )


def add_depth(df: pd.DataFrame) -> pd.DataFrame:
    parent = dict(zip(df["comment_id"], df["parent_comment_id"]))
    known = set(parent)

    def depth(comment_id: str, seen: set[str] | None = None) -> int:
        seen = seen or set()
        if comment_id in seen:
            return 1
        seen.add(comment_id)
        up = parent.get(comment_id)
        if not isinstance(up, str) or up not in known or up == comment_id:
            return 1
        return 1 + depth(up, seen)

    out = df.copy()
    out["depth"] = out["comment_id"].map({cid: depth(cid) for cid in known})
    return out


def videos_table(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("video_id")
    table = pd.DataFrame(
        {
            "title": grouped["video_title"].first(),
            "channel": grouped["video_channel_title"].first(),
            "published": grouped["video_published_at"].first(),
            "comments": grouped.size(),
            "threads": grouped["thread_id"].nunique(),
            "top_level": grouped["is_reply"].apply(lambda s: (s == "False").sum()),
            "replies": grouped["is_reply"].apply(lambda s: (s == "True").sum()),
        }
    )
    return table.sort_values("comments", ascending=False)


def reference_summary() -> list[str]:
    ref = pd.read_csv(
        DOC / "referencia_piloto.csv",
        usecols=["video_id", "comment_id", "anotacion"],
        dtype=str,
        encoding="utf-8-sig",
    )
    labels = ref["anotacion"].fillna("").str.findall(r"\[[^\[\]]+?::[^\[\]]+?\]")
    spans = [x for row in labels for x in row]
    units = {x.split("::")[0][1:] for x in spans}
    cats = {x.split("::")[1][:-1] for x in spans}
    annotated = (ref["anotacion"].fillna("Sin etiquetas") != "Sin etiquetas").sum()
    main_ids = set(load_meta()["comment_id"])
    return [
        f"rows: {len(ref)}",
        f"rows with at least one label: {annotated}",
        f"label spans: {len(spans)}",
        f"distinct units: {len(units)}",
        f"distinct labels: {len(cats)}",
        f"distinct video titles: {ref['video_id'].nunique()}",
        "titles: " + str(ref["video_id"].value_counts().to_dict()),
        "comment_ids present in application corpus: "
        + str(ref["comment_id"].isin(main_ids).sum()),
    ]


def plot_videos(videos: pd.DataFrame, total: int) -> None:
    v = videos.sort_values("comments")
    short = [t if len(t) <= 52 else t[:49] + "..." for t in v["title"]]
    fig = plt.figure(figsize=(15, 8), dpi=150)
    gs = fig.add_gridspec(1, 2, width_ratios=[2.5, 1], wspace=0.35)

    ax = fig.add_subplot(gs[0, 0])
    y = np.arange(len(v))
    ax.barh(y, v["top_level"], color="#c6dbef", label="top-level comments")
    ax.barh(y, v["replies"], left=v["top_level"], color="#2171b5", label="replies")
    for i, (_, row) in enumerate(v.iterrows()):
        ax.text(
            row["comments"] + 25, i, f"{row['comments']:,}", va="center", fontsize=8
        )
    ax.set_yticks(y)
    ax.set_yticklabels(short, fontsize=8)
    ax.set_xlabel("comments")
    ax.set_title(
        f"Comments per video ({len(v)} videos, {total:,} comments)",
        fontsize=11,
        loc="left",
    )
    ax.set_xlim(0, 1980)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#e5e7eb", linewidth=0.6)
    ax.set_axisbelow(True)

    ax2 = fig.add_subplot(gs[0, 1])
    bins = [0, 100, 250, 500, 750, 1250, 2000]
    ax2.hist(v["comments"], bins=bins, color="#2171b5", edgecolor="white")
    ax2.set_xscale("log")
    ax2.set_xlabel("comments per video (log scale)")
    ax2.set_ylabel("videos")
    ax2.set_title("Distribution of video size", fontsize=11, loc="left")
    median = v["comments"].median()
    ax2.axvline(median, color="#b45309", linestyle="--", linewidth=1)
    ax2.text(median * 1.08, 9.2, f"median {median:.0f}", color="#b45309", fontsize=8)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.grid(axis="y", color="#e5e7eb", linewidth=0.6)
    ax2.set_axisbelow(True)

    fig.savefig(
        HERE / "fig1_comments_per_video.png", bbox_inches="tight", facecolor="white"
    )
    plt.close(fig)


def plot_threads(df: pd.DataFrame, depth_counts: pd.Series) -> None:
    sizes = df.groupby("thread_id").size()
    single = (sizes == 1).mean()

    fig = plt.figure(figsize=(15, 4.6), dpi=150)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.3, 1, 1.3], wspace=0.32)

    ax = fig.add_subplot(gs[0, 0])
    buckets = {
        "1": (sizes == 1).sum(),
        "2": (sizes == 2).sum(),
        "3": (sizes == 3).sum(),
        "4": (sizes == 4).sum(),
        "5": (sizes == 5).sum(),
        "6-10": sizes.between(6, 10).sum(),
        "11-20": sizes.between(11, 20).sum(),
        "21+": (sizes >= 21).sum(),
    }
    ax.bar(list(buckets), list(buckets.values()), color="#2171b5")
    ax.set_yscale("log")
    ax.set_ylabel("threads (log scale)")
    ax.set_xlabel("comments in thread")
    ax.set_title(
        f"{single:.0%} of threads are a single comment", fontsize=11, loc="left"
    )
    for i, val in enumerate(buckets.values()):
        ax.text(i, val * 1.15, f"{val:,}", ha="center", fontsize=8)
    ax.set_ylim(0.7, 9000)
    ax.spines[["top", "right"]].set_visible(False)

    ax2 = fig.add_subplot(gs[0, 1])
    values = [depth_counts.get(1, 0), depth_counts.get(2, 0)]
    bars = ax2.bar(["top-level", "replies"], values, color=["#c6dbef", "#2171b5"])
    for bar, val in zip(bars, values):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            val + 120,
            f"{val:,}\n{val / len(df):.0%}",
            ha="center",
            fontsize=8,
        )
    ax2.set_ylim(0, 7600)
    ax2.set_ylabel("comments")
    ax2.set_title("Depth is binary on YouTube", fontsize=11, loc="left")
    ax2.spines[["top", "right"]].set_visible(False)

    ax3 = fig.add_subplot(gs[0, 2])
    xs = np.arange(1, 31)
    share = np.array([sizes[sizes <= x].sum() / sizes.sum() for x in xs])
    ax3.plot(xs, share * 100, color="#2171b5", linewidth=2)
    marks = [1, 2, 5, 10, 30]
    ax3.scatter(marks, share[[x - 1 for x in marks]] * 100, color="#b45309", zorder=3)
    for x in marks:
        ax3.annotate(
            f"{share[x - 1]:.0%}",
            (x, share[x - 1] * 100),
            textcoords="offset points",
            xytext=(4, -12),
            fontsize=8,
            color="#b45309",
        )
    ax3.set_xlabel("thread size (comments)")
    ax3.set_ylabel("% of comments")
    ax3.set_title("Comments sit in small threads", fontsize=11, loc="left")
    ax3.set_ylim(40, 102)
    ax3.spines[["top", "right"]].set_visible(False)
    ax3.grid(color="#e5e7eb", linewidth=0.6)
    ax3.set_axisbelow(True)

    fig.savefig(HERE / "fig2_threads_depth.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    df = add_depth(load_meta())
    videos = videos_table(df)
    videos.to_csv(HERE / "videos_summary.csv", index=False, encoding="utf-8")

    depth_counts = df["depth"].value_counts().sort_index()
    depth_counts.rename_axis("depth").rename("comments").to_csv(
        HERE / "depth_counts.csv", encoding="utf-8"
    )

    ref_lines = reference_summary()
    (HERE / "reference_summary.txt").write_text("\n".join(ref_lines), encoding="utf-8")

    plot_videos(videos, len(df))
    plot_threads(df, depth_counts)

    sizes = df.groupby("thread_id").size()
    print(f"comments: {len(df):,} | videos: {len(videos)} | threads: {len(sizes):,}")
    print(f"replies: {(df['is_reply'] == 'True').sum():,}")
    print(f"single-comment threads: {(sizes == 1).sum():,} ({(sizes == 1).mean():.1%})")
    print(f"depth: {depth_counts.to_dict()}")
    print("reference:", "; ".join(ref_lines))


if __name__ == "__main__":
    main()
