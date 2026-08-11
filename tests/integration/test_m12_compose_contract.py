from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]


def test_compose_declares_read_only_staging_and_healthcheck() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = compose["services"]["scholartrace"]
    assert service["read_only"] is True
    assert "no-new-privileges:true" in service["security_opt"]
    assert "ALL" in service["cap_drop"]
    assert any("/app/delivery:ro" in mount for mount in service["volumes"])
    assert service["healthcheck"]["test"][0] == "CMD"
    assert "health" in " ".join(service["healthcheck"]["test"])
    assert "--delivery-manifest" in service["command"]


def test_dockerfile_runs_non_root_and_has_healthcheck() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "USER scholartrace" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "pip install --no-cache-dir ." in dockerfile
