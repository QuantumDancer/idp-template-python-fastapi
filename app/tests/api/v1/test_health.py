from fastapi.testclient import TestClient


def test_liveness_returns_200(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_200_with_no_checks(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {}}


def test_correlation_id_header_present(client: TestClient) -> None:
    for endpoint in ["/api/v1/health/live", "/api/v1/health/ready"]:
        response = client.get(endpoint)
        assert "x-correlation-id" in response.headers, (
            f"Missing X-Correlation-ID header on {endpoint}"
        )


def test_metrics_endpoint_reachable(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
