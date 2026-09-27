"""HTTP regression tests for /api/knowledge/* (rest_knowledge.py).

Every knowledge write (create/update/delete) re-indexes the bot's whole
knowledge tree into ChromaDB under collection `Collection{bot_id}`
(knowledge_svc.reindex_bot). That collection is not cleaned up
here -- bot ids are never reused, so leftover per-bot Chroma collections
from deleted test bots don't corrupt other tests, they just accumulate in
the dev ChromaDB instance.
"""

from pathlib import Path

from src.config.constant import GUEST_ROLE, USER_ROLE
from src.models import Knowledge

from .helpers import assert_error

SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample.pdf"


def test_create_empty_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/knowledge/save/{bot.id}/this_is_a_root_chapter",
        json={},
        headers=headers,
    )

    # KnowledgeDto has no bot_id field, only chapter-local fields.
    assert response.status_code == 200, response.text
    assert response.json()["knowledge_dad_id"] == "this_is_a_root_chapter"


def test_create_empty_forbidden_for_guest(http_client, api_base_url, create_user, create_bot, login):
    owner, _owner_password = create_user(role=USER_ROLE)
    bot = create_bot(owner.id)
    guest, guest_password = create_user(role=GUEST_ROLE)
    headers = login(guest.mail, guest_password)

    response = http_client.post(
        f"{api_base_url}/knowledge/save/{bot.id}/this_is_a_root_chapter",
        json={},
        headers=headers,
    )

    assert_error(response, 403, "Access denied")


def test_save_with_pdf_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    # knowledge_svc.save_pdf() saves under the pdf_file *string field* from
    # the JSON data blob, not the uploaded file's own name -- both must be
    # supplied and they must agree, or it 500s on `None.endswith(".pdf")`.
    with open(SAMPLE_PDF, "rb") as f:
        response = http_client.post(
            f"{api_base_url}/knowledge/save/{bot.id}",
            headers=headers,
            data={
                "data": '{"name": "Chapter 1", "content": "Some content", "pdf_file": "sample.pdf"}'
            },
            files={"pdf": ("sample.pdf", f, "application/pdf")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Chapter 1"
    assert body["pdf_file"] == "sample.pdf"


def test_save_without_pdf_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/knowledge/save/{bot.id}",
        headers=headers,
        data={"data": '{"name": "Chapter 2", "content": "Text"}'},
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Chapter 2"


def test_save_sets_vector_synced_at(http_client, api_base_url, create_user, create_bot, login):
    # Every knowledge write re-ingests the chapter into ChromaDB and stamps
    # vector_synced_at (knowledge_svc._ingest_knowledge_node), regardless of
    # whether it was a create or an update -- see
    # KnowledgeDto.vector_synced_at / Knowledge.vector_synced_at.
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/knowledge/save/{bot.id}",
        headers=headers,
        data={"data": '{"name": "Chapter Sync", "content": "Text"}'},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["vector_synced_at"] is not None
    assert body["updated_at"]


def test_save_update_refreshes_vector_synced_at(
    http_client, api_base_url, create_user, create_bot, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    created = http_client.post(
        f"{api_base_url}/knowledge/save/{bot.id}",
        headers=headers,
        data={"data": '{"name": "Chapter Original", "content": "Text"}'},
    )
    assert created.status_code == 200, created.text
    knowledge_id = created.json()["id"]
    first_sync = created.json()["vector_synced_at"]
    assert first_sync is not None

    updated = http_client.put(
        f"{api_base_url}/knowledge/save/{bot.id}",
        headers=headers,
        data={
            "data": f'{{"id": {knowledge_id}, "name": "Chapter Updated", "content": "New text"}}'
        },
    )

    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["name"] == "Chapter Updated"
    assert body["vector_synced_at"] is not None


def test_create_empty_sets_vector_synced_at(
    http_client, api_base_url, create_user, create_bot, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/knowledge/save/{bot.id}/this_is_a_root_chapter",
        json={},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["vector_synced_at"] is not None


def test_patch_not_implemented(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.patch(f"{api_base_url}/knowledge/1", headers=headers)

    assert response.status_code == 501, response.text


def test_save_imported_golden_path(
    http_client, api_base_url, create_user, create_bot, login
):
    # Knowledge_svc._perform_save_imported_knowledges reads knowledge_name/
    # knowledge_content/knowledge_dad_id/indice/children_ref_id verbatim
    # (KeyError if any is missing) -- these field names differ from the
    # KnowledgeRequest DTO used elsewhere in this blueprint (name/content).
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/knowledge/save_knowledges/{bot.id}",
        json={
            "importedChapters": [
                {
                    "bot_id": bot.id,
                    "knowledge_name": "Imported 1",
                    "knowledge_content": "x",
                    "knowledge_dad_id": "this_is_a_root_chapter",
                    "indice": 0,
                    "children_ref_id": "",
                }
            ]
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_save_imported_forbidden_not_owner(
    http_client, api_base_url, create_user, create_bot, login
):
    owner, _owner_password = create_user(role=USER_ROLE)
    bot = create_bot(owner.id)
    stranger, stranger_password = create_user(role=USER_ROLE)
    headers = login(stranger.mail, stranger_password)

    response = http_client.post(
        f"{api_base_url}/knowledge/save_knowledges/{bot.id}",
        json={"importedChapters": [{"bot_id": bot.id, "name": "X"}]},
        headers=headers,
    )

    assert_error(response, 403, "not allowed")


def test_save_imported_no_data(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/knowledge/save_knowledges/{bot.id}",
        json={"importedChapters": []},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_get_knowledges_golden_path(
    http_client, api_base_url, create_user, create_bot, create_knowledge, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_knowledge(bot.id)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/knowledge/{bot.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_knowledge_golden_path(
    http_client, api_base_url, create_user, create_bot, create_knowledge, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    knowledge = create_knowledge(bot.id)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/knowledge/{bot.id}/{knowledge.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == knowledge.id


def test_get_knowledge_not_found(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/knowledge/{bot.id}/999999999", headers=headers
    )

    assert_error(response, 404, "not found")


def test_delete_knowledge_golden_path(
    http_client, api_base_url, create_user, create_bot, create_knowledge, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    knowledge = create_knowledge(bot.id)
    headers = login(user.mail, password)

    response = http_client.delete(
        f"{api_base_url}/knowledge/{knowledge.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Chapter deleted successfully"


def test_create_empty_numbers_chapters_and_delete_is_recursive(
    http_client, api_base_url, create_user, create_bot, login, db_session, track
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    def create_empty(dad_id):
        response = http_client.post(
            f"{api_base_url}/knowledge/save/{bot.id}/{dad_id}", json={}, headers=headers
        )
        assert response.status_code == 200, response.text
        track(Knowledge, response.json()["id"])
        return response.json()

    first = create_empty("this_is_a_root_chapter")
    second = create_empty("this_is_a_root_chapter")
    child = create_empty(first["children_ref_id"])
    assert (first["indice"], second["indice"], child["indice"]) == (1, 2, 1)

    response = http_client.delete(
        f"{api_base_url}/knowledge/{first['id']}", headers=headers
    )

    assert response.status_code == 200, response.text
    db_session.expire_all()
    remaining = {
        k.id: k.indice for k in db_session.query(Knowledge).filter_by(bot_id=bot.id)
    }
    assert remaining == {second["id"]: 1}


def test_delete_knowledge_leaves_other_bots_numbering_alone(
    http_client,
    api_base_url,
    create_user,
    create_bot,
    create_knowledge,
    login,
    db_session,
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    doomed = create_knowledge(
        bot.id, knowledge_dad_id="this_is_a_root_chapter", indice=1
    )
    other_user, _other_password = create_user(role=USER_ROLE)
    other_bot = create_bot(other_user.id)
    other = create_knowledge(
        other_bot.id, knowledge_dad_id="this_is_a_root_chapter", indice=1000
    )
    headers = login(user.mail, password)

    response = http_client.delete(
        f"{api_base_url}/knowledge/{doomed.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    db_session.expire_all()
    assert db_session.get(Knowledge, other.id).indice == 1000


def test_delete_imported_chapter_leaves_other_bots_chapters_alone(
    http_client, api_base_url, create_user, create_bot, login, db_session
):
    # Importing the same exported chapter tree into two bots gives both the
    # same children_ref_id values.
    user, password = create_user(role=USER_ROLE)
    bot_a, bot_b = create_bot(user.id), create_bot(user.id)
    headers = login(user.mail, password)
    tree = [
        {
            "knowledge_name": "Parent",
            "knowledge_content": "p",
            "knowledge_dad_id": "this_is_a_root_chapter",
            "indice": 1,
            "children_ref_id": "shared-parent-ref",
        },
        {
            "knowledge_name": "Child",
            "knowledge_content": "c",
            "knowledge_dad_id": "shared-parent-ref",
            "indice": 1,
            "children_ref_id": "shared-child-ref",
        },
    ]
    for bot in (bot_a, bot_b):
        response = http_client.post(
            f"{api_base_url}/knowledge/save_knowledges/{bot.id}",
            json={"importedChapters": tree},
            headers=headers,
        )
        assert response.status_code == 200, response.text
    parent_a = (
        db_session.query(Knowledge).filter_by(bot_id=bot_a.id, name="Parent").one()
    )

    response = http_client.delete(
        f"{api_base_url}/knowledge/{parent_a.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    db_session.expire_all()
    assert db_session.query(Knowledge).filter_by(bot_id=bot_a.id).count() == 0
    assert sorted(
        k.name for k in db_session.query(Knowledge).filter_by(bot_id=bot_b.id)
    ) == ["Child", "Parent"]


def test_delete_knowledge_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/knowledge/999999999", headers=headers)

    assert_error(response, 404, "not found")


def test_delete_all_golden_path(
    http_client,
    api_base_url,
    create_user,
    create_bot,
    create_knowledge,
    login,
    db_session,
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_knowledge(bot.id)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/knowledge/all/{bot.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "All knowledges deleted successfully"
    db_session.expire_all()
    assert db_session.query(Knowledge).filter_by(bot_id=bot.id).count() == 0


def test_delete_all_on_empty_bot_still_reports_success(
    http_client, api_base_url, create_user, create_bot, login
):
    # knowledge_svc.delete_all() returns True unconditionally unless a real
    # DB exception occurs, even when zero rows matched -- so the
    # controller's `if not success: return 404` branch is effectively
    # unreachable in practice.
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/knowledge/all/{bot.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "All knowledges deleted successfully"


def test_load_template_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/knowledge/load_template/{bot.id}/start", headers=headers
    )

    assert response.status_code == 200, response.text
