from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import AnalyzeResponse, AgentAnalyzeResponse, MultiAgentAnalyzeResponse


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_csv():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "sales": [100, 200, 150],
        "category": ["A", "B", "A"],
    })
    return df.to_csv(index=False).encode("utf-8")


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "model" in data


class TestAnalyzeEndpoint:
    def test_summary_works(self, client, sample_csv):
        response = client.post(
            "/analyze",
            files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")},
            data={"analysis_type": "summary"},
        )
        assert response.status_code == 200
        data = AnalyzeResponse(**response.json())
        assert data.success is True
        assert data.analysis_type == "summary"
        assert data.rows == 3

    def test_invalid_analysis_type_fails(self, client, sample_csv):
        response = client.post(
            "/analyze",
            files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")},
            data={"analysis_type": "invalid_type"},
        )
        assert response.status_code == 400
        assert "Unknown analysis type" in response.json()["detail"]

    def test_missing_file_fails(self, client):
        response = client.post(
            "/analyze",
            data={"analysis_type": "summary"},
        )
        assert response.status_code == 422

    def test_non_csv_file_fails(self, client):
        response = client.post(
            "/analyze",
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
            data={"analysis_type": "summary"},
        )
        assert response.status_code == 400
        assert "Only CSV" in response.json()["detail"]

    def test_missing_analysis_type_fails(self, client, sample_csv):
        response = client.post(
            "/analyze",
            files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")},
        )
        assert response.status_code == 422


class TestAgentAnalyzeEndpoint:
    def test_summary_works(self, client, sample_csv):
        response = client.post(
            "/agent/analyze",
            files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")},
            data={"question": "summarize this dataset"},
        )
        assert response.status_code == 200
        data = AgentAnalyzeResponse(**response.json())
        assert data.success is True
        assert "summary" in data.selected_analysis_types

    def test_empty_question_fails(self, client, sample_csv):
        response = client.post(
            "/agent/analyze",
            files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")},
            data={"question": ""},
        )
        assert response.status_code in (400, 422)

    def test_missing_file_fails(self, client):
        response = client.post(
            "/agent/analyze",
            data={"question": "summarize this"},
        )
        assert response.status_code == 422

    def test_non_csv_file_fails(self, client):
        response = client.post(
            "/agent/analyze",
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
            data={"question": "summarize this"},
        )
        assert response.status_code == 400
        assert "Only CSV" in response.json()["detail"]


class TestMultiAgentAnalyzeEndpoint:
    def test_summary_works(self, client, sample_csv):
        response = client.post(
            "/multi-agent/analyze",
            files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")},
            data={"question": "summarize this dataset"},
        )
        assert response.status_code == 200
        data = MultiAgentAnalyzeResponse(**response.json())
        assert data.success is True
        assert "summary" in data.selected_analysis_types

    def test_empty_question_fails(self, client, sample_csv):
        response = client.post(
            "/multi-agent/analyze",
            files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")},
            data={"question": ""},
        )
        assert response.status_code in (400, 422)

    def test_missing_file_fails(self, client):
        response = client.post(
            "/multi-agent/analyze",
            data={"question": "summarize this"},
        )
        assert response.status_code == 422

    def test_non_csv_file_fails(self, client):
        response = client.post(
            "/multi-agent/analyze",
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
            data={"question": "summarize this"},
        )
        assert response.status_code == 400
        assert "Only CSV" in response.json()["detail"]
