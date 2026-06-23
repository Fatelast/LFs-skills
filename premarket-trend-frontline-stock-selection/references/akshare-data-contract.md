# AKShare 数据契约

## 读取时机

执行数据采集、诊断数据缺失或调整接口映射时读取本文件。主线判断规则仍以 `SKILL.md` 为准。

## 数据源职责

| 数据 | 主源 | 可选备用 | 阻断规则 |
|---|---|---|---|
| 指数、全市场行情、板块、涨跌股池、个股 OHLCV | AKShare | 智兔行情接口 | 两者均失败时不生成正式观察池 |
| 板块近 5/10/20 日趋势 | AKShare 行业/概念历史行情 | 无 | 缺失时只给预备方向 |
| ST、解禁、业绩、财务 | AKShare 可作风险线索 | 智兔相关接口 | 不能替代官方公告 |
| 公告、监管、减持、立案、澄清 | 巨潮资讯、交易所 | 无 | 未核验时 `risk.status = "not_checked"` |

AKShare 多数东方财富接口与东方财富直连并非独立数据源，不得写成“已完成跨源核验”。

## AKShare 接口映射

- 全市场实时：`stock_zh_a_spot_em()`。
- 主要指数实时：`stock_zh_index_spot_em(symbol="沪深重要指数")`。
- 行业：`stock_board_industry_name_em()`、`stock_board_industry_hist_em()`、`stock_board_industry_cons_em()`。
- 概念：`stock_board_concept_name_em()`、`stock_board_concept_hist_em()`、`stock_board_concept_cons_em()`。
- 涨跌股池：`stock_zt_pool_em()`、`stock_zt_pool_dtgc_em()`、`stock_zt_pool_previous_em()`、`stock_zt_pool_strong_em()`、`stock_zt_pool_zbgc_em()`。
- 个股日线：`stock_zh_a_hist(period="daily", adjust="qfq")`。
- 分钟线需要时使用 `stock_zh_a_hist_min_em()`，不得把延迟数据写成竞价实时确认。

## CLI

```text
python scripts/market_snapshot.py --mode health
python scripts/market_snapshot.py --mode post_close [--date YYYY-MM-DD] [--symbols CODE ...]
python scripts/market_snapshot.py --mode auction [--symbols CODE ...]
```

`post_close` 仅在 17:10 后且最新板块历史日期等于目标交易日、全市场有效覆盖率不低于 90%、行业和概念历史均完整时返回 `complete`。15:00—17:10 只能返回 `partial`。

`auction` 在 9:25 前返回 `failed`；9:25 后必须读取最近完整盘后缓存，再补充实时指数、市场宽度和候选股行情。

## JSON 契约

根字段固定为 `meta`、`market`、`boards`、`stocks`、`risk`。

- `meta.completeness`：`complete | partial | failed`。
- `market.breadth`：`total`、`valid`、`up`、`down`、`flat`、`coverage`。
- `boards`：分别输出 `industries` 和 `concepts`；每个板块包含历史数据、成分股以及 5/10/20 日收益、20 日上涨天数、近 5 日/20 日平均成交额比值、距离 20 日高点。
- `stocks`：候选股实时行情、历史行情和 MA5/MA10。
- `risk.status`：第一阶段固定为 `not_checked`，正式观察池前必须由官方来源升级风险核验状态。

脚本不得输出百分制主线评分、资金身份或股票推荐。

## 缓存与安全

- 默认缓存：系统临时目录 `codex-premarket-cache/YYYY-MM-DD.json`。
- 只有 `post_close` 快照写入交易日缓存；`auction` 不覆盖盘后缓存。
- 智兔 Token 只允许通过 `ZHITU_API_TOKEN` 提供，URL、异常和日志必须脱敏；不得将真实 Token 写入 Skill、测试、缓存或终端输出。
- meta.providers 记录实际使用的数据源；发生成功回退时，主源失败原因写入 meta.warnings，不把已恢复请求误记为硬错误。
- 401/402/429、超时、空 DataFrame、字段缺失和日期不一致都必须转为结构化错误并降低完整性。