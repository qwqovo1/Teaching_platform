import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# --- Find fonts ---
# Chinese font
chinese_font = None
for candidate in ['WenQuanYi Zen Hei', 'SimSun', 'SimHei', 'WenQuanYi Micro Hei',
                   'Noto Sans CJK SC', 'Noto Serif CJK SC', 'AR PL UMing CN', 'Source Han Sans SC']:
    try:
        fp = fm.FontProperties(family=candidate)
        if fm.findfont(fp) != fm.findfont(fm.FontProperties()):
            chinese_font = candidate
            break
    except:
        continue
if chinese_font is None:
    for f in fm.findSystemFonts():
        try:
            fp = fm.FontProperties(fname=f)
            name = fp.get_name()
            if any(kw in name.lower() for kw in ['cjk', 'hei', 'song', 'ming', 'noto sans cjk', 'wenquan', 'wqy']):
                chinese_font = name
                break
        except:
            continue

ch_prop = fm.FontProperties(family=chinese_font) if chinese_font else fm.FontProperties()

# English font - try Times New Roman, fall back to serif
en_family = 'Times New Roman'
try:
    fp = fm.FontProperties(family='Times New Roman')
    if fm.findfont(fp) == fm.findfont(fm.FontProperties()):
        en_family = 'DejaVu Serif'
except:
    en_family = 'DejaVu Serif'

en_prop = fm.FontProperties(family=en_family)

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': [en_family, 'DejaVu Serif', 'serif'],
    'mathtext.fontset': 'stix',
    'axes.unicode_minus': False,
})

# --- Data ---
x_labels = ['基线', '4分钟', '8分钟', '12分钟']
x = np.arange(len(x_labels))

data = {
    'BAL':  {'mean': [62.5, 63.8, 65.4, 64.2], 'sd': [6.7, 5.9, 5.8, 5.4], 'color': '#1F77B4', 'marker': 'o'},
    'BFR':  {'mean': [62.8, 63.1, 62.9, 62.6], 'sd': [6.4, 6.2, 6.5, 6.3], 'color': '#E41A1C', 'marker': 's'},
    'VRT':  {'mean': [63.2, 62.0, 61.5, 59.0], 'sd': [5.8, 6.1, 6.2, 6.6], 'color': '#9467BD', 'marker': '^'},
    'MVIC': {'mean': [63.0, 61.2, 59.4, 57.2], 'sd': [6.2, 5.8, 5.1, 4.7], 'color': '#FF7F0E', 'marker': 'D'},
}

# --- Create figure ---
fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
ax.set_facecolor('white')

# --- Plot lines ---
for name, d in data.items():
    ax.errorbar(x, d['mean'], yerr=d['sd'], label=name,
                color=d['color'], marker=d['marker'], markersize=8,
                linewidth=1.5, capsize=4, capthick=1.2,
                markerfacecolor=d['color'], markeredgecolor=d['color'],
                elinewidth=1.0)

# --- Star annotation: MVIC 12min, above error bar cap ---
# Place black star above the upper error bar cap of MVIC at 12min
# Use high zorder to ensure visibility above other plot elements
ax.annotate('*', xy=(3, 57.2 + 4.7 + 0.3), fontsize=22, fontweight='bold',
            color='black', ha='center', va='bottom',
            annotation_clip=False, zorder=100)

# --- Title ---
ax.set_title('图 4-1：不同预激活方式下原地纵跳（CMJ）的表现变化',
             fontsize=14, fontweight='bold', fontproperties=ch_prop, pad=12)

# --- Axes ---
ax.set_xticks(x)
ax.set_xticklabels(x_labels, fontsize=10, fontproperties=ch_prop)
ax.set_ylabel('纵跳高度 (cm)', fontsize=12, fontproperties=ch_prop)
ax.set_ylim(55, 68)
ax.set_yticks(np.arange(55, 69, 1))
ax.tick_params(axis='both', which='major', labelsize=10)
for label in ax.get_yticklabels():
    label.set_fontproperties(en_prop)

# --- No grid, keep all four spines ---
ax.grid(False)
for spine in ax.spines.values():
    spine.set_linewidth(0.8)

# --- Legend (upper right, with frame) ---
legend = ax.legend(loc='upper right', fontsize=10, frameon=True, edgecolor='black',
                   fancybox=False, framealpha=1.0)
legend.get_frame().set_linewidth(0.8)
for text in legend.get_texts():
    text.set_fontproperties(en_prop)

# --- Bottom note ---
fig.text(0.5, 0.01,
         '注：误差棒表示标准差（SD）；* p < 0.05 vs Baseline（Dunnett校正）',
         ha='center', fontsize=9, fontproperties=ch_prop, fontstyle='italic')

plt.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig('/home/user/Teaching_platform/CMJ_Performance_Analysis.png',
            dpi=300, bbox_inches='tight', facecolor='white')
print('Done: CMJ_Performance_Analysis.png saved.')
