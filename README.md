# Distributed Deductive System Sorts (DDSS)

DDSS 是一个分布式演绎系统，用于自动化定理证明和知识推理。该系统采用前向链式推理和 E-graph（等价图）技术，实现高效的逻辑推导和等价关系推理。

## 设计思路

DDSS 采用模块化的设计，将推理引擎分解为四个独立但协同工作的模块：

1. **分离关注点**：每个模块专注于特定的推理任务
2. **并发执行**：所有模块通过数据库异步协作，充分利用系统资源
3. **持久化存储**：使用数据库存储事实（Facts）和想法（Ideas），保证数据一致性
4. **增量推理**：只处理新增的事实，避免重复计算

系统的核心思想是将演绎推理分为两个层次：
- **演绎搜索（DS）**：基于经典的前向链式推理，从已知事实推导新事实
- **等价推理（E-graph）**：基于 E-graph 算法，处理等价关系和项重写

## 模块介绍

### 1. DS 模块（Deductive Search）

**文件**：`ddss/ds.py`

DS 模块实现了前向链式推理引擎，核心功能包括：

- 监听数据库中的新事实（Facts）
- 应用推理规则进行演绎推理
- 生成新的事实和想法（Ideas）

**工作原理**：
- 使用 `apyds.Search` 进行模式匹配和规则应用
- 当检测到形如 `a => b` 的规则和 `=> a` 的事实时，推导出 `=> b`
- 对于多前提规则如 `a, b => c`，匹配部分前提后生成新的规则和对应的想法

### 2. Egg 模块（E-graph）

**文件**：`ddss/egg.py`

Egg 模块实现了基于 E-graph 的等价推理引擎：

- 维护一个等价图（E-graph），存储项之间的等价关系
- 处理想法（Ideas），尝试通过等价关系证明它们
- 支持以下推理规则：
  - **对称性**：`a = b` ⇒ `b = a`
  - **传递性**：`a = b, b = c` ⇒ `a = c`
  - **同余性**：`a = b` ⇒ `f(a) = f(b)`
  - **代换**：`f(a), a = b` ⇒ `f(b)`

**工作原理**：
- 从数据库读取等价关系事实，构建 E-graph
- 对于每个想法，在 E-graph 中查找是否可以通过等价关系证明
- 支持变量模式匹配，能够处理参数化的等价关系

### 3. Input 模块

**文件**：`ddss/input.py`

Input 模块提供交互式输入接口：

- 使用 `prompt-toolkit` 提供友好的命令行界面
- 支持输入事实和规则，使用 BNF 语法解析
- 自动将输入的规则转换为想法（如果适用）
- 实时写入数据库，触发其他模块的推理

### 4. Output 模块

**文件**：`ddss/output.py`

Output 模块负责实时显示推理结果：

- 监听数据库中新增的事实和想法
- 使用 `apyds_bnf.unparse` 将内部表示转换为可读格式
- 实时输出推理过程，便于调试和观察

## 集成运行

DDSS 提供了一个集成的主程序，同时运行所有四个模块：

**文件**：`ddss/main.py`

```python
# main() 函数同时启动四个模块
await asyncio.wait([
    asyncio.create_task(ds(addr, engine, session)),
    asyncio.create_task(egg(addr, engine, session)),
    asyncio.create_task(input(addr, engine, session)),
    asyncio.create_task(output(addr, engine, session)),
])
```

**数据流**：
1. 用户通过 Input 模块输入事实
2. DS 模块和 Egg 模块监听数据库，进行推理
3. 新推导的事实写回数据库
4. Output 模块实时显示所有新事实和想法

## 安装

### 使用 uvx（推荐）

最简单的方式是使用 `uvx` 一键运行：

```bash
uvx ddss
```

这将自动安装所有依赖并启动 DDSS 系统。

### 使用 uv 安装

如果你已经安装了 `uv`，可以通过以下方式安装：

```bash
uv pip install ddss
```

### 使用 pip 安装

```bash
pip install ddss
```

### 从源码安装

```bash
git clone https://github.com/USTC-KnowledgeComputingLab/ddss.git
cd ddss
uv pip install -e .
# 或使用 pip
pip install -e .
```

## 使用方法

### 基本用法

运行 DDSS，使用临时的 SQLite 数据库：

```bash
ddss
```

### 指定数据库

DDSS 支持多种数据库后端：

```bash
# SQLite（持久化）
ddss sqlite:///path/to/database.db

# MySQL
ddss mysql://user:password@host:port/database

# MariaDB
ddss mariadb://user:password@host:port/database

# PostgreSQL
ddss postgresql://user:password@host:port/database
```

### 交互式使用

启动后，在 `input:` 提示符下输入事实和规则：

```
input: ----
       a

input: a
       ----
       b
```

系统会自动推导新的事实并实时显示。

### 示例：简单的推理

```
# 输入事实：=> a
input: ----
       a

# 输入规则：a => b
input: a
       ----
       b

# 系统会自动推导并显示：=> b
fact: ----
      b
```

### 示例：等价推理

```
# 输入等价关系：a = b
input: ----
       (binary == a b)

# 输入想法：b = a
input: ----
       (binary == b a)

# 系统会通过对称性证明该想法
fact: ----
      (binary == b a)
```

## 依赖项

- Python >= 3.11
- apyds >= 0.0.11：抽象推理系统核心库
- apyds-bnf >= 0.0.11：BNF 语法解析
- apyds-egg >= 0.0.11：E-graph 实现
- prompt-toolkit >= 3.0.52：交互式命令行界面
- sqlalchemy >= 2.0.45：数据库抽象层
  - 支持 SQLite（aiosqlite）
  - 支持 MySQL/MariaDB（aiomysql）
  - 支持 PostgreSQL（asyncpg）

## 开发

### 运行测试

```bash
# 安装开发依赖
uv pip install -e ".[dev]"

# 运行测试
pytest

# 运行测试并显示覆盖率
pytest --cov=ddss
```

### 代码风格

项目使用 `ruff` 进行代码检查和格式化：

```bash
# 检查代码
ruff check .

# 自动修复
ruff check --fix .

# 格式化代码
ruff format .
```

## 项目结构

```
ddss/
├── ddss/
│   ├── __init__.py
│   ├── main.py       # 集成主程序和 CLI 入口
│   ├── ds.py         # 演绎搜索模块
│   ├── egg.py        # E-graph 推理模块
│   ├── egraph.py     # E-graph 核心实现
│   ├── input.py      # 交互式输入模块
│   ├── output.py     # 输出显示模块
│   ├── orm.py        # 数据库模型
│   ├── utility.py    # 工具函数
│   ├── dump.py       # 数据导出
│   └── load.py       # 数据导入
├── tests/            # 测试文件
├── pyproject.toml    # 项目配置
└── README.md         # 本文件
```

## 许可证

AGPL-3.0-or-later

## 链接

- GitHub: https://github.com/USTC-KnowledgeComputingLab/ddss
