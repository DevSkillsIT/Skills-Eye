from contextlib import contextmanager
from pathlib import Path
from typing import Callable

import sys


BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
for entry in (str(ROOT_DIR), str(BACKEND_DIR)):
  if entry not in sys.path:
    sys.path.insert(0, entry)

from fastapi.testclient import TestClient

from app import app
from api import metadata_fields_manager as mfm
from core.server_utils import ServerCapability, ServerInfo, ServerRole


class DummyMultiConfigManager:
    """Return pre-configured YAML text without touching SSH."""

    def __init__(self, yaml_factory: Callable[[], str]):
        self._yaml_factory = yaml_factory

    def get_file_content_raw(self, file_path: str, hostname: str | None = None) -> str:
        print(f"[TEST] reading {file_path} for hostname={hostname}")
        return self._yaml_factory()


@contextmanager
def patched_environment(yaml_factory: Callable[[], str]):
    """Patch dependencies used by the sync-status endpoint."""

    dummy_info = ServerInfo(
        hostname="fake-host",
        port=22,
        capabilities=[ServerCapability.PROMETHEUS],
        role=ServerRole.MASTER,
        prometheus_config_path="/etc/prometheus/prometheus.yml",
        has_prometheus=True,
    )

    class _Detector:
        def detect_server_capabilities(self, hostname: str, use_cache: bool = False) -> ServerInfo:
            print(f"[TEST] detect_server_capabilities called for {hostname}")
            return dummy_info

    detector = _Detector()

    from unittest.mock import patch

    with (
        patch.object(mfm, "MultiConfigManager", lambda: DummyMultiConfigManager(yaml_factory)),
        patch.object(mfm, "get_server_detector", lambda: detector),
    ):
        yield


def run_case(name: str, yaml_text: str) -> None:
    print("\n" + "=" * 80)
    print(f"CASE: {name}")
    print("=" * 80)

    with patched_environment(lambda: yaml_text):
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/metadata-fields/sync-status",
                params={"server_id": "fake-host:22"},
            )

        print(f"Status code: {response.status_code}")
        payload = response.json()
        print(f"fallback_used: {payload.get('fallback_used')}\n")


SIMPLE_YAML = """
global:
  scrape_interval: 30s
scrape_configs:
  - job_name: direct_relabel
    consul_sd_configs:
      - server: 'localhost:8500'
    relabel_configs:
      - source_labels: ['__meta_consul_service_metadata_company']
        target_label: company
      - source_labels: ['__meta_consul_service_metadata_project']
        target_label: project
""".strip()

FIRST_JOB_EMPTY_YAML = """
global:
  scrape_interval: 30s
scrape_configs:
  - job_name: first_without_relabel
    consul_sd_configs:
      - server: 'localhost:8500'
    relabel_configs: []
  - job_name: second_with_labels
    consul_sd_configs:
      - server: 'localhost:8500'
    relabel_configs:
      - source_labels: ['__meta_consul_service_metadata_company']
        target_label: company
      - source_labels: ['__meta_consul_service_metadata_project']
        target_label: project
""".strip()

ADVANCED_DICT_YAML = """
common_relabel:
  shared: &shared_rules
    - source_labels: ['__meta_consul_service_metadata_company']
      target_label: company
    - source_labels: ['__meta_consul_service_metadata_project']
      target_label: project
scrape_configs:
  - job_name: uses_dict_alias
    consul_sd_configs:
      - server: 'localhost:8500'
    relabel_configs:
      shared: *shared_rules
""".strip()


if __name__ == "__main__":
    run_case("Normal relabels (no fallback)", SIMPLE_YAML)
    run_case("First job without relabels", FIRST_JOB_EMPTY_YAML)
    run_case("Advanced dict alias", ADVANCED_DICT_YAML)
