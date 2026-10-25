"""Saved projects ("history"): SQLite rows + their own photo copies (real files in a temp folder)."""

import io
import os
import time

import pytest
from PIL import Image
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.history import SaveCampaignRequest
from app.services import history_service
from app.services.storage_service import get_storage


def make_upload(color="orange", size=(300, 200)) -> tuple[str, bytes]:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    data = buf.getvalue()
    return get_storage().save_original(data, "png"), data


def save(image_id, name="Summer launch", **state):
    return history_service.save_campaign(SaveCampaignRequest(
        image_id=image_id, name=name, product_name="Ring",
        state=state or {"details": {"product_name": "Ring"}, "style": "luxury"}))


def test_save_list_and_newest_first(storage_env):
    a, _ = make_upload()
    b, _ = make_upload("blue")
    first = save(a, "First")
    second = save(b, "Second")
    listed = history_service.list_campaigns()
    assert [c.name for c in listed] == ["Second", "First"]
    assert listed[0].id == second.id and listed[1].id == first.id
    assert listed[0].thumbnail_url == f"/api/history/{second.id}/thumbnail"


def test_thumbnail_is_a_small_jpeg(storage_env):
    image_id, _ = make_upload(size=(900, 400))
    summary = save(image_id)
    with Image.open(history_service.get_thumbnail(summary.id)) as thumb:
        assert thumb.format == "JPEG" and thumb.size == (360, 360)


def test_open_restores_photo_under_new_id_and_returns_state(storage_env):
    image_id, data = make_upload()
    summary = save(image_id, state_marker="kept", nested={"a": [1, 2]})
    opened = history_service.open_campaign(summary.id)
    assert opened.image.id != image_id  # fresh temporary upload
    assert get_storage().find_original(opened.image.id).read_bytes() == data
    assert opened.state == {"state_marker": "kept", "nested": {"a": [1, 2]}}
    assert (opened.image.width, opened.image.height) == (300, 200)


def test_saved_project_survives_expiry_of_the_temporary_upload(storage_env):
    image_id, data = make_upload()
    summary = save(image_id)
    path = get_storage().find_original(image_id)
    old = time.time() - 72 * 3600
    os.utime(path, (old, old))
    assert get_storage().cleanup_expired(24) == 1  # the temporary upload is removed...
    assert get_storage().find_original(image_id) is None
    opened = history_service.open_campaign(summary.id)  # ...but the saved project still opens
    assert get_storage().find_original(opened.image.id).read_bytes() == data


def test_delete_removes_row_and_files(storage_env):
    image_id, _ = make_upload()
    summary = save(image_id)
    photo = history_service.get_photo(summary.id)
    thumb = history_service.get_thumbnail(summary.id)
    history_service.delete_campaign(summary.id)
    assert not photo.exists() and not thumb.exists()
    assert history_service.list_campaigns() == []
    with pytest.raises(AppError) as exc:
        history_service.open_campaign(summary.id)
    assert exc.value.status_code == 404


def test_unknown_project_and_unknown_photo(storage_env):
    with pytest.raises(AppError) as e1:
        history_service.open_campaign(999)
    assert e1.value.status_code == 404
    with pytest.raises(AppError) as e2:
        save("0" * 32)
    assert e2.value.status_code == 404


def test_missing_photo_file_is_reported_cleanly(storage_env):
    image_id, _ = make_upload()
    summary = save(image_id)
    history_service.get_photo(summary.id).unlink()
    for call in (history_service.open_campaign, history_service.get_photo):
        with pytest.raises(AppError) as exc:
            call(summary.id)
        assert exc.value.status_code == 404


def test_history_limit(storage_env):
    image_id, _ = make_upload(size=(20, 20))
    original = history_service.MAX_CAMPAIGNS
    history_service.MAX_CAMPAIGNS = 3
    try:
        for i in range(3):
            save(image_id, f"P{i}")
        with pytest.raises(AppError) as exc:
            save(image_id, "one too many")
        assert exc.value.status_code == 409
    finally:
        history_service.MAX_CAMPAIGNS = original


def test_request_validation():
    with pytest.raises(ValidationError):
        SaveCampaignRequest(image_id="x", name="  ", state={})
    with pytest.raises(ValidationError):
        SaveCampaignRequest(image_id="x", name="ok", state={"blob": "x" * 250_000})
    assert SaveCampaignRequest(image_id="x", name="  My   project ", state={}).name == "My project"
