from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.domain.models import Asset, Project
from app.main import app
from app.api.v1.images import get_storage
from app.storage.local import LocalFilesystemStorage


def image_bytes(format: str, size: tuple[int, int] = (32, 24), color: str = "red") -> bytes:
    image = Image.new("RGB", size, color)
    output = io.BytesIO()
    image.save(output, format=format)
    return output.getvalue()


@pytest.fixture
def upload_context(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    project_id = uuid.uuid4()
    session.add(Project(id=project_id, name="Test project"))
    session.commit()
    settings = Settings(
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/house_renovation",
        storage_root=str(tmp_path),
        min_image_width=16,
        min_image_height=16,
        max_upload_bytes=1024 * 1024,
        blur_variance_threshold=0,
    )
    storage = LocalFilesystemStorage(tmp_path)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_storage] = lambda: storage
    yield session, project_id, storage, settings
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def upload(client: TestClient, project_id: uuid.UUID, filename: str, content_type: str, content: bytes):
    return client.post(
        f"/api/v1/projects/{project_id}/images",
        files={"file": (filename, content, content_type)},
    )


def test_created_project_can_immediately_receive_image(upload_context):
    _, _, storage, _ = upload_context
    with TestClient(app) as client:
        project_response = client.post("/api/v1/projects", json={"name": "Created project"})
        project_id = uuid.UUID(project_response.json()["id"])
        response = upload(client, project_id, "front.png", "image/png", image_bytes("PNG"))

    assert project_response.status_code == 200
    assert response.status_code == 200
    assert response.json()["project_id"] == str(project_id)


@pytest.mark.parametrize(
    ("filename", "content_type", "format"),
    [("front.jpg", "image/jpeg", "JPEG"), ("front.png", "image/png", "PNG")],
)
def test_valid_image_uploads_are_stored(upload_context, filename, content_type, format):
    _, project_id, storage, _ = upload_context
    with TestClient(app) as client:
        response = upload(client, project_id, filename, content_type, image_bytes(format))

    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "accepted"
    assert body["width"] == 32
    assert body["height"] == 24
    assert storage.path_for(f"projects/{project_id}/images/{body['image_id']}/processing.png").exists()


def test_successful_canonical_processing_image_is_rgb_png(upload_context):
    session, project_id, storage, _ = upload_context
    with TestClient(app) as client:
        response = upload(client, project_id, "house.webp", "image/webp", image_bytes("WEBP"))

    assert response.status_code == 200
    asset = session.get(Asset, uuid.UUID(response.json()["processing_asset_id"]))
    assert asset.media_type == "image/png"
    with storage.open(asset.storage_key) as stored:
        canonical = Image.open(stored)
        assert canonical.format == "PNG"
        assert canonical.mode == "RGB"


def test_unsupported_corrupt_and_oversized_files_are_rejected(upload_context):
    _, project_id, _, settings = upload_context
    with TestClient(app) as client:
        unsupported = upload(client, project_id, "house.gif", "image/gif", b"GIF89a")
        corrupt = upload(client, project_id, "house.jpg", "image/jpeg", b"not an image")
        settings.max_upload_bytes = 10
        oversized = upload(client, project_id, "house.jpg", "image/jpeg", image_bytes("JPEG"))

    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "UNSUPPORTED_FILE"
    assert corrupt.status_code == 422
    assert corrupt.json()["error"]["code"] == "CORRUPTED_IMAGE"
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_small_image_and_warning_response(upload_context):
    _, project_id, _, settings = upload_context
    with TestClient(app) as client:
        settings.min_image_width = 64
        small = upload(client, project_id, "small.jpg", "image/jpeg", image_bytes("JPEG"))
        settings.min_image_width = 16
        warning = upload(client, project_id, "wide.jpg", "image/jpeg", image_bytes("JPEG", (200, 20)))

    assert small.status_code == 422
    assert small.json()["error"]["code"] == "IMAGE_TOO_SMALL"
    assert warning.status_code == 200
    assert warning.json()["validation_status"] == "accepted_with_warnings"
    assert warning.json()["validation_reasons"][0]["code"] == "EXTREME_ASPECT_RATIO"


def test_image_over_maximum_dimensions_is_rejected(upload_context):
    _, project_id, _, settings = upload_context
    settings.max_image_width = 64
    with TestClient(app) as client:
        response = upload(client, project_id, "large.jpg", "image/jpeg", image_bytes("JPEG", (80, 40)))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE_DIMENSIONS"


def test_exif_orientation_is_normalized_and_filename_is_not_storage_path(upload_context):
    session, project_id, storage, _ = upload_context
    image = Image.new("RGB", (20, 40), "blue")
    exif = image.getexif()
    exif[274] = 6
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif.tobytes())
    with TestClient(app) as client:
        response = upload(client, project_id, "../../secret.jpg", "image/jpeg", output.getvalue())

    assert response.status_code == 200
    body = response.json()
    assert body["width"] == 40
    assert body["height"] == 20
    original = session.get(Asset, uuid.UUID(body["original_asset_id"]))
    assert "secret.jpg" not in original.storage_key
    assert storage.path_for(original.storage_key).exists()


def test_nonexistent_project_is_rejected(upload_context):
    _, _, _, _ = upload_context
    with TestClient(app) as client:
        response = upload(client, uuid.uuid4(), "house.jpg", "image/jpeg", image_bytes("JPEG"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"