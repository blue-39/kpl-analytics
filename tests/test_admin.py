from __future__ import annotations

from threading import Event
from time import monotonic, sleep

import pytest
from fastapi.testclient import TestClient

from kpl_analytics.api.admin import JobBusyError, JobManager
from kpl_analytics.api.main import create_app


def _wait_for_job(client: TestClient) -> dict:
    deadline = monotonic() + 3
    while monotonic() < deadline:
        job = client.get("/api/admin/job").json()
        if job["status"] != "running":
            return job
        sleep(0.01)
    raise AssertionError("background job did not finish")


def test_job_manager_rejects_a_second_concurrent_operation():
    manager = JobManager()
    release = Event()

    manager.start("first", lambda _: release.wait(1) or {"ok": True})
    with pytest.raises(JobBusyError):
        manager.start("second", lambda _: {"ok": True})
    release.set()


def test_admin_status_and_audit_job(warehouse):
    app = create_app(warehouse.settings)
    with TestClient(app) as client:
        status = client.get("/api/admin/status")
        started = client.post("/api/admin/audit")
        job = _wait_for_job(client)

    assert status.status_code == 200
    assert status.json()["meta"]["coverage"]["battles"] == 18
    assert started.status_code == 202
    assert job["status"] == "succeeded"
    assert job["result"]["ok"] is True


def test_llm_runtime_configuration_never_returns_the_secret(warehouse):
    app = create_app(warehouse.settings)
    secret = "test-only-secret"
    with TestClient(app) as client:
        rejected = client.post(
            "/api/settings/llm",
            json={
                "endpoint": "http://example.com/v1/chat/completions",
                "model": "example-model",
                "api_key": secret,
            },
        )
        configured = client.post(
            "/api/settings/llm",
            json={
                "endpoint": "https://example.com/v1/chat/completions",
                "model": "example-model",
                "api_key": secret,
            },
        )
        status = client.get("/api/settings/llm")
        cleared = client.post("/api/settings/llm/clear")

    assert rejected.status_code == 422
    assert configured.json() == {
        "configured": True,
        "endpoint": "https://example.com/v1/chat/completions",
        "model": "example-model",
        "has_api_key": True,
        "source": "runtime",
    }
    assert secret not in configured.text
    assert secret not in status.text
    assert cleared.json()["configured"] is False
