"""Exercise the running checkout-built server against the local mock on port 8000."""

import json
import pymysql
from mock_service import vector


def main():
    with pymysql.connect(host="127.0.0.1", port=2881, user="root",
                         database="test", autocommit=True) as connection:
        with connection.cursor() as cursor:
            def execute(sql, args=None):
                cursor.execute(sql, args)
                return cursor.fetchall()

            def scalar(sql, args=None):
                return execute(sql, args)[0][0]

            models = [
                ("local_ai_complete", "completion", "openai", "/v1/chat/completions"),
                ("local_ai_embed", "dense_embedding", "openai", "/v1/embeddings"),
                ("local_ai_ollama", "completion", "oLlAmA", "/api/generate"),
                ("local_ai_ollama_embed", "dense_embedding", "OLLAMA", "/api/embed"),
                ("local_ai_rerank", "rerank", "dashscope", "/rerank"),
            ]
            created_models = []
            created_endpoints = []
            try:
                for name, kind, provider, path in models:
                    execute("CALL DBMS_AI_SERVICE.CREATE_AI_MODEL(%s, %s)",
                            (name, json.dumps({"type": kind, "model_name": name})))
                    created_models.append(name)
                    execute("CALL DBMS_AI_SERVICE.CREATE_AI_MODEL_ENDPOINT(%s, %s)",
                            (name + "_endpoint", json.dumps({
                                "ai_model_name": name, "provider": provider,
                                "url": "http://127.0.0.1:8000" + path,
                                "access_key": "" if provider.upper() == "OLLAMA" else "local-fixture",
                            })))
                    created_endpoints.append(name + "_endpoint")

                assert scalar("SELECT AI_COMPLETE('local_ai_complete','你好', NULL)") == "你好"
                assert scalar("SELECT AI_COMPLETE('local_ai_complete', AI_PROMPT('{0}-{0}', 'abc'))") == "abc-abc"
                assert scalar("SELECT AI_COMPLETE('local_ai_complete', AI_PROMPT('{0}', AI_PROMPT('{0}', 'nested')))") == "nested"
                assert scalar("SELECT AI_COMPLETE('local_ai_ollama', 'hello', JSON_OBJECT('temperature', 0, 'max_tokens', 8))") == "hello"
                assert scalar("SELECT AI_COMPLETE('local_ai_complete', AI_PROMPT('{0}', JSON_ARRAY('x', 'y')))") == '["x", "y"]'
                long_text = "你好" * 10000
                assert scalar("SELECT AI_COMPLETE('local_ai_complete', %s)", (long_text,)) == long_text
                for model in ("local_ai_embed", "local_ai_ollama_embed"):
                    assert json.loads(scalar("SELECT AI_EMBED(%s, 'hello')", (model,))) == vector("hello", 4)
                    assert json.loads(scalar("SELECT AI_EMBED(%s, 'hello', 8)", (model,))) == vector("hello", 8)

                execute("CREATE TEMPORARY TABLE local_ai_rows (id INT PRIMARY KEY, txt LONGTEXT)")
                cursor.executemany("INSERT INTO local_ai_rows VALUES (%s, %s)",
                                   [(i, None if i % 11 == 0 else str(i)) for i in range(80)])
                rows = execute("SELECT id, AI_EMBED('local_ai_embed', txt, 4) FROM local_ai_rows WHERE id >= 3 LIMIT 65")
                assert len(rows) == 65
                for index, result in rows:
                    assert (result is None) if index % 11 == 0 else json.loads(result) == vector(str(index), 4)
                for dimension in (0, -1, 1.5):
                    try:
                        execute("SELECT AI_EMBED('local_ai_embed', 'x', %s)", (dimension,))
                    except pymysql.MySQLError:
                        pass
                    else:
                        raise AssertionError("invalid dimension accepted")
                documents = [{"id": i, "text": "q" * (i % 4)} for i in range(45)]
                ranked = json.loads(scalar("SELECT AI_RERANK('local_ai_rerank', 'q', %s, 'text')",
                                           (json.dumps(documents),)))
                assert [item["id"] for item in ranked] == sorted(range(45), key=lambda i: -(i % 4))
                print("Local SQL checks passed")
            finally:
                for name in reversed(created_endpoints):
                    execute("CALL DBMS_AI_SERVICE.DROP_AI_MODEL_ENDPOINT(%s)", (name,))
                for name in reversed(created_models):
                    execute("CALL DBMS_AI_SERVICE.DROP_AI_MODEL(%s)", (name,))


if __name__ == "__main__":
    main()
