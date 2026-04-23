# Java-Code-Reviewer-Agent 规范文档

## 1. 项目概述

### 1.1 项目简介

Java-Code-Reviewer-Agent 是一个基于 LangGraph 的自动化代码审查系统，根据阿里巴巴 Java 开发规范（华山版/泰山版）对 Java Pull Requests 进行审查。

### 1.2 核心功能

| 模式 | 说明 |
|------|------|
| `audit_only` | 生成 Markdown 格式的代码审查报告，列出问题并按严重程度排序 |
| `autofix` | 生成代码修复，创建新分支并推送补丁 |

### 1.3 支持平台

- **GitHub**: 支持 Pull Request 审查
- **GitLab**: 支持 Merge Request 审查

---

## 2. 系统架构

### 2.1 LangGraph 管道流程

```
input_node → crawler_node → context_retriever_node → reviewer_node → option_router → report_node/patch_node
```

### 2.2 节点职责

| 节点 | 职责 |
|------|------|
| `input_node` | 验证 PR URL 格式，检查作用域白名单 |
| `crawler_node` | 通过 GitHub/GitLab API 获取 PR 元数据和 diff |
| `context_retriever_node` | 基于 RAG 检索相关阿里巴巴规范 |
| `reviewer_node` | 调用 LLM 审查代码，输出 JSON 格式问题列表 |
| `option_router` | 根据模式路由到 report_node 或 patch_node |
| `report_node` | 生成 Markdown 格式审查报告 |
| `patch_node` | 生成修复代码，创建提交并推送 |

### 2.3 条件边逻辑

```python
# input → crawler: validated == True
# crawler → context_retriever: diff_content exists and no error
# context_retriever → reviewer: retrieved_context exists and no error
# reviewer → option_router: (always)
# option_router → report/patch: mode == "autofix" ? "patch" : "report"
```

---

## 3. 状态管理

### 3.1 ReviewMode 枚举

```python
class ReviewMode(str, Enum):
    AUDIT_ONLY = "audit_only"
    AUTOFIX = "autofix"
```

### 3.2 Severity 枚举

```python
class Severity(str, Enum):
    BLOCKER = "blocker"    # 强制性问题
    CRITICAL = "critical"  # 严重问题
    WARNING = "warning"    # 警告
    INFO = "info"          # 信息
```

优先级顺序：`BLOCKER > CRITICAL > WARNING > INFO`

### 3.3 Issue TypedDict

```python
class Issue(TypedDict):
    severity: Severity
    rule_id: str           # 规则 ID，如 "NAMING-001"
    file_path: str         # 文件路径
    line_number: int        # 行号
    message: str           # 问题描述
    code_snippet: str      # 问题代码
    suggestion: NotRequired[str]  # 修复建议（autofix 模式）
```

### 3.4 ReviewState TypedDict

```python
class ReviewState(TypedDict):
    # 输入
    pr_url: str
    mode: ReviewMode

    # 验证后的元数据
    validated: bool
    validation_error: NotRequired[str]

    # PR 标识
    provider: Literal["github", "gitlab"]
    repo_owner: str
    repo_name: str
    pr_number: int

    # PR 内容
    diff_content: str
    changed_files: list[str]
    pr_title: str
    pr_description: str

    # RAG 上下文
    retrieved_context: dict[str, str]

    # 审查结果
    issues: list[Issue]

    # 路由
    route_decision: Literal["report", "patch"]

    # 输出
    markdown_report: str
    patch_files: NotRequired[dict[str, str]]
    patch_commit_sha: NotRequired[str]
    patch_error: NotRequired[str]

    # 错误处理
    error: NotRequired[str]
```

---

## 4. 核心模块

### 4.1 目录结构

```
src/java_code_reviewer/
├── main.py                    # 入口点，LangGraph 编译和执行
├── config.py                  # 配置管理（单例模式）
├── agents/
│   ├── base.py               # PRAgent 抽象基类
│   ├── github_agent.py       # GitHub PR 操作
│   └── gitlab_agent.py       # GitLab MR 操作
├── state/
│   └── review_state.py       # 状态定义
├── nodes/
│   ├── input_node.py         # URL 验证
│   ├── crawler_node.py       # 获取 PR 元数据
│   ├── context_retriever.py  # RAG 检索
│   ├── reviewer_node.py     # LLM 审查
│   ├── option_router.py      # 路由决策
│   ├── report_node.py        # 生成报告
│   └── patch_node.py         # 生成补丁
├── rag/
│   ├── alibaba_standards.py  # 阿里巴巴规范（19 条规则）
│   ├── knowledge_base.py    # FAISS 向量存储
│   └── retriever.py          # 检索器
├── llm/
│   ├── client.py             # LLM 客户端
│   └── prompts.py            # 提示词模板
├── git_ops/
│   └── git_manager.py        # Git 操作
└── utils/
    ├── diff_parser.py        # Diff 解析器
    └── severity.py           # 严重程度工具
```

### 4.2 agents/ - API 代理

**base.py**
```python
@dataclass
class PRMetadata:
    repo_owner: str
    repo_name: str
    pr_number: int
    title: str
    description: str
    diff_content: str
    changed_files: list[str]
    base_branch: str
    head_branch: str

class PRAgent(ABC):
    @abstractmethod
    def fetch_pr_metadata(self, repo_owner, repo_name, pr_number) -> PRMetadata

    @abstractmethod
    def validate_token(self) -> bool
```

**github_agent.py**
- 使用 `PyGithub` 库
- 通过 `pr.get_diff()` 和 `pr.get_files()` 获取数据

**gitlab_agent.py**
- 使用 `python-gitlab` 库
- 通过 `mr.changes` 获取变更

### 4.3 nodes/ - 管道节点

| 节点文件 | 关键函数 |
|----------|----------|
| `input_node.py` | `parse_pr_url()`, `check_scope_limit()`, `input_node()` |
| `crawler_node.py` | `crawler_node()` - 选择 Agent 并获取 PR 元数据 |
| `context_retriever_node.py` | `context_retriever_node()` - 检索相关规范上下文 |
| `reviewer_node.py` | `reviewer_node()` - 调用 LLM 审查代码 |
| `option_router.py` | `option_router_node()` - 路由决策 |
| `report_node.py` | `report_node()` - 生成 Markdown 报告 |
| `patch_node.py` | `patch_node()` - 生成并推送补丁 |

### 4.4 rag/ - RAG 系统

**alibaba_standards.py**
- 定义 19 条阿里巴巴代码规范
- 6 大类别：命名、异常、并发、集合、SQL、面向对象

**knowledge_base.py**
```python
class KnowledgeBase:
    def build_index(self) -> None
    def similarity_search(self, query: str, top_k: int = 5) -> list[AlibabaStandard]
```

**retriever.py**
```python
class Retriever:
    def retrieve_context(self, filepath: str, diff_content: str) -> Optional[str]
    def _extract_symbols(self, filepath: str, diff_content: str) -> list[str]
```

### 4.5 llm/ - LLM 集成

**client.py**
```python
class LLMClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None)
    def invoke(self, messages: list[dict]) -> str
```

支持 OpenAI（默认）和 Anthropic，通过 LangChain 实现。

**prompts.py**
- `SYSTEM_PROMPT`: 系统角色定义
- `REVIEW_PROMPT`: 代码审查提示词
- `PATCH_PROMPT`: 补丁生成提示词

### 4.6 git_ops/ - Git 操作

**git_manager.py**
```python
class GitManager:
    def clone_repo(self, repo_url: str, branch: Optional[str] = None, target_dir: Optional[str] = None) -> str
    def create_commit(self, repo_owner: str, repo_name: str, branch_name: str, patch_files: dict[str, str], message: str) -> str
    def apply_patch(self, repo_dir: str, patch_content: str) -> None
```

使用 `GitPython` 库实现。

---

## 5. 阿里巴巴代码规范

### 5.1 规则总览

共 19 条规则，覆盖 6 大类别。

### 5.2 规则详情

#### 命名规范 (Naming)

| 规则 ID | 标题 | 严重程度 |
|---------|------|----------|
| NAMING-001 | 类名使用 UpperCamelCase | critical |
| NAMING-002 | 方法名使用 lowerCamelCase | critical |
| NAMING-003 | 常量命名全部大写 | blocker |
| NAMING-004 | POJO 类布尔变量不加 is 前缀 | critical |

#### 异常处理 (Exception)

| 规则 ID | 标题 | 严重程度 |
|---------|------|----------|
| EXCEPTION-001 | 异常不能被吞掉 | blocker |
| EXCEPTION-002 | 不要捕获 RuntimeException | warning |
| EXCEPTION-003 | finally 块不能 return | blocker |
| EXCEPTION-004 | 自定义异常要提供 cause | critical |

#### 并发编程 (Concurrency)

| 规则 ID | 标题 | 严重程度 |
|---------|------|----------|
| CONCURRENCY-001 | 并发修改同一对象要加锁 | blocker |
| CONCURRENCY-002 | ThreadLocal 要清理 | critical |
| CONCURRENCY-003 | 禁止使用 Executors 创建线程池 | blocker |

#### 集合框架 (Collection)

| 规则 ID | 标题 | 严重程度 |
|---------|------|----------|
| COLLECTION-001 | ArrayList 删除元素要使用 Iterator | critical |
| COLLECTION-002 | 集合初始化要指定大小 | warning |
| COLLECTION-003 | 不要使用 size()==0 判断集合为空 | warning |

#### SQL 规范 (SQL)

| 规则 ID | 标题 | 严重程度 |
|---------|------|----------|
| SQL-001 | 不要使用 count(列名) 判断是否存在 | critical |
| SQL-002 | SQL 语句不要用 * 作为返回列 | warning |

#### 面向对象 (OOP)

| 规则 ID | 标题 | 严重程度 |
|---------|------|----------|
| OOP-001 | 外部依赖必须依赖接口 | critical |
| OOP-002 | 覆写方法必须加 @Override | critical |

### 5.3 辅助函数

```python
def get_all_rules() -> list[AlibabaStandard]
def get_rules_by_category(category: str) -> list[AlibabaStandard]
def get_rules_by_severity(severity: RuleSeverity) -> list[AlibabaStandard]
```

---

## 6. 配置说明

### 6.1 config.yaml

```yaml
github:
  token_env: GITHUB_TOKEN
  api_url: https://api.github.com

gitlab:
  token_env: GITLAB_TOKEN
  api_url: https://gitlab.com/api/v4

llm:
  provider: openai
  model: gpt-4o
  temperature: 0
  max_tokens: 4096

review:
  max_files: 50
  max_context_lines: 100

git:
  clone_depth: 1
  branch_prefix: java-reviewer/

rag:
  vector_store: faiss
  embedding_model: text-embedding-3-small
  top_k: 5
```

### 6.2 环境变量

| 变量名 | 说明 | 来源 |
|--------|------|------|
| `GITHUB_TOKEN` | GitHub 访问令牌 | github.token_env |
| `GITLAB_TOKEN` | GitLab 访问令牌 | gitlab.token_env |
| `LLM_PROVIDER` | LLM 提供商 (openai/anthropic) | llm.provider |
| `LLM_API_KEY` | LLM API 密钥 | - |
| `LLM_MODEL` | LLM 模型名称 | llm.model |
| `LLM_BASE_URL` | LLM API 基础 URL | - |
| `SCOPE_LIMIT` | 允许审查的范围白名单（逗号分隔） | - |

### 6.3 配置优先级

1. 环境变量 > config.yaml
2. 硬编码默认值

---

## 7. 快速开始

### 7.1 安装依赖

```bash
pip install -r requirements.txt
```

### 7.2 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
export GITHUB_TOKEN="your-github-token"
export LLM_API_KEY="your-openai-api-key"
```

### 7.3 运行审查

**audit_only 模式（生成报告）**

```python
from java_code_reviewer.main import run_review

result = run_review(
    "https://github.com/org/repo/pull/123",
    mode="audit_only"
)

print(result["markdown_report"])
```

**autofix 模式（生成修复并推送）**

```python
from java_code_reviewer.main import run_review

result = run_review(
    "https://github.com/org/repo/pull/123",
    mode="autofix"
)

print(f"修复分支: {result.get('patch_commit_sha')}")
```

### 7.4 命令行测试

```bash
# 运行所有测试
pytest tests/

# 运行单个测试
pytest tests/test_diff_parser.py -v
```

---

## 8. 附录

### 8.1 依赖列表

```
langgraph>=0.0.20
langchain>=0.1.0
langchain-openai>=0.0.2
PyGithub>=2.1.1
python-gitlab>=4.0.0
GitPython>=3.1.40
faiss-cpu>=1.7.4
pydantic>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
```

### 8.2 严重程度排序

报告中问题按以下顺序排序：

1. **[BLOCKER]** - 强制性问题，必须修复
2. **[CRITICAL]** - 严重问题，强烈建议修复
3. **[WARNING]** - 警告，参考改进
4. **[INFO]** - 信息性建议

### 8.3 入口函数

```python
def run_review(pr_url: str, mode: Literal["audit_only", "autofix"] = "audit_only") -> ReviewState
```

返回完整的 `ReviewState`，包含审查结果或补丁信息。
