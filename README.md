# funseek

**Find the Python function that does X, without knowing its name or where it resides.**

`funseek` is a command-line search engine for Python Repos. Point it at a folder, then describe what you are looking for in plain English. It combines keyword search, semantic search and call-graph function neighbours, and can optionally rerank the top results with an LLM that explains each match in one sentence.

Everything runs locally by default. Nothing leaves your machine unless you choose a cloud reranker.


```text
$ funseek search .

Query: combine scores from several retrievers

Warning: No provider specified. Skipping reranking, showing fused results.

Results for: "combine scores from several retrievers"

1. _accumulate_scores  C:/Demo/funseek/funseek/pipeline/fusion.py:32

2. fuse  C:/Demo/funseek/funseek/pipeline/fusion.py:12
.
.
```

Both `funseek` and the shorter `fun` invoke the same program.

![Demo](https://raw.githubusercontent.com/GovindhKishore/funseek/main/docs/demo-funseek.gif)

---

## Contents

1. [Why it exists](#why-it-exists)
2. [Installation](#installation)
3. [Quickstart](#quickstart)
4. [CLI reference](#cli-reference)
5. [How it works and the Math](#how-it-works-and-the-math)
6. [Evaluation](#evaluation)
7. [Tuning guide](#tuning-guide)
8. [Behaviour worth knowing](#notes-and-behaviour-worth-knowing)
9. [Limitations](#limitations)
10. [Project layout](#project-layout)

---

## Why it exists

When you join a project, or work inside an unfamiliar module, the hard question is rarely "what does this function do?". It is "where is the code that does X?".

| Tool | Where it lacks eficacy                                                     |
|---|----------------------------------------------------------------------------|
| `grep` / IDE search | Needs the exact name or a keyword that appears in the code.                |
| Pure keyword search (BM25) | Misses paraphrases: "make each row unit length" will not match "normalize". |
| Pure embedding search | Understands meaning but can miss exact identifiers and rare terms.         |
| AI-native IDEs / assistants | Strong at generating and editing code, but usually cloud-hosted and account-based, so your code leaves the machine. Their retrieval is largely opaque, and you cannot tune its weighting.                              |

`funseek` fuses three signals so that each covers the others' blind spots, and returns results at **function level**: name, file and line, ready to jump to.

---

## Installation

```bash
pip install funseek
```

### From source (for development)

```bash
git clone https://github.com/GovindhKishore/funseek.git
cd funseek
pip install -e .
```

Requires Python 3.10 or newer.


### First run

- The first run of `index` or `search` imports the `sentence-transformers` library and downloads the `all-MiniLM-L6-v2` model weights to build or load the index. This initial setup takes a moment.
- If you need higher priority and higher rate-limited downloads, set a free token: `HF_TOKEN=<your token>`.
- Indexes are stored under `~/.funseek`.

---

## Quickstart

```bash
# 1. Index a folder (builds the BM25, vector and call-graph indexes)
funseek index ./my_project

# 2. Search it interactively
funseek search ./my_project

# 3. Optional rerank with an LLM
funseek set-api-key gemini <your-key>
funseek search ./my_project --provider gemini

# Optional rerank but fully local
ollama pull llama3.2:1b
funseek search ./my_project --provider ollama
```

`search` is an interactive loop. The models and indexes load once, then you can type as many queries as you like. Type `exit` or `quit`, or press `Ctrl+C`, to leave the loop.

---

## CLI reference

All commands work as `funseek <command>` or `fun <command>`.

### `index`

Build and save all three indexes for a folder.

```bash
funseek index FOLDER [--timings] [--include-tests]
```

| Option | Default  | Description |
|---|----------|---|
| `FOLDER` | required | Folder to index. |
| `--timings` | false    | Print how long parsing and each index took. |
| `--include-tests` | false      | Also index test files and test directories. |

If the folder is already indexed, the command says so and exits. Use `reindex` to rebuild.

### `reindex`

Force a full rebuild of a folder's indexes. Use it after code changes, to change the `--include-tests` setting or to 
remove corrupted indexes and rebuild new ones

```bash
funseek reindex FOLDER [--timings] [--include-tests]
```

Options are the same as `index`.

### `search`

Interactive natural-language search over an indexed folder.

```bash
funseek search FOLDER [OPTIONS]
```

| Option | Default  | Description                                                                                                                                                                                |
|---|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `FOLDER` | required | Folder to search. Must have been indexed, unless `--no-index` is used.                                                                                                                     |
| `--no-index` | false    | Build the indexes in memory for this session only. Nothing is written to `~/.funseek`.                                                                                                     |
| `--bm25-weight` | 0.9      | Weight of the bm25 retriever in fusion.                                                                                                                                                    |
| `--vector-weight` | 1.0      | Weight of the vector retriever in fusion.                                                                                                                                                  |
| `--structural-weight` | 0.3      | Weight of the call-graph retriever in fusion.                                                                                                                                              |
| `--max-hop` | 1        | Controls how deep to traverse caller and callee function relationships from seed results. 1 inspects direct callers/callees, while 2 expands to 2nd-degree functional neighbors and so on. |
| `--decay-factor` | 0.5      | Per-hop decay in graph scoring.                                                                                                                                                            |
| `--provider` | none     | Reranker: `gemini` or `ollama`. Without it, fused results are shown.                                                                                                                       |
| `--model` | none     | Model name for the reranker. If default(None) is used, default model name is chosen from given provider class, if povider is given.                                                        |
| `--top-n` | 10       | Number of results shown.                                                                                                                                                                   |
| `--num-rerank-candids` | 20       | Number of fused candidates sent to the reranker.                                                                                                                                           
| `--timings` | false    | Print per-step timings.                                                                                                                                                                    |
| `--include-tests` | false    | Only used with `--no-index`. For an indexed folder, the setting chosen at index time applies.                                                                                              |

If files changed since the last index, `search` warns you and asks whether to continue with the existing index.

### `clear`

Delete stored indexes.

```bash
funseek clear --folder PATH
funseek clear --all-items
```

| Option | Default | Description |
|---|-------|---|
| `--folder` | none  | Remove the indexes of one folder. |
| `--all-items` | false | Remove every stored index. |

Exactly one of the two options is required. The folder must be given with `--folder`, so a stray argument can never delete anything.

### `set-api-key`, `get-api-key`, `clear-api-key`

```bash
funseek set-api-key gemini <key>
funseek get-api-key gemini     
funseek clear-api-key gemini
```

Keys are kept in your operating system's credential store (Windows Credential Manager, macOS Keychain, Linux Secret Service), never in a plain file.

---

## How it works and the Math

### 1. Parsing

`funseek` parses every `.py` file with Python's `ast` module and extracts each function and method: name, enclosing class, file, line, docstring, parameters, return type and the function names with class names (if detectable) it calls. Each function becomes a normalised text document used by the keyword and semantic indexes. Files that cannot be parsed are skipped and counted in a warning.

### 2. Three retrievers

| Retriever | Signal                      | Implementation |
|---|-----------------------------|---|
| **Lexical** | exact terms                 | BM25 over the composite document of each function |
| **Semantic** | meaning                     | `all-MiniLM-L6-v2` embeddings in ChromaDB, cosine similarity |
| **Structural** | function call relationships | NetworkX call graph, expanded from the top results of the other two |

The semantic retriever always returns its closest matches and current architecture keeps minimum of 3 results from
vector search afterwards only takes the next if it's similarity is above a certain threshold, so a typo-heavy query still gets results.

### 3. Structural scoring

The structural retriever takes the top 10 BM25 and top 10 semantic results as **seeds** and walks the call graph from them, following both callees and callers. A function reached from several seeds, and from highly ranked seeds, scores higher:

$$
\text{score}(n) = \sum_{s \in S(n)} \frac{\gamma^{\,d(s,n)}}{\text{rank}(s)}
$$

where $S(n)$ is the set of seeds that reach node $n$, $d(s,n)$ is the number of hops to reach the node $n$ from seed $s$, $\gamma$ is the decay factor (default $0.5$), and $\text{rank}(s)$ is the seed's rank in the retriever that produced it. Seeds themselves are excluded from the structural list, so the graph only adds new candidates. The top 10 structural results are passed to fusion.

This retriever exists to fetch functions that neither keyword nor semantic search would find, such as a helper that shares no vocabulary with the query but sits right next to a relevant function.

### 4. Reciprocal Rank Fusion

The three ranked lists are merged using rank position rather than raw score values, avoiding the need to normalize incompatible scales.

$$
\text{RRF}(f) = \sum_{i \in \{\text{bm25},\,\text{vec},\,\text{struct}\}} \frac{w_i}{k + \text{rank}_i(f)}, \qquad k = 60
$$

A function absent from a retriever's list simply contributes nothing for that retriever. The weights $w_i$ are the `--*-weight` options.

### 5. Optional LLM reranking

The top `--num-rerank-candids` fused candidates (default 20) are sent to an LLM along with each function's source code. Candidates are shuffled to avoid position bias. The model returns a ranking with a one-sentence explanation per function.

The reranker is defensive. If the call fails, the response is not valid JSON, or no returned entry can be matched to a candidate, `funseek` falls back to the fused ranking. Entries returned are matched by `(file, line)` first and by `(file, name)` only when that is unambiguous.

---

## Evaluation

### Setup

| Item | Value                                                                                                                                                                      |
|---|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Corpus | scikit-learn: `model_selection`, `preprocessing` and other subpackages (about 1,260 functions)                                                                             |
| Snapshot | funseek [`64e67a4`](https://github.com/GovindhKishore/funseek/commit/64e67a4); scikit-learn [`c1f21786a8`](https://github.com/scikit-learn/scikit-learn/commit/c1f21786a8) |
| Tests | Excluded from the index                                                                                                                                                    |
| Queries | 30 natural-language queries, about a quarter with realistic typos and grammar mistakes.                                                                                    |
| Labels | Graded: **exact** (grade 2) and **related** (grade 1)                                                                                                                      |

Queries describe what a function does. Labels indicate whether the function is directly relevant (grade 2), related (grade 1), or unrelated (grade 0) to the query.
### Metrics

Let $G$ be the set of labelled functions of a query (grades 1 and 2), and $\text{top}_k$ the first $k$ distinct results.

$$
\text{MRR@5} = \frac{1}{|Q|}\sum_{q}\frac{1}{r_q}, \quad r_q = \text{rank of the first exact (grade 2) result within the top 5}
$$

$$
\text{Precision@5} = \frac{|\text{top}_5 \cap G|}{5}, \qquad
\text{Recall@}k = \frac{|\text{top}_k \cap G|}{|G|}
$$

$$
\text{nDCG@10} = \frac{\text{DCG@10}}{\text{IDCG@10}}, \qquad
\text{DCG@10} = \sum_{i=1}^{10} \frac{g_i}{\log_2(i+1)}
$$

where $g_i$ is the grade (0, 1 or 2) of the result at position $i$, and IDCG is the DCG of the ideal ordering. Recall@20 is also the ceiling for the reranker, which only sees the top 20 candidates. Precision@5, Recall@k and nDCG@10 are computed per query and then averaged over all queries in Q, in the same way as MRR@5. Reported values are means over the 30 queries.

### Results

Weights: BM25 0.9, semantic 1.0, structural 0.3; one graph hop; seeds = top 10 of each retriever; vector retriever `min_keep = 3`.

| Configuration | MRR@5 | Prec@5 | nDCG@10 | Recall@10 | Recall@15 | Recall@20 |
|---|---:|---:|---:|---:|---:|---:|
| BM25 only | 0.4194 | 0.1867 | 0.4758 | 0.5500 | 0.5778 | 0.6111 |
| Semantic only | 0.5122 | 0.2133 | 0.5460 | 0.6278 | 0.6722 | 0.7222 |
| Structural only | 0.0917 | 0.1467 | 0.2687 | 0.4056 | 0.4583 | 0.4583 |
| BM25 + Semantic (no graph) | 0.5389 | 0.2333 | 0.5575 | 0.6444 | 0.7111 | 0.7389 |
| **BM25 + Semantic + Graph** | **0.6022** | **0.2533** | **0.6016** | **0.6833** | **0.7444** | **0.7889** |

What this shows:

- Fusing keyword and semantic search improves on semantic search alone on MRR@5 (0.5389 vs 0.5122), Recall@15 and Recall@20, while nDCG@10 is roughly equal (0.5575 vs 0.5460).
- Adding the call graph gives the best result on MRR@5, Precision@5, nDCG@10, Recall@10, Recall@15 and Recall@20. Against the same system without the graph, the gain is about +0.063 MRR@5, +0.044 nDCG@10 and +0.05 Recall@20.
- The structural retriever is weak on its own, as expected, since it can only reach neighbours of seeds. Its value is in fusion.

### How the graph scoring was chosen

Several scoring schemes were compared on the same query set, each changing one thing at a time. These comparisons were run while the vector retriever's `min_keep` was 10. After they were run, `min_keep` was changed to 3, which performed better, and the final results above use 3.

| Structural scoring                                             | nDCG@10 |
|----------------------------------------------------------------|---:|
| No graph                                                       | 0.544 |
| Hop decay only                                                 | 0.534 |
| Hop decay + degree penalty + counting seeds                    | 0.535 |
| Hop decay + Jaccard overlap with seeds                         | 0.558 |
| Sum of decay over all reaching seeds                           | 0.576 |
| **Sum of decay over all reaching seeds, divided by seed rank** | **0.610** |

Hop decay alone and the degree penalty did not help. Jaccard overlap gave a small gain but pulls the graph towards functions that BM25 already finds. Weighting by how many seeds reach a node, and by how highly those seeds ranked, was clearly better. Extending to two hops did not help under a top-10 cap.

**Note:** The vector retriever's `min_keep` parameter sets the number of top-ranked results that are always kept, regardless of the similarity threshold. Only results ranked after `MIN_KEEP` are filtered by the threshold. This prevents the semantic retriever from returning an empty list for queries whose best matches are weakly similar.

**Note:** The performance of every retriever depends on repository, and this is especially true for the graph retriever. The evaluation was run on a test folder containing the scikit-learn subpackages `preprocessing`, `model_selection` and related modules. If a repository has many functions with unique (name, class name) pairs, the call graph will be large and less ambiguous, and structural expansion reaches a broader and more reliable set of related functions. If names and class names are heavily reused, the graph is smaller, and the structural signal contributes less. The reported numbers should therefore be read as results for this corpus, not as a general measure of performance on all Python code.

### Caveats

- **Small query set.** 30 queries: one query moves recall by about 0.03, so differences of a few hundredths are within noise.
- **In-sample tuning.** Weights were tuned on the same queries that are reported, so the numbers are optimistic.
- **Incomplete labels.** Unlabelled correct functions count as misses, so absolute scores are lower bounds. Comparisons between configurations are still valid, since all are judged on the same labels.
- **Corpus-dependent.** **Scale matters.** On the full scikit-learn package (about 11,000 functions including tests) scores are lower for every retriever, because there are many more near-duplicate names. Module-scale search is the intended use case.
- **Reranker not measured.** The reranker is not part of this table. It measures retrieval quality only.

---

## Tuning guide

| Situation | Try                                                                               |
|---|-----------------------------------------------------------------------------------|
| Queries use the codebase's exact terminology | Increase `--bm25-weight`.                                                         |
| Queries are vague or use different vocabulary | Increase `--vector-weight`.                                                       |
| Many classes share method names (`run`, `fit`, `execute`) | Lower `--structural-weight`.                                                      |
| Results feel too broad (unrelated functions mixed in) | Lower `--structural-weight` (or set it to `0`), or keep `--max-hop` at `1`. |
| Results feel too narrow | Increase `--max-hop` to `2` for more related functions or `--num-rerank-candids`. |
| Reranking is slow or the model is weak | Lower `--num-rerank-candids` to `10`.                                             |


---

## Behaviour worth knowing

- **Tests are excluded by default.** Directories named `test` or `tests`, and files named `test_*.py` or `*_test.py`, are skipped. Use `--include-tests` on `index` or `reindex` to include them. Changing the setting for an existing index requires `reindex`.
- **Stale indexes.** `search` compares file modification times with those recorded at index time. If they differ, it asks whether to proceed.
- **`--no-index`** parses and builds in memory, searches, and discards everything. It is useful for one-off searches and writes nothing to disk, but the build takes time on large folders.
- **Reranker models.** Defaults are `gemini-3.1-flash-lite` and `llama3.2:1b`. Can change using `--model`. A 1B local model may sometimes fail to return valid JSON, in which case the fused results are shown. A larger local model usually reranks better.
- **Ollama** must be running if using ollama provider for reranking, and the model must be pulled (`ollama pull <model>`).
- **Registry corruption.** If `~/.funseek/registry.json` is damaged, it is moved aside to a timestamped backup and rebuilt on the next `index` or `reindex`.
- **Clickable paths.** Results print `path:line`. Some IDE terminals (PyCharm, for example) only make paths clickable for projects they have indexed.
- **Interrupted builds.** If you cancel `index` or `reindex` midway, run `reindex` again to completion to create non-corrupted indexes.
- **Privacy.** With no `--provider`, or with `ollama`, no code leaves your machine. With `gemini`, the source of the top candidates is sent to Google.

---

## Limitations

- **Python only.** Other languages are not parsed.
- **Approximate call graph.** Calls are matched by name and class, without full import or type resolution. Calls like `obj.method()` on an unknown receiver are not resolved. Functions whose `(name, class)` pair is not unique within the folder are left out of the call graph, so in codebases with heavy name reuse the structural retriever helps less.
- **Small evaluation set** and incomplete labels, as described above.
- **Embedding model** is general-purpose, not code-specific.
- **Large repositories.** Indexing time and memory grow with the number of functions. Index the subpackage you work in if a whole repository is slow.

---

## Project layout

```text
funseek/
├── eval/
│   ├── run_eval.py
│   └── new_set_queries_hcse_eval.json
├── funseek/
│   ├── indexing/
│   │   ├── bm25_index.py
│   │   ├── vector_index.py
│   │   └── graph_index.py
│   ├── parsing/
│   │   └── parser.py
│   ├── pipeline/
│   │   ├── fusion.py
│   │   └── reranker.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── gemini.py
│   │   └── ollama.py
│   ├── retrieval/
│   │   ├── types.py
│   │   ├── bm25_retriever.py
│   │   ├── vector_retriever.py
│   │   └── graph_retriever.py
│   ├── cli.py
│   └── config.py
├── pyproject.toml
└── README.md
```

## Contributing

Issues and pull requests are welcome. Run the evaluation harness before and after any retrieval change, and report the table.

## License

This project is licensed under the MIT License.