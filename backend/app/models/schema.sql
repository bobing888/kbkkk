-- K 线趋势分析系统 - PostgreSQL Schema
-- 创建时间：2026-10-04
-- 设计原则：时序数据 + 索引优化 + A 股特殊规则

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索标的代码

-- 标的表（symbols）
CREATE TABLE symbols (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(20) UNIQUE NOT NULL,         -- 标的代码（如 600519 / AAPL / BTC/USDT）
    name VARCHAR(100) NOT NULL,                -- 标的名称（如 贵州茅台 / Apple / Bitcoin）
    market VARCHAR(10) NOT NULL,               -- 市场：cn / us / crypto / future
    exchange VARCHAR(20),                      -- 交易所（SH / SZ / NASDAQ / Binance）
    is_active BOOLEAN DEFAULT true,
    is_st BOOLEAN DEFAULT false,               -- A 股 ST 标记
    is_limit_20 BOOLEAN DEFAULT false,         -- 注册制 20% 涨跌幅
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_symbols_code ON symbols(code);
CREATE INDEX idx_symbols_market ON symbols(market);
CREATE INDEX idx_symbols_name_trgm ON symbols USING gin(name gin_trgm_ops);

-- K线数据表（klines）- 时序数据，按日期分区
CREATE TABLE klines (
    id BIGSERIAL,
    symbol_code VARCHAR(20) NOT NULL,
    period VARCHAR(10) NOT NULL,               -- 1m / 5m / 15m / 1h / 1d / 1w
    datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(20, 4) NOT NULL,
    amount NUMERIC(20, 4),                     -- 成交额（A 股特有）
    adj_factor NUMERIC(10, 6) DEFAULT 1.0,     -- 复权因子
    is_limit_up BOOLEAN DEFAULT false,
    is_limit_down BOOLEAN DEFAULT false,
    is_suspended BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (symbol_code, period, datetime)
) PARTITION BY RANGE (datetime);

-- 按年分区（A 股数据量大，PostgreSQL 12+ 支持声明式分区）
CREATE TABLE klines_2026 PARTITION OF klines
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE klines_2025 PARTITION OF klines
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE klines_2024 PARTITION OF klines
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE klines_default PARTITION OF klines DEFAULT;

-- 索引：按标的 + 周期 + 时间查询（最常见查询）
CREATE INDEX idx_klines_symbol_period_time ON klines (symbol_code, period, datetime DESC);

-- 索引：按时间查询（全局行情扫描）
CREATE INDEX idx_klines_time ON klines (datetime DESC);

-- 指标数据表（indicators）
CREATE TABLE indicators (
    id BIGSERIAL PRIMARY KEY,
    symbol_code VARCHAR(20) NOT NULL,
    period VARCHAR(10) NOT NULL,
    datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    ma5 NUMERIC(20, 8),
    ma10 NUMERIC(20, 8),
    ma20 NUMERIC(20, 8),
    ma60 NUMERIC(20, 8),
    ma120 NUMERIC(20, 8),
    ma250 NUMERIC(20, 8),
    macd_dif NUMERIC(20, 8),
    macd_dea NUMERIC(20, 8),
    macd_hist NUMERIC(20, 8),
    rsi14 NUMERIC(10, 4),
    boll_upper NUMERIC(20, 8),
    boll_mid NUMERIC(20, 8),
    boll_lower NUMERIC(20, 8),
    kdj_k NUMERIC(10, 4),
    kdj_d NUMERIC(10, 4),
    kdj_j NUMERIC(10, 4),
    obv NUMERIC(20, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (symbol_code, period, datetime)
);

CREATE INDEX idx_indicators_symbol_period_time ON indicators (symbol_code, period, datetime DESC);

-- 信号表（signals）
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_code VARCHAR(20) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,          -- strong_buy / buy / hold / sell / strong_sell
    signal_strength VARCHAR(10) NOT NULL,      -- strong / medium / weak
    confidence NUMERIC(5, 2) NOT NULL,         -- 置信度 0-100
    datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC(20, 8) NOT NULL,
    stop_loss NUMERIC(20, 8),
    take_profit NUMERIC(20, 8),
    reasons JSONB,                             -- 信号来源 JSON 数组：["MA金叉", "MACD底背离"]
    is_executed BOOLEAN DEFAULT false,         -- 是否已执行
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_signals_symbol_time ON signals (symbol_code, datetime DESC);
CREATE INDEX idx_signals_type ON signals (signal_type, datetime DESC);

-- 回测结果表（backtest_results）
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_name VARCHAR(100) NOT NULL,
    symbol_code VARCHAR(20) NOT NULL,
    market VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital NUMERIC(20, 2) NOT NULL,
    final_capital NUMERIC(20, 2) NOT NULL,
    total_return NUMERIC(10, 4),               -- 总收益率
    annual_return NUMERIC(10, 4),              -- 年化收益率
    max_drawdown NUMERIC(10, 4),               -- 最大回撤
    sharpe_ratio NUMERIC(10, 4),               -- 夏普比率
    win_rate NUMERIC(5, 4),                    -- 胜率
    profit_loss_ratio NUMERIC(10, 4),          -- 盈亏比
    total_trades INTEGER,
    parameters JSONB,                          -- 策略参数
    report_url TEXT,                           -- 回测报告 URL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_backtest_strategy ON backtest_results (strategy_name, created_at DESC);
CREATE INDEX idx_backtest_symbol ON backtest_results (symbol_code, start_date DESC);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_symbols_updated_at
    BEFORE UPDATE ON symbols
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE klines IS 'K线时序数据，按年分区';
COMMENT ON TABLE indicators IS '技术指标计算结果';
COMMENT ON TABLE signals IS 'K线分析信号';
COMMENT ON TABLE backtest_results IS '回测结果';
