# Local AI enhancement validation

These fixtures were written for this change. The official competition enhancement
test and official Mock AI Service were unavailable in the selected repository.

Start the fixture in one terminal, then execute SQL checks against the server built
from this checkout in another terminal. The fixture listens on port 8000.

```sh
python3 unittest/sql/engine/expr/local_ai/mock_service.py
python3 unittest/sql/engine/expr/local_ai/check_sql.py
```

The SQL runner requires PyMySQL and a checkout-built seekdb listening on port 2881.
It creates temporary AI models and endpoints in the connected database and removes
them on exit. Use a disposable development instance with no existing models named
`local_ai_*`. Embedding responses deliberately reverse the OpenAI result order.

## Validation recorded during implementation

- Python syntax compilation passed for both local scripts.
- HTTP requests to the running fixture passed for OpenAI embeddings, Ollama
  completion, Ollama embeddings and rerank. These checks exercise the fixture.
- The SQL runner failed to connect to port 2881. No SQL assertions executed.
- The source build failed during Bazel analysis because the pinned SDK compiler
  `deps/3rd/usr/local/oceanbase/devtools/bin/clang` was missing.
- Downloading the pinned SDK from the official OceanBase mirror returned a
  proxy CONNECT 403. Repository toolchain pins and checksums were preserved.
- The existing `ai_function.ai_prompt` mysqltest run could not start because
  `build/bin/src/observer/seekdb` was missing.
- `git diff --check` passed.

Build attempted from the repository root after sourcing the local tool environment.

```sh
./build.py build -j5 --lockfile_mode=error   --downloader_config=/workspace/seekdb-dev/direct-downloads.cfg seekdb
python3 tools/deploy/mysqltest.py run   --base-dir /workspace/seekdb-dev/ai-mysqltest-instance   --work-dir /workspace/seekdb-dev/ai-mysqltest-results   --port 2881 --test-set ai_function.ai_prompt
```

The downloader override is an empty local file which selects canonical upstream
URLs and preserves artifact checksum verification.

## Competition test availability

The selected origin advertised master and a dependency-cache repair branch.
The current checkout contains `ai_prompt.test` with legacy expectations rejecting
JSON and TEXT arguments. Its assertions and expected output were preserved.
The two requested C++ files existed before commit `45cbbe9e1` and were removed in
that historical cleanup. Current Bazel target discovery does not declare them.
No `ai_function_enhancement.test` or official mock service was found.
The supplied Yuque tutorial URL also returned proxy CONNECT 403.

## Outstanding validation

All changed C++ paths require compilation and execution with the pinned SDK.
The six competition subproblems remain unverified against the official tests.
The local SQL runner covers positive prompt, completion, embedding, object rerank,
NULL, filtering, LIMIT, multiple batches and invalid dimension cases. It does not
yet cover every malformed-response and transport-failure scenario.
No published pylibseekdb result is used as evidence for this source change.
