# A股盘前短线选股 Skill

该 Skill 使用 AKShare 采集 A 股市场、板块、涨跌停和个股行情事实，再由 `SKILL.md` 完成主线层级、生命周期、观察池和竞价条件判断。

## 初始化

Python 需为 3.9 及以上。首次安装依赖属于联网和环境变更操作，必须先获得用户确认：

```powershell
python -m pip install -r requirements.txt
```

依赖固定为 `akshare==1.18.64`，不得在执行选股时自动升级。

## 使用

```powershell
python scripts/market_snapshot.py --mode health
python scripts/market_snapshot.py --mode post_close --date 2026-06-22
python scripts/market_snapshot.py --mode auction --symbols 002378 600160
```

默认缓存位于系统临时目录的 `codex-premarket-cache`。`auction` 必须读取最近一个 `complete` 的盘后缓存。

## 数据边界

- AKShare 是行情和板块趋势主源，接口可能随上游网页变化而失效。
- 智兔仅为可选备用源；只从环境变量 `ZHITU_API_TOKEN` 读取，任何文档、脚本和日志均不得保存或回显真实 Token。
- 配置 Token 后，AKShare 的指数、全市场行情或候选股日线请求失败时自动回退到智兔；板块历史与涨跌停池没有智兔等价接口，失败时仍必须降级。
- health 会同时检查固定版本和真实指数接口可用性；依赖可导入但上游接口不可达时返回 ailed。
- 公告、监管、减持、立案与澄清必须继续使用巨潮资讯或交易所官方来源核验。
- 脚本只输出事实和确定性指标，不输出股票推荐或主观评分。