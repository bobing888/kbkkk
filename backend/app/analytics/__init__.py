"""Analytics package — 高级量化指标

来源：bobing888/ai-trader (MIT/Apache-2.0) 复盘后谨慎复用
原始项目：https://github.com/bobing888/ai-trader
原始路径：backend/app/analytics/

复用的具体模块（全部纯 numpy，零外部依赖）：
- trend.py       — ADX / MACD / SMA / 多指标共振 / 信号方向
- statistical.py — Hurst 指数 / 分形维数 / Shannon 熵 / RSI 分数
- volatility.py  — ATR / 波动率分位数

⚠️ 复用规则（kline-system SPEC.md）：
1. 保留原文件的所有 docstring（作者署名）
2. 不与 kline-system/services/indicators.py 的同名函数冲突
3. 添加单元测试覆盖（与 ai-trader 相同测试用例）
4. 任何修改必须更新此 header
"""
