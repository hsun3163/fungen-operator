"""Small MCP adapter. Scientific confirmation is injected by the human client."""

import asyncio
import json
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.elicitation import ElicitationResult
from mcp.server.mcpserver import Elicit, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict

from .actions import PrepareConfig, CheckReadiness, InitiateRun, InspectRun, digest
from .harness import Harness
from .notebook import now


class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    approve: bool


class OperatorServer(MCPServer):
    async def call_tool(self, name, arguments, context=None):
        if set(arguments) != {"request"}:
            raise ToolError("Action tools accept only the structured request argument")
        return await super().call_tool(name, arguments, context)


def create_server(harness: Harness):
    server = OperatorServer("Fungen Operator")
    # Only in-flight approval proposals. The notebook owns all retained state.
    proposals = {}

    def confirmation(request: PrepareConfig):
        try:
            proposal = harness.propose_config(request)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        proposals[digest(request.model_dump())] = proposal
        if not proposal["scientific_changes"]:
            return Confirmation(approve=True)
        return Elicit(
            "Human approval is required before configuration or notebook materialization.\n"
            + json.dumps({"scientific_changes": proposal["scientific_changes"],
                          "proposal_fingerprint": proposal["fingerprint"],
                          "configfile": request.configfile}, indent=2), Confirmation)

    async def invoke(function, *args):
        try:
            return await asyncio.to_thread(function, *args)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool()
    async def prepare_config(
        request: PrepareConfig,
        confirmation_result: Annotated[ElicitationResult[Confirmation], Resolve(confirmation)],
    ) -> dict[str, Any]:
        """Prepare canonical config; scientific changes require client-mediated human approval."""
        proposal = proposals.pop(digest(request.model_dump()))
        if confirmation_result.action != "accept" or not confirmation_result.data.approve:
            return {"status": "approval_declined", "materialized": False}
        proof = None
        if proposal["scientific_changes"]:
            proof = {"fingerprint": proposal["fingerprint"], "scientific_changes": proposal["scientific_changes"],
                     "channel": "mcp_human_elicitation", "time": now(),
                     "backend": harness.deployment.backend}
        return await invoke(harness.prepare_config, proposal, proof)

    @server.tool()
    async def check_readiness(request: CheckReadiness) -> dict[str, Any]:
        """Execute the canonical dry-run and retain readiness or nothing-to-do evidence."""
        return await invoke(harness.run, "check_readiness", request)

    @server.tool()
    async def initiate_run(request: InitiateRun) -> dict[str, Any]:
        """Submit or normally resume the same graph through the fixed LSF/Snakemake cell."""
        return await invoke(harness.run, "initiate_run", request)

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    async def inspect_run(request: InspectRun) -> dict[str, Any]:
        """Read action history, scheduler states, logs, and requested file observations."""
        return await invoke(harness.inspect, request)

    return server
