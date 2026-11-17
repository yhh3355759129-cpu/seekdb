"""Local protocol fixture for AI enhancement checks, independent of contest tests."""

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def vector(text, dimensions):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255 for i in range(dimensions)]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path in ("/api/embed", "/v1/embeddings"):
                inputs = body["input"]
                if isinstance(inputs, str):
                    inputs = [inputs]
                dimensions = body.get("dimensions", 4)
                embeddings = [vector(text, dimensions) for text in inputs]
                if self.path == "/api/embed":
                    result = {"embeddings": embeddings}
                else:
                    result = {"data": [
                        {"index": i, "embedding": embeddings[i]}
                        for i in reversed(range(len(inputs)))
                    ]}
            elif self.path in ("/api/generate", "/v1/chat/completions"):
                if self.path == "/api/generate":
                    if body.get("stream") is not False:
                        raise ValueError("non-streaming request required")
                    result = {"response": body["prompt"], "done": True}
                else:
                    result = {"choices": [{"message": {
                        "content": body["messages"][-1]["content"]
                    }}]}
            elif self.path == "/rerank":
                inputs = body["input"]
                documents = inputs["documents"]
                query = inputs["query"]
                result = {"output": {"results": [
                    {"index": i, "relevance_score": float(doc.count(query))}
                    for i, doc in enumerate(documents)
                ]}}
            else:
                self.send_error(404)
                return
            payload = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (KeyError, ValueError, TypeError) as error:
            self.send_error(400, str(error))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
