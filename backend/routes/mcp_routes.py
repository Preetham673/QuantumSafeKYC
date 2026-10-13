from flask import Blueprint, jsonify, request
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

mcp_bp = Blueprint("mcp_bp", __name__, url_prefix="/api/mcp")

TOOL_DEFINITIONS = [
    {
        "name": "system_status",
        "description": "Check the health and operational status of the QuantumSafeKYC MCP server.",
        "parameters": {},
    },
    {
        "name": "get_user_tool",
        "description": "Retrieve user details and role status by user UUID.",
        "parameters": {
            "user_uuid": {"type": "string", "description": "UUID of the user", "required": True}
        },
    },
    {
        "name": "get_credential_tool",
        "description": "Retrieve PQC-protected credential details and status by credential UUID.",
        "parameters": {
            "credential_uuid": {"type": "string", "description": "UUID of the credential", "required": True}
        },
    },
    {
        "name": "check_consent_tool",
        "description": "Verify whether an active consent authorization exists for a verifier and purpose.",
        "parameters": {
            "user_uuid": {"type": "string", "description": "Holder user UUID", "required": True},
            "credential_uuid": {"type": "string", "description": "Credential UUID", "required": True},
            "verifier_id": {"type": "string", "description": "Verifier identifier", "required": True},
            "purpose": {"type": "string", "description": "Purpose for credential verification", "required": True},
        },
    },
    {
        "name": "verify_pqc_tool",
        "description": "Cryptographically verify the post-quantum ML-DSA-65 signature on a credential.",
        "parameters": {
            "credential_uuid": {"type": "string", "description": "Credential UUID to verify", "required": True}
        },
    },
    {
        "name": "verify_credential_tool",
        "description": "Execute complete verification pipeline: consent check, PQC signature verification, and revocation check.",
        "parameters": {
            "credential_uuid": {"type": "string", "description": "Credential UUID", "required": True},
            "verifier_id": {"type": "string", "description": "Verifier identifier", "required": True},
            "purpose": {"type": "string", "description": "Verification purpose", "required": True},
        },
    },
    {
        "name": "check_revocation_tool",
        "description": "Check if a credential has been revoked and inspect the revocation reason and timestamp.",
        "parameters": {
            "credential_uuid": {"type": "string", "description": "Credential UUID to check", "required": True}
        },
    },
    {
        "name": "verify_blockchain_tool",
        "description": "Verify the integrity of a credential against its immutable blockchain anchor.",
        "parameters": {
            "credential_uuid": {"type": "string", "description": "Credential UUID to verify against anchor", "required": True}
        },
    },
    {
        "name": "get_verification_history_tool",
        "description": "Retrieve the complete audit history of all verifications performed for a credential.",
        "parameters": {
            "credential_uuid": {"type": "string", "description": "Credential UUID", "required": True}
        },
    },
]


@mcp_bp.get("/status")
def mcp_status():
    return jsonify({
        "status": "success",
        "service": "QuantumSafeKYC MCP Bridge",
        "tools_count": len(TOOL_DEFINITIONS),
        "protocol": "Model Context Protocol (MCP) + REST Bridge",
    })


@mcp_bp.get("/tools")
def list_tools():
    return jsonify({
        "status": "success",
        "tools": TOOL_DEFINITIONS,
    })


@mcp_bp.post("/execute")
def execute_tool():
    try:
        data = request.get_json(silent=True) or {}
        tool_name = data.get("tool")
        params = data.get("parameters", {})

        if not tool_name:
            return jsonify({
                "status": "error",
                "message": "Missing 'tool' parameter",
            }), 400

        if tool_name == "system_status":
            result = {
                "status": "success",
                "service": "QuantumSafeKYC MCP Server",
                "mcp": "connected",
                "message": "MCP server is running successfully",
            }
        elif tool_name == "get_user_tool":
            result = get_user(params.get("user_uuid"))
        elif tool_name == "get_credential_tool":
            result = get_credential(params.get("credential_uuid"))
        elif tool_name == "check_consent_tool":
            result = check_consent(
                params.get("user_uuid"),
                params.get("credential_uuid"),
                params.get("verifier_id"),
                params.get("purpose"),
            )
        elif tool_name == "verify_pqc_tool":
            result = verify_pqc(params.get("credential_uuid"))
        elif tool_name == "verify_credential_tool":
            result = verify_credential_complete(
                params.get("credential_uuid"),
                params.get("verifier_id"),
                params.get("purpose"),
            )
        elif tool_name == "check_revocation_tool":
            result = check_revocation(params.get("credential_uuid"))
        elif tool_name == "verify_blockchain_tool":
            result = verify_blockchain(params.get("credential_uuid"))
        elif tool_name == "get_verification_history_tool":
            result = get_verification_history(params.get("credential_uuid"))
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown tool: '{tool_name}'",
            }), 404

        return jsonify({
            "status": "success",
            "tool": tool_name,
            "result": result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error executing tool '{tool_name}': {str(e)}",
        }), 500
