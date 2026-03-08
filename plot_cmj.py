import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# 设置全局字体为 Times New Roman (学术期刊常用)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# --- 1. 数据录入 ---
time_points = ['Baseline', '4 min', '8 min', '12 min']
x = np.arange(len(time_points))

# 格式: { 条件: {'mean': [均值列表], 'sd': [标准差列表], 'color': 颜色, 'marker': 形状} }
data = {
    'BAL':  {'mean': [62.5, 63.8, 65.4, 64.2], 'sd': [6.7, 5.9, 5.8, 5.4],  'color': '#2166AC', 'marker': 'o'},
    'BFR':  {'mean': [62.8, 63.1, 62.9, 62.6], 'sd': [6.4, 6.2, 6.5, 6.3],  'color': '#4DAF4A', 'marker': 's'},
    'VRT':  {'mean': [63.2, 62.0, 61.5, 59.0], 'sd': [5.8, 6.1, 6.2, 6.6],  'color': '#FF7F00', 'marker': '^'},
    'MVIC': {'mean': [63.0, 61.2, 59.4, 57.2], 'sd': [6.2, 5.8, 5.1, 4.7],  'color': '#E31A1C', 'marker': 'D'}
}

# --- 2. 创建画布 ---
fig, ax = plt.subplots(figsize=(7, 5.5), dpi=300)
fig.patch.set_facecolor('white')

# --- 3. 循环绘图 ---
for label, cfg in data.items():
    ax.errorbar(
        x, cfg['mean'], yerr=cfg['sd'],
        label=label,
        color=cfg['color'],
        marker=cfg['marker'],
        markersize=8,
        linewidth=1.5,
        linestyle='-',
        capsize=4,
        elinewidth=1.2,
        markeredgecolor='white',
        markeredgewidth=0.8
    )

# --- 4. 标注显著性 (MVIC 12min) ---
star_x = 3
star_y = data['MVIC']['mean'][3] + data['MVIC']['sd'][3] + 0.5
ax.text(star_x, star_y, '*', ha='center', va='bottom', fontsize=14, color='#E31A1C', fontweight='bold')

# --- 5. 坐标轴及样式美化 ---
ax.set_ylim(55, 68)
ax.set_xticks(x)
ax.set_xticklabels(time_points, fontsize=10)
ax.set_yticks(np.arange(55, 69, 2))
ax.tick_params(axis='both', which='major', labelsize=10)
ax.set_ylabel('CMJ Height (cm)', fontsize=12, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# --- 6. 图例与图注 ---
ax.legend(
    loc='upper right',
    frameon=False,
    prop={'size': 9, 'family': 'serif'}
)

plt.figtext(
    0.15, 0.02,
    "Note: Error bars = SD; * p < 0.05 vs Baseline (Dunnett)",
    fontsize=9, ha='left'
)

plt.tight_layout(rect=[0, 0.05, 1, 0.95])

# --- 7. 输出保存 ---
plt.savefig('CMJ_Performance_Analysis.png', bbox_inches='tight', dpi=300)
print("图片已生成并保存为 CMJ_Performance_Analysis.png (300 DPI)")
