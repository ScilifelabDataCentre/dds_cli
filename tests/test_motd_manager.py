from requests_mock.mocker import Mocker
from dds_cli import DDSEndpoint
from typing import Dict
from dds_cli import motd_manager

def test_list_all_active_motds():
    """List all active motds."""
    response_json: Dict = {}

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.MOTD, status_code=200, json=response_json)

        with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
            mtdm.list_all_active_motds(table=True)
            