import React from 'react';

const App = () => {
  // 数据配置
  const labels = ["基线", "4分钟", "8分钟", "12分钟"];
  const yRange = [55, 68];
  const data = {
    BAL: {
      name: "BAL",
      values: [62.5, 63.8, 65.4, 64.2],
      lineStyle: "solid",
      marker: "circle",
    },
    BFR: {
      name: "BFR",
      values: [62.8, 63.1, 62.9, 62.6],
      lineStyle: "dashed",
      marker: "square",
    },
    VRT: {
      name: "VRT",
      values: [63.2, 62.0, 61.5, 59.0],
      lineStyle: "dotted",
      marker: "triangle",
    },
    MVIC: {
      name: "MVIC",
      values: [63.0, 61.2, 59.4, 57.2],
      lineStyle: "dashdot",
      marker: "diamond",
    },
  };

  // 画布尺寸
  const width = 800;
  const height = 600;
  const padding = { top: 80, right: 150, bottom: 100, left: 80 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // 比例转换函数
  const getX = (index) => padding.left + (index * (chartWidth / (labels.length - 1)));
  const getY = (val) => padding.top + chartHeight - ((val - yRange[0]) / (yRange[1] - yRange[0]) * chartHeight);

  // 标记点形状渲染
  const renderMarker = (type, cx, cy) => {
    const size = 6;
    switch (type) {
      case 'circle': return <circle cx={cx} cy={cy} r={size} fill="black" />;
      case 'square': return <rect x={cx - size} y={cy - size} width={size * 2} height={size * 2} fill="black" />;
      case 'triangle': return <path d={`M ${cx} ${cy - size - 2} L ${cx + size + 1} ${cy + size} L ${cx - size - 1} ${cy + size} Z`} fill="black" />;
      case 'diamond': return <path d={`M ${cx} ${cy - size - 2} L ${cx + size + 2} ${cy} L ${cx} ${cy + size + 2} L ${cx - size - 2} ${cy} Z`} fill="black" />;
      default: return null;
    }
  };

  // 线条样式
  const getStrokeDashArray = (style) => {
    switch (style) {
      case 'dashed': return "8, 6";
      case 'dotted': return "2, 3";
      case 'dashdot': return "12, 4, 2, 4";
      default: return "none";
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-white p-8 font-serif">
      <div className="relative bg-white shadow-sm p-4 border border-gray-50">
        {/* 标题 */}
        <h1 className="text-xl font-bold text-center mb-6 text-black">
          图 4-1：不同预激活方式下原地纵跳（CMJ）的表现变化
        </h1>

        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* Y 轴刻度和标签 */}
          <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + chartHeight} stroke="black" strokeWidth="1.5" />
          {[55, 60, 65, 68].map((tick) => (
            <g key={tick}>
              <line x1={padding.left - 5} y1={getY(tick)} x2={padding.left} y2={getY(tick)} stroke="black" strokeWidth="1" />
              <text x={padding.left - 10} y={getY(tick)} textAnchor="end" alignmentBaseline="middle" className="text-sm font-serif">{tick}</text>
            </g>
          ))}
          <text
            transform={`translate(${padding.left - 50}, ${padding.top + chartHeight / 2}) rotate(-90)`}
            textAnchor="middle"
            className="text-base font-serif font-semibold"
          >
            纵跳高度 (cm)
          </text>

          {/* X 轴刻度和标签 */}
          <line x1={padding.left} y1={padding.top + chartHeight} x2={padding.left + chartWidth} y2={padding.top + chartHeight} stroke="black" strokeWidth="1.5" />
          {labels.map((label, i) => (
            <g key={label}>
              <line x1={getX(i)} y1={padding.top + chartHeight} x2={getX(i)} y2={padding.top + chartHeight + 5} stroke="black" strokeWidth="1" />
              <text x={getX(i)} y={padding.top + chartHeight + 25} textAnchor="middle" className="text-sm font-serif">{label}</text>
            </g>
          ))}

          {/* 绘制数据线 */}
          {Object.entries(data).map(([key, config]) => {
            const points = config.values.map((v, i) => `${getX(i)},${getY(v)}`).join(' ');
            return (
              <g key={key}>
                <polyline
                  points={points}
                  fill="none"
                  stroke="black"
                  strokeWidth="1.5"
                  strokeDasharray={getStrokeDashArray(config.lineStyle)}
                />
                {config.values.map((v, i) => (
                  <g key={`${key}-${i}`}>
                    {renderMarker(config.marker, getX(i), getY(v))}
                  </g>
                ))}
              </g>
            );
          })}

          {/* 统计学星号标注 - MVIC 12分钟点 */}
          <text
            x={getX(3)}
            y={getY(57.2) - 15}
            textAnchor="middle"
            className="text-lg font-bold"
          >
            *
          </text>

          {/* 图例 (Legend) */}
          <g transform={`translate(${padding.left + chartWidth + 20}, ${padding.top})`}>
            {Object.entries(data).map(([key, config], i) => (
              <g key={key} transform={`translate(0, ${i * 30})`}>
                <line x1="0" y1="0" x2="30" y2="0" stroke="black" strokeWidth="1.5" strokeDasharray={getStrokeDashArray(config.lineStyle)} />
                {renderMarker(config.marker, 15, 0)}
                <text x="40" y="5" className="text-sm font-serif">{config.name}</text>
              </g>
            ))}
          </g>

          {/* 底部说明文字 */}
          <text
            x={padding.left}
            y={height - 20}
            className="text-xs italic font-serif"
            fill="#333"
          >
            注：* p &lt; 0.05 vs Baseline（Dunnett校正）
          </text>
        </svg>
      </div>

      <div className="mt-8 max-w-2xl text-gray-500 text-sm leading-relaxed text-center">
        该图表根据顶刊出版规范设计：无冗余背景网格、高对比度黑白设计、区分明显的线型和几何标记、标准衬线字体排版。
      </div>
    </div>
  );
};

export default App;
