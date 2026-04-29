"""Alibaba Java development standards (华山版/泰山版) rules."""

from typing import Literal, Optional

RuleSeverity = Literal["blocker", "critical", "warning", "info"]
RuleLevel = Literal["强制", "推荐", "参考"]


SEVERITY_TO_LEVEL: dict[str, RuleLevel] = {
    "blocker": "强制",
    "critical": "推荐",
    "warning": "参考",
    "info": "参考",
}


class AlibabaStandard:
    """A single Alibaba Java development standard rule."""

    def __init__(
        self,
        rule_id: str,
        title: str,
        category: str,
        severity: RuleSeverity,
        description: str,
        examples: list[str],
        keywords: list[str],
        source: str = "Alibaba Java Development Manual",
        version: str = "华山版/泰山版",
        section: str = "",
        level: Optional[RuleLevel] = None,
        detection_patterns: Optional[list[str]] = None,
    ):
        self.rule_id = rule_id
        self.title = title
        self.category = category
        self.severity = severity
        self.description = description
        self.examples = examples
        self.keywords = keywords
        self.source = source
        self.version = version
        self.section = section or category
        self.level = level or SEVERITY_TO_LEVEL[severity]
        self.detection_patterns = detection_patterns or keywords


ALIBABA_STANDARDS: dict[str, AlibabaStandard] = {
    # Naming Conventions (命名风格)
    "NAMING-001": AlibabaStandard(
        rule_id="NAMING-001",
        title="类名使用UpperCamelCase",
        category="Naming",
        severity="critical",
        description="类名、接口名使用 UpperCamelCase 风格，正则匹配 [A-Z][a-zA-Z0-9]*",
        examples=["ProductService", "UserManager", "OrderController"],
        keywords=["class", "interface", "Abstract", "Exception"],
    ),
    "NAMING-002": AlibabaStandard(
        rule_id="NAMING-002",
        title="方法名使用lowerCamelCase",
        category="Naming",
        severity="critical",
        description="方法名、参数名、变量名使用 lowerCamelCase 风格，正则匹配 [a-z][a-zA-Z0-9]*",
        examples=["getUserById", "calculateTotal", "setOrderStatus"],
        keywords=["public", "private", "protected", "void", "return"],
    ),
    "NAMING-003": AlibabaStandard(
        rule_id="NAMING-003",
        title="常量命名全部大写",
        category="Naming",
        severity="blocker",
        description="常量命名全部大写，单词间用下划线分隔，正则匹配 [A-Z][A-Z0-9_]*",
        examples=["MAX_SIZE", "DEFAULT_TIMEOUT", "ORDER_STATUS_PENDING"],
        keywords=["static", "final", "const"],
        detection_patterns=[r"static\s+final", r"final\s+\w+\s+[a-z][A-Za-z0-9]*"],
    ),
    "NAMING-004": AlibabaStandard(
        rule_id="NAMING-004",
        title="POJO类布尔变量不加is前缀",
        category="Naming",
        severity="critical",
        description="POJO类中的布尔属性不要加 is 前缀，否则部分框架解析会引起序列化错误",
        examples=["private Boolean deleted;", "private boolean active;"],
        keywords=["private", "boolean", "Boolean", "is"],
        detection_patterns=[r"\b(?:boolean|Boolean)\s+is[A-Z]\w*"],
    ),
    # Exception Handling (异常处理)
    "EXCEPTION-001": AlibabaStandard(
        rule_id="EXCEPTION-001",
        title="异常不能被吞掉",
        category="Exception",
        severity="blocker",
        description="异常不能被吞掉（catch后不记录也不抛出），catch块必须记录日志或抛出",
        examples=["log.error('error', e); throw new RuntimeException(e);"],
        keywords=["catch", "Exception", "e.printStackTrace", "throw"],
        detection_patterns=[r"catch\s*\([^)]*Exception[^)]*\)\s*\{\s*\}", r"catch\s*\([^)]*\)\s*\{[^}]*(?<!log\.error)(?<!throw)\}"],
    ),
    "EXCEPTION-002": AlibabaStandard(
        rule_id="EXCEPTION-002",
        title="不要捕获RuntimeException",
        category="Exception",
        severity="warning",
        description="不要用catch捕获RuntimeException，应该使用具体异常类型或让RuntimeException传播",
        examples=["catch (NullPointerException e)", "catch (IllegalArgumentException e)"],
        keywords=["catch", "RuntimeException", "Exception"],
    ),
    "EXCEPTION-003": AlibabaStandard(
        rule_id="EXCEPTION-003",
        title="finally块不能return",
        category="Exception",
        severity="blocker",
        description="finally块中禁止return，否则会吞掉try/catch中的异常",
        examples=["finally { return result; } // BAD"],
        keywords=["finally", "return"],
        detection_patterns=[r"finally\s*\{[^}]*return\b"],
    ),
    "EXCEPTION-004": AlibabaStandard(
        rule_id="EXCEPTION-004",
        title="自定义异常要提供cause",
        category="Exception",
        severity="critical",
        description="自定义异常必须提供原始异常的cause传递",
        examples=["new BusinessException('msg', e)"],
        keywords=["extends", "Exception", "BusinessException", "cause"],
    ),
    # Concurrency (并发编程)
    "CONCURRENCY-001": AlibabaStandard(
        rule_id="CONCURRENCY-001",
        title="并发修改同一对象要加锁",
        category="Concurrency",
        severity="blocker",
        description="并发修改同一对象时必须加锁，使用synchronized或java.util.concurrent包",
        examples=["synchronized(this)", "ReentrantLock"],
        keywords=["synchronized", "volatile", "RaceCondition"],
    ),
    "CONCURRENCY-002": AlibabaStandard(
        rule_id="CONCURRENCY-002",
        title="ThreadLocal要清理",
        category="Concurrency",
        severity="critical",
        description="ThreadLocal使用后必须remove()，避免内存泄漏",
        examples=["threadLocal.remove();"],
        keywords=["ThreadLocal", "remove", "InheritableThreadLocal"],
        detection_patterns=[r"ThreadLocal<", r"\.remove\(\)"],
    ),
    "CONCURRENCY-003": AlibabaStandard(
        rule_id="CONCURRENCY-003",
        title="禁止使用Executors创建线程池",
        category="Concurrency",
        severity="blocker",
        description="禁止使用Executors创建线程池，应使用ThreadPoolExecutor明确参数",
        examples=["new ThreadPoolExecutor(core, max, 0L, ...)"],
        keywords=["Executors.newFixedThreadPool", "Executors.newCachedThreadPool", "ThreadPoolExecutor"],
        detection_patterns=[r"Executors\.new(?:Fixed|Cached|Single|Scheduled)ThreadPool"],
    ),
    # Collection (集合处理)
    "COLLECTION-001": AlibabaStandard(
        rule_id="COLLECTION-001",
        title="ArrayList删除元素要使用Iterator",
        category="Collection",
        severity="critical",
        description="ArrayList删除元素必须使用Iterator，否则会抛出ConcurrentModificationException",
        examples=["iterator.remove()", "list.removeIf()"],
        keywords=["Iterator", "remove", "for-each", "ArrayList"],
        detection_patterns=[r"for\s*\([^:]+:\s*[^)]+\)\s*\{[^}]*\.remove\("],
    ),
    "COLLECTION-002": AlibabaStandard(
        rule_id="COLLECTION-002",
        title="集合初始化要指定大小",
        category="Collection",
        severity="warning",
        description="ArrayList、HashMap等在可预估大小时应指定初始容量，避免扩容开销",
        examples=["new ArrayList<>(100)", "new HashMap<>(16)"],
        keywords=["new ArrayList", "new HashMap", "initialCapacity"],
        detection_patterns=[r"new\s+(?:ArrayList|HashMap)\s*<[^>]*>\s*\(\s*\)"],
    ),
    "COLLECTION-003": AlibabaStandard(
        rule_id="COLLECTION-003",
        title="不要使用size()==0判断集合为空",
        category="Collection",
        severity="warning",
        description="集合判断是否为空应使用isEmpty()，更简洁高效",
        examples=["if (list.isEmpty())", "if (!list.isEmpty())"],
        keywords=["size() == 0", "size() > 0", "isEmpty()"],
        detection_patterns=[r"\.size\(\)\s*(?:==|>|!=)\s*0"],
    ),
    # SQL Standards (SQL规约)
    "SQL-001": AlibabaStandard(
        rule_id="SQL-001",
        title="不要使用count(列名)判断是否存在",
        category="SQL",
        severity="critical",
        description="判断是否存在应使用 EXISTS 或将count()改为limit 1",
        examples=["SELECT 1 FROM ... LIMIT 1", "EXISTS(SELECT 1 ...)"],
        keywords=["count(", "SELECT COUNT"],
        detection_patterns=[r"(?i)select\s+count\s*\("],
    ),
    "SQL-002": AlibabaStandard(
        rule_id="SQL-002",
        title="SQL语句不要用*作为返回列",
        category="SQL",
        severity="warning",
        description="SQL返回列应明确指定，避免使用*导致性能问题和结果不稳定",
        examples=["SELECT id, name, email FROM users"],
        keywords=["SELECT *", "select *"],
        detection_patterns=[r"(?i)select\s+\*"],
    ),
    # OOP Standards (面向对象)
    "OOP-001": AlibabaStandard(
        rule_id="OOP-001",
        title="外部依赖必须依赖接口",
        category="OOP",
        severity="critical",
        description="类依赖应依赖接口或抽象类，避免依赖具体实现类",
        examples=["Map<String, Object> map", "List<User> users"],
        keywords=["Map<", "List<", "Set<", "DependencyInjection"],
    ),
    "OOP-002": AlibabaStandard(
        rule_id="OOP-002",
        title="覆写方法必须加@Override",
        category="OOP",
        severity="critical",
        description="覆写父类或接口方法必须加@Override注解，便于编译器检查",
        examples=["@Override public void method()"],
        keywords=["@Override"],
    ),
}


def get_all_rules() -> list[AlibabaStandard]:
    """Return all Alibaba standards as a list."""
    return list(ALIBABA_STANDARDS.values())


def get_rules_by_category(category: str) -> list[AlibabaStandard]:
    """Return rules filtered by category."""
    return [r for r in ALIBABA_STANDARDS.values() if r.category == category]


def get_rules_by_severity(severity: RuleSeverity) -> list[AlibabaStandard]:
    """Return rules filtered by severity."""
    return [r for r in ALIBABA_STANDARDS.values() if r.severity == severity]
