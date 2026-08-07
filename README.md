# 6v 影视资源库（hao6v.cc 爬虫 + TMDB 补全 + Web 展示）

从 [www.hao6v.cc](https://www.hao6v.cc) 首页 `<p class="bg">` 元素**动态发现**专题分类
（白名单 **21 类**：18 个专题分类：喜剧/动作/爱情/科幻/奇幻/神秘/幻想/恐怖/战争/冒险/惊悚/
剧情/传记/历史/纪录/印度电影/国产电影/欧洲电影，另加主菜单的 **国剧/日韩剧/欧美剧**），
每个类型抓取**前 20 页**。

数据来源约定：

- **hao6v.cc 只提供**：资源名称、详情页链接（仅用于前端“查看原网页”）、磁力链接；
- **TMDB 提供全部详细信息**：简介、海报、年份、演员、总集数、导演、类型、语言、产地。

> 仅用于个人学习研究，请遵守目标站点 robots 协议与相关法律法规；数据版权归原站点与 TMDB 所有。

## 项目结构

```
电影资源/
├── config.py            # 全局配置（数据库、站点、类型、并发、TMDB、日志）
├── schema.sql           # MySQL 建表语句
├── common/
│   ├── logger.py        # 日志：控制台 + data/logs/app.log（轮转）
│   └── db.py            # pymysql 线程级连接与 SQL 辅助
├── spider/
│   ├── parser.py        # 首页分类 / 列表页 / 详情页（磁力）解析
│   └── crawler.py       # 分类动态发现、列表抓取、磁力抓取
├── tmdb/
│   ├── client.py        # TMDB v3 API 封装（限速 + 重试）
│   └── enrich.py        # 批量 TMDB 补全
├── web/
│   ├── app.py           # Flask 应用（列表/多条件查询/详情）
│   ├── templates/       # Jinja2 模板
│   └── static/          # 样式
├── run_crawler.py       # 爬虫一键入口
├── run_web.py           # Web 启动入口
└── data/logs/           # 日志目录（自动创建）
```

## 数据库设计

- `categories`：类型（站点菜单 32 个分类）
- `resources`：影视资源（名称、磁力 JSON 来自 hao6v；其余字段全部来自 TMDB）
- `resource_categories`：资源与类型的多对多关联（同一部片可属于多个分类）

## 使用步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 抓取数据（全流程）

```bash
python run_crawler.py
```

默认每个类型抓取前 20 页（每页约 25 条），之后抓取所有详情页磁力链接，
最后用 TMDB 补全简介/海报/演员/集数等信息。整个过程支持断点续跑
（重复执行只会补充未处理的数据），并输出详细日志到 `data/logs/app.log`。

常用参数：

```bash
python run_crawler.py --reset              # 清空全部数据后重新抓取
python run_crawler.py --steps lists details   # 只跑指定步骤
python run_crawler.py --pages 10              # 每个类型只抓 10 页
python run_crawler.py --category dongzuo --pages 1 --limit 10   # 单类型小规模调试
python run_crawler.py --steps tmdb            # 只做 TMDB 补全
```

### 3. 启动 Web

```bash
python run_web.py --port 5000
```

浏览器访问 <http://127.0.0.1:5000>，支持：

- 首页海报卡片列表，分页浏览；
- 按钮式筛选：类型 / 年份，配合片名、演员关键词组合查询；
- 详情页展示海报、简介、年份、导演、演员、总集数、类型/语言/产地、磁力链接（一键复制）
  与 hao6v 原详情页链接。

## 部署到飞牛 NAS（Docker + 青龙面板定时更新）

### 1. 上传项目

把整个项目目录上传到 NAS，例如：

```text
/vol1/docker/hao6v/
├── config.py
├── run_crawler.py
├── run_web.py
└── deploy/
    ├── ql_update.py         # 青龙定时任务入口
    ├── Dockerfile           # Web 服务镜像
    └── docker-compose.yml   # 一键编排（青龙 + Web）
```

### 2. 用 Compose 启动

在 fnOS 的 Docker（或 SSH）中进入 `deploy` 目录执行：

```bash
docker compose up -d --build
```

启动后：

- 青龙面板：http://NAS_IP:5700（首次默认账号 `admin` / `adminadmin`，登录后强制改密）
- Web 展示：http://NAS_IP:5000

> 前提：NAS 需要能访问 MySQL `10.1.0.4:8004`（同一局域网即可）以及外网
> （hao6v.cc 与 api.themoviedb.org）。如数据库信息不同，在 Compose 的环境变量
> 或 `config.py` 中修改。

### 3. 配置青龙定时任务

青龙面板 → 定时任务 → 新建任务：

- 名称：`hao6v 影视更新`
- 命令：

```bash
cd /ql/scripts/hao6v_movie && pip3 install -r requirements.txt -q && python3 deploy/ql_update.py
```

- 定时规则（cron）：`0 3 * * *`（每天凌晨 3 点，可按需修改）

也可以先在面板“依赖管理 → Python3”里添加 `requests / beautifulsoup4 / pymysql`，
再省略命令中的 pip 安装部分。

任务执行流程（全部为增量更新，不会重复抓取已处理的数据，也不会清空库）：

1. 从首页动态发现 21 个分类（18 专题 + 国剧/日韩剧/欧美剧）并建表；
2. 每个类型抓取前 20 页列表（新条目入库）；
3. 抓取新详情页的磁力链接；
4. TMDB 补全新资源（简介/海报/年份/演员/集数/评分等）；
5. 补填历史资源缺失的评分。

运行日志可在青龙面板“日志”中查看，也会写入项目 `data/logs/app.log`。

### 4. 手动立即执行一次

在青龙任务列表中点击“运行”，首次执行耗时约 30–50 分钟（视新增数据量而定）；
后续定时执行通常几分钟内完成。

## 配置修改

数据库、TMDB Key、类型列表、并发与限速等均在 `config.py` 中集中配置。
`config.py` 含敏感信息（数据库密码、API Key），**不会提交到 Git**；
克隆项目后先执行 `copy config.example.py config.py` 并填入自己的配置，
或直接设置环境变量 `HAO6V_DB_*` / `HAO6V_TMDB_API_KEY`。

| 配置项 | 说明 |
| --- | --- |
| `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` | MySQL 连接信息 |
| `DEFAULT_PAGES_PER_CATEGORY` | 每个类型抓取前 N 页（默认 20） |
| `ALLOWED_CATEGORY_SLUGS` | 分类白名单（18 专题 + 国剧/日韩剧/欧美剧） |
| `LIST_WORKERS / DETAIL_WORKERS / TMDB_WORKERS` | 各阶段并发线程数 |
| `LIST_DELAY_RANGE / DETAIL_DELAY_RANGE / TMDB_DELAY` | 请求间隔（礼貌限速） |
| `TMDB_API_KEY` | TMDB v3 API Key |
