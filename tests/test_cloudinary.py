import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestCloudinaryUpload:
    ENDPOINT = "/api/v1/upload"

    @pytest.fixture
    def mock_image_file(self):
        return io.BytesIO(b"fake-image-bytes")

    @pytest.fixture
    def mock_cloudinary_upload(self):
        with patch("app.modules.cloudinary.router.cloudinary.uploader.upload") as mock:
            mock.return_value = {"secure_url": "https://res.cloudinary.com/demo/image/upload/v1/test.jpg"}
            yield mock

    def test_upload_ok(self, client: TestClient, admin_headers, mock_image_file,
                       mock_cloudinary_upload):
        mock_image_file.name = "test.jpg"
        resp = client.post(
            self.ENDPOINT,
            files={"file": ("test.jpg", mock_image_file, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://res.cloudinary.com/demo/image/upload/v1/test.jpg"
        mock_cloudinary_upload.assert_called_once()

    def test_upload_forbidden_client(self, client: TestClient, client_headers,
                                      mock_image_file):
        mock_image_file.name = "test.jpg"
        resp = client.post(
            self.ENDPOINT,
            files={"file": ("test.jpg", mock_image_file, "image/jpeg")},
        )
        assert resp.status_code == 403

    def test_upload_unauthenticated(self, client: TestClient, mock_image_file):
        client.cookies.clear()
        mock_image_file.name = "test.jpg"
        resp = client.post(
            self.ENDPOINT,
            files={"file": ("test.jpg", mock_image_file, "image/jpeg")},
        )
        assert resp.status_code == 401

    def test_upload_not_an_image(self, client: TestClient, admin_headers):
        resp = client.post(
            self.ENDPOINT,
            files={"file": ("doc.pdf", io.BytesIO(b"pdf"), "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Solo se permiten archivos de imagen" in resp.text

    def test_upload_cloudinary_error(self, client: TestClient, admin_headers,
                                      mock_image_file, mock_cloudinary_upload):
        mock_cloudinary_upload.side_effect = Exception("Connection refused")
        mock_image_file.name = "test.jpg"
        resp = client.post(
            self.ENDPOINT,
            files={"file": ("test.jpg", mock_image_file, "image/jpeg")},
        )
        assert resp.status_code == 502
        assert "Error al subir la imagen" in resp.text
