import contextlib
import io


# ==================================================
# IMPORTS
# ==================================================
#
# Some PQC/liboqs imports can write diagnostic
# output to stdout. MCP stdio uses stdout for
# JSON-RPC, so suppress import-time stdout.
# ==================================================

with contextlib.redirect_stdout(
    io.StringIO()
):

    from mcp.server.mcpserver import MCPServer

    from mcp_server.db import (
        create_mcp_app
    )

    from mcp_server.tools import (
        get_user,
        get_credential,
        check_consent,
        verify_pqc,
        verify_credential_complete,
        check_revocation,
        verify_blockchain,
        get_verification_history,
    )

    mcp_app = create_mcp_app()


# ==================================================
# MCP SERVER
# ==================================================

mcp = MCPServer(
    "QuantumSafeKYC"
)


# ==================================================
# SYSTEM STATUS
# ==================================================

@mcp.tool()
def system_status() -> dict:

    return {
        "status": "success",
        "service": "QuantumSafeKYC MCP Server",
        "mcp": "connected",
        "message": (
            "MCP server is running successfully"
        ),
    }


# ==================================================
# GET USER
# ==================================================

@mcp.tool()
def get_user_tool(
    user_uuid: str,
) -> dict:

    with mcp_app.app_context():

        return get_user(
            user_uuid
        )


# ==================================================
# GET CREDENTIAL
# ==================================================

@mcp.tool()
def get_credential_tool(
    credential_uuid: str,
) -> dict:

    with mcp_app.app_context():

        return get_credential(
            credential_uuid
        )


# ==================================================
# CHECK CONSENT
# ==================================================

@mcp.tool()
def check_consent_tool(
    user_uuid: str,
    credential_uuid: str,
    verifier_id: str,
    purpose: str,
) -> dict:

    with mcp_app.app_context():

        return check_consent(
            user_uuid=user_uuid,
            credential_uuid=credential_uuid,
            verifier_id=verifier_id,
            purpose=purpose,
        )


# ==================================================
# VERIFY PQC
# ==================================================

@mcp.tool()
def verify_pqc_tool(
    credential_uuid: str,
) -> dict:

    with mcp_app.app_context():

        return verify_pqc(
            credential_uuid
        )


# ==================================================
# VERIFY CREDENTIAL
# ==================================================

@mcp.tool()
def verify_credential_tool(
    credential_uuid: str,
) -> dict:

    with mcp_app.app_context():

        return verify_credential_complete(
            credential_uuid
        )


# ==================================================
# CHECK REVOCATION
# ==================================================

@mcp.tool()
def check_revocation_tool(
    credential_uuid: str,
) -> dict:

    with mcp_app.app_context():

        return check_revocation(
            credential_uuid
        )


# ==================================================
# VERIFY BLOCKCHAIN
# ==================================================

@mcp.tool()
def verify_blockchain_tool(
    credential_uuid: str,
) -> dict:

    with mcp_app.app_context():

        return verify_blockchain(
            credential_uuid
        )

# ==================================================
# GET VERIFICATION HISTORY
# ==================================================

@mcp.tool()
def get_verification_history_tool(
    credential_uuid: str,
) -> dict:

    with mcp_app.app_context():

        return get_verification_history(
            credential_uuid
        )


# ==================================================
# RUN MCP SERVER
# ==================================================

if __name__ == "__main__":

    mcp.run()