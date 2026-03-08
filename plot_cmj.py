import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from matplotlib.font_manager import FontProperties
import platform

# --- 1. 环境配置与字体设置 ---
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
plt.rcParams['axes.unicode_minus'] = False

# 配置中文字体（跨平台兼容）
if platform.system() == 'Windows':
    font_ch = FontProperties(fname="C:/Windows/Fonts/simsun.ttc", size=9)
    font_ch_label = FontProperties(fname="C:/Windows/Fonts/simsun.ttc", size=12)
elif platform.system() == 'Darwin':
    font_ch = FontProperties(fname="/System/Library/Fonts/STHeiti Light.ttc", size=9)
    font_ch_label = FontProperties(fname="/System/Library/Fonts/STHeiti Light.ttc", size=12)
else:
    # Linux: 使用 WenQuanYi Zen Hei（系统已安装）
    import matplotlib.font_manager as fm
    _wqy_path = None
    for f in fm.findSystemFonts():
        if 'wqy-zenhei' in f.lower():
            _wqy_path = f
            break
    if _wqy_path:
        font_ch = FontProperties(fname=_wqy_path, size=9)
        font_ch_label = FontProperties(fname=_wqy_path, size=12)
    else:
        font_ch = FontProperties(size=9)
        font_ch_label = FontProperties(size=12)

# --- 2. 数据准备 ---
x_labels = ['基线', '4分钟', '8分钟', '12分钟']
x = np.arange(len(x_labels))

data = {
    'BAL':  {'mean': [62.5, 63.8, 65.4, 64.2], 'sd': [6.7, 5.9, 5.8, 5.4],  'color': '#1F77B4', 'marker': 'o'},
    'BFR':  {'mean': [62.8, 63.1, 62.9, 62.6], 'sd': [6.4, 6.2, 6.5, 6.3],  'color': '#E41A1C', 'marker': 's'},
    'VRT':  {'mean': [63.2, 62.0, 61.5, 59.0], 'sd': [5.8, 6.1, 6.2, 6.6],  'color': '#9467BD', 'marker': '^'},
    'MVIC': {'mean': [63.0, 61.2, 59.4, 57.2], 'sd': [6.2, 5.8, 5.1, 4.7],  'color': '#FF7F0E', 'marker': 'D'},
}

# --- 3. 创建图形 ---
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
fig.patch.set_facecolor('white')

# --- 4. 核心绘图循环 ---
for label, cfg in data.items():
    ax.errorbar(
        x, cfg['mean'], yerr=cfg['sd'],
        label=label,
        color=cfg['color'],
        marker=cfg['marker'],
        markersize=8,
        linewidth=1.5,
        linestyle='-',
        capsize=5,
        elinewidth=1.2,
        markeredgecolor='white',
        markeredgewidth=0.8
    )

# --- 5. 标注显著性星号 (*) ---
star_x = 3
star_y = 57.2 + 4.7 + 0.3
ax.text(star_x, star_y, '*', ha='center', va='bottom', fontsize=16, color='black')

# --- 6. 坐标轴及样式美化 ---
plt.title('图 4-1：不同预激活方式下原地纵跳（CMJ）的表现变化',
          fontsize=14, fontweight='bold', pad=20, fontproperties=font_ch_label)

ax.set_ylim(55, 68)
ax.set_ylabel('纵跳高度 (cm)', fontsize=12, fontproperties=font_ch_label)

ax.set_xticks(x)
ax.set_xticklabels(x_labels, fontsize=10, fontproperties=font_ch_label)

ax.tick_params(axis='both', which='major', labelsize=10)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(1)
ax.spines['bottom'].set_linewidth(1)

ax.set_facecolor('white')
ax.grid(False)

# --- 7. 图例与底部标注 ---
ax.legend(
    loc='upper right',
    frameon=False,
    prop={'size': 10, 'family': 'serif'},
    handletextpad=0.5
)

plt.figtext(
    0.15, 0.02,
    "注：误差棒表示标准差（SD）；* p < 0.05 vs Baseline（Dunnett校正）",
    fontsize=9, fontproperties=font_ch, ha='left'
)

# --- 8. 输出与保存 ---
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.savefig('/home/user/Teaching_platform/CMJ_Performance_Analysis.png', bbox_inches='tight', dpi=300)
print("高清图片已生成并保存为: CMJ_Performance_Analysis.png")
