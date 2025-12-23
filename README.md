# Distributed Deductive System Sorts (DDSS)

DDSS is a distributed deductive system for automated theorem proving and knowledge reasoning. It combines forward-chaining inference with E-graph (equality graph) techniques to enable efficient logical deduction and equality reasoning.

## Design Philosophy

DDSS adopts a modular architecture that decomposes the reasoning engine into independent but collaborative components:

1. **Separation of Concerns**: Each module focuses on a specific reasoning task
2. **Concurrent Execution**: All modules collaborate asynchronously through a shared database, fully utilizing system resources
3. **Persistent Storage**: Uses a database to store facts and ideas, ensuring data consistency
4. **Incremental Reasoning**: Only processes newly added facts, avoiding redundant computations

The system divides deductive reasoning into two layers:
- **Deductive Search (DS)**: Classical forward-chaining inference that derives new facts from known facts
- **Equality Reasoning (E-graph)**: E-graph algorithm for handling equivalence relations and term rewriting

## Modules

### 1. Input Module

**File**: `ddss/input.py`

The Input module provides an interactive input interface:

- Uses `prompt-toolkit` for a user-friendly command-line interface
- Accepts facts and rules using BNF syntax parsing
- Automatically converts input rules to ideas (when applicable)
- Writes to the database in real-time, triggering inference in other modules

### 2. Output Module

**File**: `ddss/output.py`

The Output module displays reasoning results in real-time:

- Monitors newly added facts and ideas in the database
- Uses `apyds_bnf.unparse` to convert internal representation to readable format
- Outputs the inference process in real-time for debugging and observation

### 3. Load Module

**File**: `ddss/load.py`

The Load module imports data from external sources:

- Reads facts from standard input in batch mode
- Parses using BNF syntax
- Inserts into the database for processing by other modules

### 4. Dump Module

**File**: `ddss/dump.py`

The Dump module exports data to external destinations:

- Outputs all ideas and facts from the database
- Converts to readable format using `apyds_bnf.unparse`
- Useful for saving and analyzing reasoning results

### 5. DS Module (Deductive Search)

**File**: `ddss/ds.py`

The DS module implements a forward-chaining inference engine:

- Monitors new facts in the database
- Applies inference rules to perform deductive reasoning
- Generates new facts and ideas

**How it works**:
- Uses `apyds.Search` for pattern matching and rule application
- When it detects a rule like `a => b` and a fact `=> a`, it derives `=> b`
- For multi-premise rules like `a, b => c`, matching partial premises generates new rules and corresponding ideas

### 6. Egg Module (E-graph)

**File**: `ddss/egg.py`

The Egg module implements an E-graph-based equality reasoning engine:

- Maintains an equality graph (E-graph) storing equivalence relations between terms
- Processes ideas, attempting to prove them through equality relations
- Supports the following inference rules:
  - **Symmetry**: `a = b` ⇒ `b = a`
  - **Transitivity**: `a = b, b = c` ⇒ `a = c`
  - **Congruence**: `a = b` ⇒ `f(a) = f(b)`
  - **Substitution**: `f(a), a = b` ⇒ `f(b)`

**How it works**:
- Reads equality relation facts from the database, building an E-graph
- For each idea, searches in the E-graph whether it can be proven through equality relations
- Supports variable pattern matching, handling parameterized equality relations

## Integrated Main

DDSS provides an integrated main program that runs all four modules concurrently:

**File**: `ddss/main.py`

```python
# The main() function starts four modules simultaneously
await asyncio.wait([
    asyncio.create_task(ds(addr, engine, session)),
    asyncio.create_task(egg(addr, engine, session)),
    asyncio.create_task(input(addr, engine, session)),
    asyncio.create_task(output(addr, engine, session)),
])
```

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

### From Source

```bash
git clone https://github.com/USTC-KnowledgeComputingLab/ddss.git
cd ddss
pip install -e .
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

Input an equality relation `a = b`:
```
input: => (binary == a b)
```

Input an idea `b = a`:
```
input: => (binary == b a)
```

The system proves this idea through symmetry:
```
fact: => (binary == b a)
```

## License

This project is licensed under the GNU Affero General Public License v3.0 or later. See [LICENSE.md](LICENSE.md) for details.

## Links

- GitHub: https://github.com/USTC-KnowledgeComputingLab/ddss
