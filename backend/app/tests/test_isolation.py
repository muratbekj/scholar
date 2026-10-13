"""Acceptance: two X-Client-Id values cannot see each other's documents or sessions (cloud mode)."""
import uuid

A, B = str(uuid.uuid4()), str(uuid.uuid4())
MARKER = "zebracorn"
DOC = ("Chloroplasts capture light energy in the stroma. " * 40 + f"The secret marker is {MARKER}.").encode()


def h(client_id):
    return {"X-Client-Id": client_id}


def upload(client, client_id):
    response = client.post("/files/upload", params={"study_mode": "qa"},
                           files={"file": ("notes.txt", DOC, "text/plain")}, headers=h(client_id))
    assert response.status_code == 200, response.text
    return response.json()["file_id"]


def test_missing_or_invalid_client_id_is_rejected(cloud_app):
    assert cloud_app.client.get("/files/stats").status_code == 400
    assert cloud_app.client.get("/files/stats", headers={"X-Client-Id": "nope"}).status_code == 400


def test_other_client_gets_not_found_for_file_reads(cloud_app):
    client = cloud_app.client
    file_id = upload(client, A)
    assert MARKER in client.get(f"/files/{file_id}/text", headers=h(A)).text
    for path in (f"/files/info/{file_id}", f"/files/{file_id}/text", f"/files/{file_id}/chunks"):
        response = client.get(path, headers=h(B))
        assert response.status_code == 404, path
        assert MARKER not in response.text


def test_other_client_search_finds_nothing(cloud_app):
    client = cloud_app.client
    file_id = upload(client, A)
    mine = client.get("/files/search", params={"query": "chloroplast light", "file_id": file_id}, headers=h(A))
    assert mine.json()["total_results"] > 0
    for params in ({"query": "chloroplast light", "file_id": file_id}, {"query": "chloroplast light"}):
        theirs = client.get("/files/search", params=params, headers=h(B))
        assert theirs.status_code == 200 and theirs.json()["total_results"] == 0


def test_other_client_generation_behaves_like_an_unknown_file(cloud_app):
    client = cloud_app.client
    file_id = upload(client, A)
    unknown = str(uuid.uuid4())
    for path, body in (("/quiz/generate", {"filename": "notes.txt", "num_questions": 2}),
                       ("/flashcards/generate", {"filename": "notes.txt"})):
        theirs = client.post(path, json={**body, "file_id": file_id}, headers=h(B))
        missing = client.post(path, json={**body, "file_id": unknown}, headers=h(B))
        assert theirs.status_code == missing.status_code != 200, path
        assert MARKER not in theirs.text
        assert client.post(path, json={**body, "file_id": file_id}, headers=h(A)).status_code == 200, path


def test_other_client_question_gets_no_document_content(cloud_app):
    client = cloud_app.client
    file_id = upload(client, A)
    answer = client.post("/qa/ask", json={"question": "What is the secret marker?", "file_id": file_id,
                                          "filename": "notes.txt"}, headers=h(B))
    assert answer.status_code == 200
    assert MARKER not in answer.text


def test_other_client_cannot_delete(cloud_app):
    client = cloud_app.client
    file_id = upload(client, A)
    assert client.delete(f"/files/{file_id}", headers=h(B)).status_code == 404
    assert MARKER in client.get(f"/files/{file_id}/text", headers=h(A)).text
    search = client.get("/files/search", params={"query": "chloroplast", "file_id": file_id}, headers=h(A))
    assert search.json()["total_results"] > 0


def test_sessions_are_private(cloud_app):
    client = cloud_app.client
    session_id = client.post("/qa/sessions", json={"file_id": "f", "filename": "n.txt"}, headers=h(A)).json()["session_id"]
    assert client.get(f"/qa/sessions/{session_id}", headers=h(B)).status_code == 404
    assert client.get("/qa/sessions", headers=h(B)).json() == []
    assert client.delete(f"/qa/sessions/{session_id}", headers=h(B)).status_code == 404
    assert [s["session_id"] for s in client.get("/qa/sessions", headers=h(A)).json()] == [session_id]


def test_quizzes_are_private(cloud_app):
    client = cloud_app.client
    file_id = upload(client, A)
    quiz_id = client.post("/quiz/generate", json={"file_id": file_id, "filename": "notes.txt", "num_questions": 2},
                          headers=h(A)).json()["quiz_id"]
    theirs = client.get(f"/quiz/{quiz_id}/questions", headers=h(B))
    missing = client.get(f"/quiz/{uuid.uuid4()}/questions", headers=h(B))
    assert theirs.status_code == missing.status_code != 200
    assert client.get(f"/quiz/{quiz_id}/questions", headers=h(A)).status_code == 200
