import pytest

from flowsint_crypto_compliance.demo.microservices import (
    get_mesh_topology,
    list_microservices,
    run_microservice,
)
from flowsint_crypto_compliance.demo.osint_console import OSINTConsole


def test_microservices_count_and_osint_cluster():
    services = list_microservices()
    assert len(services) == 24
    mesh = get_mesh_topology()
    assert mesh["total_services"] == 24
    assert mesh["osint_cluster_size"] >= 8
    assert "OSINT" in str(mesh["layers"])


@pytest.mark.asyncio
async def test_run_osint_fusion_service():
    result = await run_microservice("ms-osint-fusion")
    assert result["status"] == "completed"
    assert result["scenario_id"] == "p2p_rub_offshore"
    assert "Fusion" in result["summary_ru"] or "fusion" in result["summary_ru"].lower()
    assert result["metrics"]["graph_nodes"] > 0


@pytest.mark.asyncio
async def test_run_microservice_with_scenario():
    result = await run_microservice("ms-osint-fusion", scenario_id="sbp_gray_hub")
    assert result["scenario_id"] == "sbp_gray_hub"
    assert result["metrics"]["graph_nodes"] > 0


@pytest.mark.asyncio
async def test_osint_console_fusion():
    console = OSINTConsole()
    assert len(console.sources()) == 9
    assert len(console.pipeline()) == 8
    status = console.status()
    assert status["sovereign_mode"] is True
    result = await console.run_fusion("p2p_rub_offshore")
    assert len(result["steps"]) == 8
    assert result["report"]["illegal_flow_score"] >= 0
