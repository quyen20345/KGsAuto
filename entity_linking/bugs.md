Khi toi chay thi duong nhu qua trinh bi chung lai khong hoat dong linking entity. Giai thich tai sao, cho toi huong giai quyet.

(py312) quyen@Legion-5:~/Documents/KGsAuto$ ./run.sh
Starting Docker services...
WARN[0000] /home/quyen/Documents/KGsAuto/docker-compose.yaml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
Ollama: http://localhost:11434
Neo4j: http://localhost:7474
Bolt: bolt://localhost:7687
Qdrant Web UI: http://localhost:6333/dashboard
Choose an action:
 1) Extract entities
 2) Link entities
 3) Import to Neo4j
 4) Run All
 5) Exit (Services only)
Select [1-5]: 2
[*] Linking entities: data/extracted -> data/import_linked
Starting Entity Linking Pipeline
Input folder: data/extracted
Output folder: data/import_linked
Model: gpt-5
Provider: proxypal

Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█| 103/103 [00:00<00:00, 2042.99it/s, Materializing param=pooler.dense.wei
BertModel LOAD REPORT from: sentence-transformers/all-MiniLM-L6-v2
Key                     | Status     |  | 
------------------------+------------+--+-
embeddings.position_ids | UNEXPECTED |  | 

Notes:
- UNEXPECTED    :can be ignored when loading from different task/architecture; not ok if you expect identical arch.
/home/quyen/Documents/KGsAuto/entity_linking/entity_store.py:14: UserWarning: Qdrant client version 1.17.0 is incompatible with server version 1.15.0. Major versions should match and minor version difference must not exceed 1. Set check_compatibility=False to skip version check.
  self.qdrant_client = QdrantClient("http://localhost:6333")
Loading weights: 100%|█| 103/103 [00:00<00:00, 2815.04it/s, Materializing param=pooler.dense.wei
BertModel LOAD REPORT from: sentence-transformers/all-MiniLM-L6-v2
Key                     | Status     |  | 
------------------------+------------+--+-
embeddings.position_ids | UNEXPECTED |  | 

Notes:
- UNEXPECTED    :can be ignored when loading from different task/architecture; not ok if you expect identical arch.
^CTraceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/quyen/Documents/KGsAuto/entity_linking/cli.py", line 63, in <module>
    main()
  File "/home/quyen/Documents/KGsAuto/entity_linking/cli.py", line 37, in main
    stats = run_pipeline(
            ^^^^^^^^^^^^^
  File "/home/quyen/Documents/KGsAuto/entity_linking/pipeline.py", line 190, in run_pipeline
    stats = run_entity_linking(
            ^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/Documents/KGsAuto/entity_linking/linker.py", line 171, in run_entity_linking
    n = entity_link_iteration(store, llm, **kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/Documents/KGsAuto/entity_linking/linker.py", line 143, in entity_link_iteration
    result = _ask_llm(llm, seed, candidates)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/Documents/KGsAuto/entity_linking/linker.py", line 105, in _ask_llm
    response = llm.generate(prompt)
               ^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/Documents/KGsAuto/llms/clients/proxypal_client.py", line 34, in generate
    response = self.client.chat.completions.create(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/openai/_utils/_utils.py", line 286, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/openai/resources/chat/completions/completions.py", line 1192, in create
    return self._post(
           ^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/openai/_base_client.py", line 1297, in post
    return cast(ResponseT, self.request(cast_to, opts, stream=stream, stream_cls=stream_cls))
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/openai/_base_client.py", line 1005, in request
    response = self._client.send(
               ^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpx/_client.py", line 914, in send
    response = self._send_handling_auth(
               ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpx/_client.py", line 942, in _send_handling_auth
    response = self._send_handling_redirects(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpx/_client.py", line 979, in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpx/_client.py", line 1014, in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpx/_transports/default.py", line 250, in handle_request
    resp = self._pool.handle_request(req)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpcore/_sync/connection_pool.py", line 256, in handle_request
    raise exc from None
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpcore/_sync/connection_pool.py", line 236, in handle_request
    response = connection.handle_request(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpcore/_sync/connection.py", line 103, in handle_request
    return self._connection.handle_request(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpcore/_sync/http11.py", line 136, in handle_request
    raise exc
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpcore/_sync/http11.py", line 106, in handle_request
    ) = self._receive_response_headers(**kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpcore/_sync/http11.py", line 177, in _receive_response_headers
    event = self._receive_event(timeout=timeout)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpcore/_sync/http11.py", line 217, in _receive_event
    data = self._network_stream.read(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/quyen/miniconda3/envs/py312/lib/python3.12/site-packages/httpcore/_backends/sync.py", line 128, in read
    return self._sock.recv(max_bytes)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
KeyboardInterrupt

(py312) quyen@Legion-5:~/Documents/KGsAuto$ 