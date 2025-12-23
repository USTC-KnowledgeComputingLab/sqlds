# Distributed Deductive System Sorts (DDSS)

DDSS is a distributed deductive system with a scalable architecture. It currently supports distributed engines including forward-chaining, E-graph, and more.

## Design Philosophy

DDSS adopts a modular architecture that decomposes the deductive system into independent but collaborative sub-systems:

1. **Separation of Concerns**: Each module focuses on a specific reasoning task
2. **Concurrent Execution**: All modules collaborate asynchronously through a shared database, fully utilizing system resources
3. **Persistent Storage**: Uses a database to store facts and ideas, ensuring data consistency

The system uses a database as the central hub, with two tables (`facts` and `ideas`) for interaction between sub-systems:

- **Eager engines** (e.g., forward-chaining): Read facts and eagerly produce new facts. They also add ideas to broadcast "I want this XXX" - indicating what new facts they need to produce more results.

- **Lazy engines** (e.g., E-graph): Could produce too many facts if eager, so they quietly accept facts without producing many. They only produce facts when they see ideas from other engines that they can (partially) fulfill.

## Modules

- **Input** (`ddss/input.py`): Interactive input interface with BNF syntax parsing
- **Output** (`ddss/output.py`): Real-time display of facts and ideas from the database
- **Load** (`ddss/load.py`): Batch import of facts from standard input
- **Dump** (`ddss/dump.py`): Export all facts and ideas to output
- **DS** (`ddss/ds.py`): Forward-chaining deductive search engine
- **Egg** (`ddss/egg.py`): E-graph based equality reasoning engine

## Integrated Main

DDSS provides an integrated main program that runs the Input, Output, DS, and Egg modules concurrently.

**Data Flow**:
1. User inputs facts through the Input module
2. DS and Egg modules monitor the database and perform inference
3. Newly derived facts are written back to the database
4. Output module displays all new facts and ideas in real-time

## Installation

### Using uvx (Recommended)

The simplest way is to run with `uvx`:

```bash
uvx ddss
```

This automatically installs all dependencies and starts the DDSS system.

### Using pip

```bash
pip install ddss
ddss
```

## Usage

### Basic Usage

Run DDSS with a temporary SQLite database:

```bash
ddss
```

### Specifying a Database

DDSS supports multiple database backends:

```bash
# SQLite (persistent)
ddss sqlite:///path/to/database.db

# MySQL
ddss mysql://user:password@host:port/database

# MariaDB
ddss mariadb://user:password@host:port/database

# PostgreSQL
ddss postgresql://user:password@host:port/database
```

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
