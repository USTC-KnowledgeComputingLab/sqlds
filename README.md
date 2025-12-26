# Distributed Deductive System Sorts (DDSS)

DDSS is a distributed deductive system with a scalable architecture, providing identical implementations in both **Python** and **TypeScript**. It currently supports distributed engines including forward-chaining, E-graph, and more.

## Design Philosophy

DDSS adopts a modular architecture that decomposes the deductive system into independent but collaborative sub-systems:

1. **Separation of Concerns**: Each module focuses on a specific reasoning task.
2. **Concurrent Execution**: All modules collaborate asynchronously through a shared database, fully utilizing system resources.
3. **Persistent Storage**: Uses a database to store facts and ideas, ensuring data consistency.

The system uses a database as the central hub, with two tables (`facts` and `ideas`) for interaction between sub-systems:

- **Eager engines** (e.g., forward-chaining): Read facts and eagerly produce new facts. They also add ideas to broadcast "I want this XXX" - indicating what new facts they need to produce more results.

- **Lazy engines** (e.g., E-graph): Could produce too many facts if eager, so they quietly accept facts without producing many. They only produce facts when they see ideas from other engines that they can (partially) fulfill.

## Modules

The system consists of the following modules, implemented symmetrically in `ddss/*.py` and `ddss/*.ts`:

- **Input** (`ddss/input.py`, `ddss/input.ts`): Interactive input interface with BNF syntax parsing
- **Output** (`ddss/output.py`, `ddss/output.ts`): Real-time display of facts and ideas from the database
- **Load** (`ddss/load.py`, `ddss/load.ts`): Batch import of facts from standard input
- **Dump** (`ddss/dump.py`, `ddss/dump.ts`): Export all facts and ideas to output
- **DS** (`ddss/ds.py`, `ddss/ds.ts`): Forward-chaining deductive search engine
- **Egg** (`ddss/egg.py`, `ddss/egg.ts`): E-graph based equality reasoning engine

## Installation

You can choose either the Python or TypeScript version. Both provide the same `ddss` command-line interface.

### Python Version

#### Using uvx (Recommended)
```bash
uvx ddss
```

#### Using pip
```bash
pip install ddss
ddss
```

### TypeScript Version

#### Using npx (Recommended)
```bash
npx @hzhangxyz/ddss
```

#### Using npm
```bash
npm install -g @hzhangxyz/ddss
ddss
```

## Usage

The usage, command-line options, and interactive syntax are identical regardless of the implementation language used.

### Basic Usage

Run DDSS with a temporary SQLite database:

```bash
ddss
```

### Specifying a Database

DDSS supports multiple database backends using the `-a` or `--addr` option:

```bash
# SQLite (persistent)
ddss --addr sqlite:///path/to/database.db

# MySQL
ddss --addr mysql://user:password@host:port/database

# MariaDB
ddss --addr mariadb://user:password@host:port/database

# PostgreSQL
ddss --addr postgresql://user:password@host:port/database
```

### Selecting Components

By default, DDSS runs with all interactive components (`input`, `output`, `ds`, `egg`). You can select specific components using the `-c` or `--component` option:

```bash
# Run only input and output (no inference engines)
ddss --component input output

# Run with only the forward-chaining engine
ddss --component input output ds

# Run with only the E-graph engine
ddss --component input output egg
```

Available components:
- `input`: Interactive input interface
- `output`: Real-time display of facts and ideas
- `ds`: Forward-chaining deductive search engine
- `egg`: E-graph based equality reasoning engine
- `load`: Batch import facts from standard input
- `dump`: Export all facts and ideas to output

### Interactive Usage

After starting, input facts and rules at the `input:` prompt. The syntax follows the format `premise => conclusion`:

**Example 1: Simple Inference**

Input a fact stating `a` is true:
```
input: => a
```

Input a rule stating if `a` then `b`:
```
input: a => b
```

The system automatically derives and displays `=> b`:
```
fact: => b
```

**Example 2: Equality Reasoning**

Input an equality relation `a == b`:
```
input: => a == b
```

Input an idea for `b == a` by creating a rule that requires it:
```
input: b == a => target
```

The system will derive both the idea and facts:
```
idea: => b == a
fact: => b == a
fact: => target
```

## License

This project is licensed under the GNU Affero General Public License v3.0 or later. See [LICENSE.md](LICENSE.md) for details.

## Links

- GitHub: https://github.com/USTC-KnowledgeComputingLab/ddss
