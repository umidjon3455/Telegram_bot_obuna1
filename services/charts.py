"""
Generates daily statistics charts as PNG images using matplotlib.
Returns BytesIO object ready to send as Telegram photo.
"""
import io
import logging
from datetime import datetime, date
from typing import List

logger = logging.getLogger(__name__)


def _try_import_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        return plt, mdates
    except ImportError:
        return None, None


async def generate_stats_chart(daily_stats: List[dict]) -> io.BytesIO:
    """
    Generate a beautiful dual-line chart for new users and messages per day.
    Returns PNG as BytesIO.
    """
    plt, mdates = _try_import_matplotlib()
    if plt is None:
        raise ImportError("matplotlib not installed. Run: pip install matplotlib")

    dates = [row["date"] for row in daily_stats]
    new_users = [row["new_users"] for row in daily_stats]
    messages  = [row["messages"] for row in daily_stats]

    fig, ax1 = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#1e1e2e")
    ax1.set_facecolor("#1e1e2e")

    # New users line
    color_users = "#89b4fa"
    ax1.plot(dates, new_users, color=color_users, linewidth=2.5,
             marker="o", markersize=6, label="Yangi foydalanuvchilar")
    ax1.fill_between(dates, new_users, alpha=0.15, color=color_users)
    ax1.set_ylabel("Yangi foydalanuvchilar", color=color_users, fontsize=11)
    ax1.tick_params(axis="y", labelcolor=color_users)

    # Messages line (secondary axis)
    ax2 = ax1.twinx()
    color_msg = "#a6e3a1"
    ax2.plot(dates, messages, color=color_msg, linewidth=2.5,
             marker="s", markersize=6, label="Xabarlar", linestyle="--")
    ax2.fill_between(dates, messages, alpha=0.10, color=color_msg)
    ax2.set_ylabel("Xabarlar soni", color=color_msg, fontsize=11)
    ax2.tick_params(axis="y", labelcolor=color_msg)

    # X axis formatting
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax1.xaxis.set_major_locator(mdates.DayLocator())
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right", color="#cdd6f4")
    ax1.tick_params(axis="x", colors="#cdd6f4")

    # Grid and spines
    ax1.grid(color="#313244", linestyle="--", linewidth=0.7, alpha=0.7)
    for spine in ax1.spines.values():
        spine.set_edgecolor("#313244")
    for spine in ax2.spines.values():
        spine.set_edgecolor("#313244")

    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               facecolor="#313244", edgecolor="#45475a",
               labelcolor="#cdd6f4", fontsize=9, loc="upper left")

    ax1.set_title("📊 7 kunlik statistika", color="#cdd6f4", fontsize=14, pad=15, fontweight="bold")
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf
